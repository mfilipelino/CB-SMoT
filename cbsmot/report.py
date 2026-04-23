"""Aggregate statistics from a detected-segments Parquet file."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_report(segments_path: str | Path, *, top_n_routes: int = 5) -> dict:
    segments = pd.read_parquet(segments_path)
    if segments.empty:
        return {"total": 0}

    start_time = pd.to_datetime(segments["start_time"])
    hourly = (
        start_time.dt.hour.value_counts()
        .reindex(range(24), fill_value=0)
        .astype(int)
        .to_dict()
    )
    top_routes = (
        segments.groupby("route_id", dropna=False)
        .size()
        .sort_values(ascending=False)
        .head(top_n_routes)
    )

    return {
        "total": int(len(segments)),
        "avg_duration_s": float(segments["duration_seconds"].mean()),
        "avg_speed_mps": float(segments["average_speed_mps"].mean()),
        "avg_points": float(segments["num_points"].mean()),
        "total_distance_m": float(segments["distance_meters"].sum()),
        "top_routes": [
            (None if pd.isna(route_id) else int(route_id), int(count))
            for route_id, count in top_routes.items()
        ],
        "hourly": hourly,
    }


def print_report(report: dict) -> None:
    if report["total"] == 0:
        print("No detected segments found. Nothing to report.")
        return

    print("--- Overall Segment Statistics ---")
    print(f"Total Detected Segments: {report['total']}")
    print(f"Average Segment Duration: {report['avg_duration_s']:.2f} seconds")
    print(f"Average Segment Speed: {report['avg_speed_mps']:.2f} m/s")
    print(f"Average Points per Segment: {report['avg_points']:.2f}")
    print(f"Total Distance Covered by Segments: {report['total_distance_m']:.2f} meters")
    print()

    print(f"--- Top {len(report['top_routes'])} Routes by Segment Count ---")
    for i, (route_id, count) in enumerate(report["top_routes"], start=1):
        label = "Segments with no associated route" if route_id is None else f"Route {route_id}"
        print(f"{i}. {label}: {count} segments")
    print()

    print("--- Segment Distribution by Start Hour ---")
    for hour in range(24):
        print(f"Hour {hour:02d}: {report['hourly'].get(hour, 0)} segments")
