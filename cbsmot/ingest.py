"""Poll the SPTrans Olho Vivo API for vehicle positions and write trajectory Parquet files.

The SPTrans API requires an access token. Obtain one at
https://www.sptrans.com.br/desenvolvedores/ and pass it via `--token` or the
`SPTRANS_TOKEN` environment variable. The emitted `datetime` column stores
poll-observation time; the raw API `ta` field is preserved separately as
`source_datetime`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
import requests

BASE_URL = "http://api.olhovivo.sptrans.com.br/v2.1"
TRAJECTORY_COLUMNS = ["vehicle_id", "route_id", "datetime", "latitude", "longitude"]
INGEST_OUTPUT_COLUMNS = [*TRAJECTORY_COLUMNS, "source_datetime"]


class SPTransAuthError(RuntimeError):
    pass


@dataclass
class SPTransClient:
    token: str
    session: requests.Session | None = None
    base_url: str = BASE_URL
    timeout: float = 20.0

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()

    def authenticate(self) -> None:
        resp = self.session.post(
            f"{self.base_url}/Login/Autenticar",
            params={"token": self.token},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        if resp.json() is not True:
            raise SPTransAuthError("SPTrans authentication rejected the token.")

    def fetch_positions(self, route_code: int) -> list[dict]:
        resp = self.session.get(
            f"{self.base_url}/Posicao/Linha",
            params={"codigoLinha": route_code},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json() or {}
        sampled_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return _parse_positions(payload, route_code=route_code, sampled_at=sampled_at)


def _parse_positions(payload: dict, *, route_code: int, sampled_at: datetime) -> list[dict]:
    """Extract rows from the `/Posicao/Linha` response shape.

    `datetime` stores when the poll observed the vehicle state. The raw
    SPTrans `ta` value is preserved in `source_datetime` because it can
    repeat while a bus is stationary.
    """
    rows: list[dict] = []
    for v in payload.get("vs", []) or []:
        try:
            source_datetime = _parse_timestamp(v.get("ta"))
            rows.append(
                {
                    "vehicle_id": int(v["p"]),
                    "route_id": int(route_code),
                    "datetime": sampled_at,
                    "source_datetime": source_datetime,
                    "latitude": float(v["py"]),
                    "longitude": float(v["px"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def poll_once(client: SPTransClient, route_codes: Sequence[int]) -> list[dict]:
    rows: list[dict] = []
    for code in route_codes:
        try:
            rows.extend(client.fetch_positions(code))
        except requests.RequestException as exc:
            print(f"[warn] route {code}: {exc}")
    return rows


def ingest(
    token: str,
    route_codes: Iterable[int],
    output_path: str | Path,
    *,
    duration_seconds: float,
    interval_seconds: float = 15.0,
    client: SPTransClient | None = None,
    sleep: "callable" = time.sleep,
    clock: "callable" = time.monotonic,
) -> pd.DataFrame:
    """Poll SPTrans for `duration_seconds`, flush all rows to `output_path`."""
    codes = list(route_codes)
    if client is None:
        client = SPTransClient(token=token)
        client.authenticate()

    rows: list[dict] = []
    deadline = clock() + duration_seconds

    while True:
        rows.extend(poll_once(client, codes))
        if clock() >= deadline:
            break
        sleep(interval_seconds)

    df = pd.DataFrame(rows, columns=INGEST_OUTPUT_COLUMNS)
    for column in ("datetime", "source_datetime"):
        df[column] = pd.to_datetime(df[column])
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, index=False)
    return df
