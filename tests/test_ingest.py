"""Tests for the SPTrans ingestion module.

No real network calls — `requests.Session` is replaced with a fake.
"""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import pandas as pd

from cbsmot.ingest import (
    INGEST_OUTPUT_COLUMNS,
    SPTransAuthError,
    SPTransClient,
    _parse_positions,
    _parse_timestamp,
    ingest,
    poll_once,
)


def _fake_response(json_value, *, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_value
    resp.raise_for_status = MagicMock()
    return resp


class ParsePositionsTests(unittest.TestCase):
    def test_extracts_rows(self):
        payload = {
            "hr": "12:00",
            "vs": [
                {"p": 12345, "a": True, "ta": "2020-01-01T12:00:00Z", "py": -23.55, "px": -46.63},
                {"p": 67890, "a": False, "py": -23.56, "px": -46.64},  # missing ta
            ],
        }
        sampled = datetime(2020, 1, 1, 12, 0, 5)
        rows = _parse_positions(payload, route_code=100, sampled_at=sampled)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["vehicle_id"], 12345)
        self.assertEqual(rows[0]["route_id"], 100)
        self.assertEqual(rows[0]["datetime"], sampled)
        self.assertEqual(rows[0]["source_datetime"], datetime(2020, 1, 1, 12, 0, 0))
        self.assertEqual(rows[1]["datetime"], sampled)
        self.assertIsNone(rows[1]["source_datetime"])

    def test_empty_payload(self):
        self.assertEqual(_parse_positions({}, route_code=100, sampled_at=datetime.now()), [])
        self.assertEqual(_parse_positions({"vs": None}, route_code=100, sampled_at=datetime.now()), [])

    def test_skips_malformed_rows(self):
        payload = {"vs": [{"p": "bad"}, {"p": 1, "py": -23.5, "px": -46.6}]}
        rows = _parse_positions(payload, route_code=100, sampled_at=datetime.now())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["vehicle_id"], 1)


class ParseTimestampTests(unittest.TestCase):
    def test_parses_iso_with_z(self):
        self.assertEqual(_parse_timestamp("2020-01-01T12:00:00Z"), datetime(2020, 1, 1, 12, 0, 0))

    def test_returns_none_for_empty_or_bad(self):
        self.assertIsNone(_parse_timestamp(None))
        self.assertIsNone(_parse_timestamp(""))
        self.assertIsNone(_parse_timestamp("not a date"))


class SPTransClientTests(unittest.TestCase):
    def test_authenticate_rejects_false_response(self):
        session = MagicMock()
        session.post.return_value = _fake_response(False)
        client = SPTransClient(token="tok", session=session)
        with self.assertRaises(SPTransAuthError):
            client.authenticate()

    def test_authenticate_accepts_true(self):
        session = MagicMock()
        session.post.return_value = _fake_response(True)
        client = SPTransClient(token="tok", session=session)
        client.authenticate()
        session.post.assert_called_once()

    def test_fetch_positions_returns_rows(self):
        session = MagicMock()
        session.get.return_value = _fake_response(
            {"vs": [{"p": 1, "a": True, "py": -23.5, "px": -46.6}]}
        )
        client = SPTransClient(token="tok", session=session)
        rows = client.fetch_positions(route_code=8000)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["route_id"], 8000)


class PollOnceTests(unittest.TestCase):
    def test_aggregates_across_routes(self):
        session = MagicMock()

        def get(url, params, timeout):
            code = params["codigoLinha"]
            return _fake_response({"vs": [{"p": code * 10, "py": -23.5, "px": -46.6}]})

        session.get.side_effect = get
        client = SPTransClient(token="tok", session=session)
        rows = poll_once(client, [100, 200])
        self.assertEqual({r["vehicle_id"] for r in rows}, {1000, 2000})


class IngestTests(unittest.TestCase):
    def test_polls_multiple_times_until_deadline(self):
        session = MagicMock()
        session.get.return_value = _fake_response(
            {"vs": [{"p": 1, "py": -23.5, "px": -46.6}]}
        )
        client = SPTransClient(token="tok", session=session)

        # ticks consumed: deadline=0.0+30; loop1 clock=15 (<30, continue);
        # loop2 clock=30 (>=30, break). Two polls total, one sleep between.
        ticks = iter([0.0, 15.0, 30.0])
        sleep_calls: list[float] = []

        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "trajectories.parquet"
            df = ingest(
                token="unused",
                route_codes=[100],
                output_path=output,
                duration_seconds=30.0,
                interval_seconds=15.0,
                client=client,
                clock=lambda: next(ticks),
                sleep=sleep_calls.append,
            )
            self.assertTrue(output.exists())
            reloaded = pd.read_parquet(output)
            self.assertEqual(list(reloaded.columns), INGEST_OUTPUT_COLUMNS)
            self.assertEqual(len(df), 2)
            self.assertEqual(sleep_calls, [15.0])

    def test_empty_poll_still_produces_empty_parquet_with_schema(self):
        session = MagicMock()
        session.get.return_value = _fake_response({"vs": []})
        client = SPTransClient(token="tok", session=session)

        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "trajectories.parquet"
            df = ingest(
                token="unused",
                route_codes=[100],
                output_path=output,
                duration_seconds=0.0,
                interval_seconds=15.0,
                client=client,
                clock=iter([0.0, 0.1]).__next__,
                sleep=lambda _: None,
            )
            self.assertEqual(len(df), 0)
            reloaded = pd.read_parquet(output)
            self.assertEqual(list(reloaded.columns), INGEST_OUTPUT_COLUMNS)


if __name__ == "__main__":
    unittest.main()
