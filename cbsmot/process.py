"""Run CB-SMoT over a trajectories Parquet file and emit a segments Parquet file."""

from __future__ import annotations

from collections import namedtuple
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd
from shapely.geometry import LineString, Point

from .algorithm import DEFAULT_MAX_GAP_SECONDS, cbsmot

TRAJECTORY_COLUMNS = ["vehicle_id", "route_id", "datetime", "latitude", "longitude"]

SEGMENT_COLUMNS = [
    "vehicle_id",
    "route_id",
    "start_time",
    "end_time",
    "duration_seconds",
    "distance_meters",
    "num_points",
    "average_speed_mps",
    "geometry_wkt",
]

_Row = namedtuple("_Row", ["datetime", "point", "vehicle_id", "route_id"])


def _to_algorithm_points(group: pd.DataFrame) -> list[_Row]:
    return [
        _Row(
            datetime=row.datetime,
            point=Point(row.longitude, row.latitude),
            vehicle_id=row.vehicle_id,
            route_id=row.route_id,
        )
        for row in group.itertuples(index=False)
    ]


def _iter_segments(
    trajectories: pd.DataFrame,
    max_speed: float,
    min_time: float,
    max_gap_seconds: float,
) -> Iterator[dict]:
    ordered = trajectories.sort_values(["vehicle_id", "datetime"])
    for vehicle_id, group in ordered.groupby("vehicle_id", sort=False):
        points = _to_algorithm_points(group)
        for stop in cbsmot(
            points,
            max_average_speed=max_speed,
            min_time=min_time,
            max_gap_seconds=max_gap_seconds,
        ):
            if len(stop.trajectorys) < 2:
                continue
            coords = [(p.point.x, p.point.y) for p in stop.trajectorys]
            route_id = next(
                (p.route_id for p in stop.trajectorys if pd.notna(p.route_id)),
                None,
            )
            duration = stop.delta_time
            distance = stop.dist
            yield {
                "vehicle_id": int(vehicle_id),
                "route_id": None if route_id is None else int(route_id),
                "start_time": stop.init_time,
                "end_time": stop.last_time,
                "duration_seconds": float(duration),
                "distance_meters": float(distance),
                "num_points": len(stop.trajectorys),
                "average_speed_mps": float(distance / duration) if duration > 0 else 0.0,
                "geometry_wkt": LineString(coords).wkt,
            }


def detect_segments(
    trajectories: pd.DataFrame,
    *,
    max_speed: float = 3.0,
    min_time: float = 60.0,
    max_gap_seconds: float = DEFAULT_MAX_GAP_SECONDS,
) -> pd.DataFrame:
    """Run CB-SMoT on an in-memory trajectories DataFrame."""
    missing = set(TRAJECTORY_COLUMNS) - set(trajectories.columns)
    if missing:
        raise ValueError(f"trajectories is missing required columns: {sorted(missing)}")
    if trajectories.empty:
        return pd.DataFrame(columns=SEGMENT_COLUMNS)
    records = list(_iter_segments(trajectories, max_speed, min_time, max_gap_seconds))
    if not records:
        return pd.DataFrame(columns=SEGMENT_COLUMNS)
    return pd.DataFrame.from_records(records, columns=SEGMENT_COLUMNS)


def process(
    input_path: str | Path,
    output_path: str | Path,
    *,
    max_speed: float = 3.0,
    min_time: float = 60.0,
    max_gap_seconds: float = DEFAULT_MAX_GAP_SECONDS,
    vehicle_ids: Iterable[int] | None = None,
    route_ids: Iterable[int] | None = None,
) -> pd.DataFrame:
    """Read a trajectories Parquet file, detect segments, write a segments Parquet file."""
    trajectories = pd.read_parquet(input_path, columns=TRAJECTORY_COLUMNS)
    if vehicle_ids is not None:
        trajectories = trajectories[trajectories["vehicle_id"].isin(list(vehicle_ids))]
    elif route_ids is not None:
        trajectories = trajectories[trajectories["route_id"].isin(list(route_ids))]
    segments = detect_segments(
        trajectories,
        max_speed=max_speed,
        min_time=min_time,
        max_gap_seconds=max_gap_seconds,
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    segments.to_parquet(output_path, index=False)
    return segments
