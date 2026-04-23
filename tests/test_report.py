"""Tests for the segment statistical report."""

import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from cbsmot.process import SEGMENT_COLUMNS
from cbsmot.report import build_report, print_report


def _write_segments(rows: list[dict], path: Path) -> None:
    pd.DataFrame(rows, columns=SEGMENT_COLUMNS).to_parquet(path, index=False)


def _segment(
    *,
    vehicle_id: int = 1,
    route_id: int | None = 100,
    start_hour: int = 8,
    duration: float = 90.0,
    distance: float = 50.0,
    num_points: int = 10,
) -> dict:
    start = datetime(2020, 1, 1, start_hour, 0, 0)
    return {
        "vehicle_id": vehicle_id,
        "route_id": route_id,
        "start_time": start,
        "end_time": datetime(2020, 1, 1, start_hour, 1, 30),
        "duration_seconds": duration,
        "distance_meters": distance,
        "num_points": num_points,
        "average_speed_mps": distance / duration,
        "geometry_wkt": "LINESTRING(0 0, 1 1)",
    }


class BuildReportTests(unittest.TestCase):
    def test_empty_parquet(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.parquet"
            _write_segments([], path)
            report = build_report(path)
        self.assertEqual(report, {"total": 0})

    def test_aggregations(self):
        rows = [
            _segment(route_id=100, start_hour=8),
            _segment(route_id=100, start_hour=9),
            _segment(route_id=200, start_hour=8),
            _segment(route_id=None, start_hour=23),
        ]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.parquet"
            _write_segments(rows, path)
            report = build_report(path, top_n_routes=2)

        self.assertEqual(report["total"], 4)
        self.assertEqual(report["hourly"][8], 2)
        self.assertEqual(report["hourly"][9], 1)
        self.assertEqual(report["hourly"][23], 1)
        self.assertEqual(report["hourly"][0], 0)
        top = dict(report["top_routes"])
        self.assertEqual(top[100], 2)
        self.assertIn(200, top)


class PrintReportTests(unittest.TestCase):
    def test_empty_message(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_report({"total": 0})
        self.assertIn("No detected segments", buf.getvalue())

    def test_populated_output_contains_sections(self):
        rows = [_segment(route_id=100), _segment(route_id=200)]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.parquet"
            _write_segments(rows, path)
            report = build_report(path)
            buf = io.StringIO()
            with redirect_stdout(buf):
                print_report(report)
        output = buf.getvalue()
        self.assertIn("Overall Segment Statistics", output)
        self.assertIn("Top", output)
        self.assertIn("Segment Distribution by Start Hour", output)


if __name__ == "__main__":
    unittest.main()
