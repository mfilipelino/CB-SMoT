"""End-to-end tests for the Parquet → Parquet processing pipeline."""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from cbsmot.process import SEGMENT_COLUMNS, detect_segments, process


def _build_trajectories(n_points: int, *, lon_step: float, vehicle_id: int = 1,
                       route_id: int = 100, seconds_between: int = 10) -> pd.DataFrame:
    base_time = datetime(2020, 1, 1, 12, 0, 0)
    rows = []
    for i in range(n_points):
        rows.append(
            {
                "vehicle_id": vehicle_id,
                "route_id": route_id,
                "datetime": base_time + timedelta(seconds=i * seconds_between),
                "latitude": -23.550520,
                "longitude": -46.633309 + (i * lon_step),
            }
        )
    return pd.DataFrame(rows)


class DetectSegmentsTests(unittest.TestCase):
    def test_empty_input_returns_empty_frame_with_schema(self):
        df = pd.DataFrame(columns=["vehicle_id", "route_id", "datetime", "latitude", "longitude"])
        segments = detect_segments(df, max_speed=1.0, min_time=60.0)
        self.assertEqual(len(segments), 0)
        self.assertEqual(list(segments.columns), SEGMENT_COLUMNS)

    def test_missing_column_raises(self):
        df = pd.DataFrame({"vehicle_id": [1], "datetime": [datetime.now()], "latitude": [0.0], "longitude": [0.0]})
        with self.assertRaises(ValueError):
            detect_segments(df)

    def test_moving_vehicle_produces_no_segments(self):
        df = _build_trajectories(n_points=10, lon_step=0.001)  # ~100m per 10s
        segments = detect_segments(df, max_speed=1.0, min_time=60.0)
        self.assertEqual(len(segments), 0)

    def test_stationary_vehicle_produces_segment(self):
        df = _build_trajectories(n_points=10, lon_step=0.00001)  # ~1m per 10s
        segments = detect_segments(df, max_speed=1.0, min_time=60.0)
        self.assertEqual(len(segments), 1)
        row = segments.iloc[0]
        self.assertEqual(row["vehicle_id"], 1)
        self.assertEqual(row["route_id"], 100)
        self.assertGreaterEqual(row["duration_seconds"], 60)
        self.assertGreaterEqual(row["num_points"], 7)
        self.assertTrue(row["geometry_wkt"].startswith("LINESTRING"))

    def test_per_vehicle_grouping(self):
        a = _build_trajectories(n_points=10, lon_step=0.00001, vehicle_id=1, route_id=100)
        b = _build_trajectories(n_points=10, lon_step=0.00001, vehicle_id=2, route_id=200)
        segments = detect_segments(pd.concat([a, b], ignore_index=True), max_speed=1.0, min_time=60.0)
        self.assertEqual(len(segments), 2)
        self.assertEqual(set(segments["vehicle_id"]), {1, 2})
        self.assertEqual(set(segments["route_id"]), {100, 200})


class ProcessParquetTests(unittest.TestCase):
    def test_round_trip(self):
        df = _build_trajectories(n_points=10, lon_step=0.00001)
        with TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "trajectories.parquet"
            output_path = Path(tmp) / "out" / "segments.parquet"
            df.to_parquet(input_path, index=False)

            segments = process(input_path, output_path, max_speed=1.0, min_time=60.0)

            self.assertEqual(len(segments), 1)
            self.assertTrue(output_path.exists())
            reloaded = pd.read_parquet(output_path)
            self.assertEqual(len(reloaded), 1)
            self.assertEqual(list(reloaded.columns), SEGMENT_COLUMNS)

    def test_vehicle_id_filter(self):
        a = _build_trajectories(n_points=10, lon_step=0.00001, vehicle_id=1)
        b = _build_trajectories(n_points=10, lon_step=0.00001, vehicle_id=2)
        with TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "trajectories.parquet"
            output_path = Path(tmp) / "segments.parquet"
            pd.concat([a, b], ignore_index=True).to_parquet(input_path, index=False)

            segments = process(
                input_path, output_path,
                max_speed=1.0, min_time=60.0, vehicle_ids=[2],
            )

            self.assertEqual(len(segments), 1)
            self.assertEqual(segments.iloc[0]["vehicle_id"], 2)


if __name__ == "__main__":
    unittest.main()
