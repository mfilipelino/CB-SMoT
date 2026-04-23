"""Tests for recurrent region discovery via DBSCAN over segment centroids."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from shapely.geometry import LineString

from cbsmot.process import SEGMENT_COLUMNS
from cbsmot.regions import REGION_COLUMNS, cluster_regions, discover_regions


def _segment(
    *,
    vehicle_id: int,
    route_id: int,
    lat: float,
    lon: float,
    duration: float = 90.0,
) -> dict:
    # Tiny linestring around the given point so its centroid sits at (lat, lon).
    delta = 1e-5
    line = LineString(
        [
            (lon - delta, lat - delta),
            (lon, lat),
            (lon + delta, lat + delta),
        ]
    )
    return {
        "vehicle_id": vehicle_id,
        "route_id": route_id,
        "start_time": datetime(2020, 1, 1, 8, 0, 0),
        "end_time": datetime(2020, 1, 1, 8, 1, 30),
        "duration_seconds": duration,
        "distance_meters": 20.0,
        "num_points": 5,
        "average_speed_mps": 20.0 / duration,
        "geometry_wkt": line.wkt,
    }


def _segments_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=SEGMENT_COLUMNS)


class ClusterRegionsTests(unittest.TestCase):
    def test_empty_segments_returns_empty_schema(self):
        regions = cluster_regions(_segments_df([]))
        self.assertEqual(len(regions), 0)
        self.assertEqual(list(regions.columns), REGION_COLUMNS)

    def test_dense_cluster_forms_one_region(self):
        # Three distinct vehicles stop within ~20m of each other at one spot.
        rows = [
            _segment(vehicle_id=1, route_id=100, lat=-23.550520, lon=-46.633309),
            _segment(vehicle_id=2, route_id=100, lat=-23.550530, lon=-46.633310),
            _segment(vehicle_id=3, route_id=200, lat=-23.550540, lon=-46.633300),
        ]
        regions = cluster_regions(_segments_df(rows), eps_meters=50.0, min_samples=3)
        self.assertEqual(len(regions), 1)
        region = regions.iloc[0]
        self.assertEqual(region["num_segments"], 3)
        self.assertEqual(region["unique_vehicles"], 3)
        self.assertEqual(region["num_routes"], 2)
        self.assertAlmostEqual(region["centroid_latitude"], -23.550530, places=4)
        self.assertAlmostEqual(region["centroid_longitude"], -46.633306, places=4)

    def test_isolated_segments_are_treated_as_noise(self):
        # Two clusters far apart: one dense (3 pts), one sparse (1 pt).
        # Only the dense cluster should become a region; the isolated point drops.
        dense = [
            _segment(vehicle_id=1, route_id=100, lat=-23.550520, lon=-46.633309),
            _segment(vehicle_id=2, route_id=100, lat=-23.550530, lon=-46.633310),
            _segment(vehicle_id=3, route_id=100, lat=-23.550540, lon=-46.633300),
        ]
        isolated = [_segment(vehicle_id=4, route_id=100, lat=-23.600000, lon=-46.700000)]
        regions = cluster_regions(
            _segments_df(dense + isolated), eps_meters=50.0, min_samples=3
        )
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions.iloc[0]["num_segments"], 3)

    def test_two_separated_clusters_form_two_regions(self):
        cluster_a = [
            _segment(vehicle_id=1, route_id=100, lat=-23.550520, lon=-46.633309),
            _segment(vehicle_id=2, route_id=100, lat=-23.550530, lon=-46.633310),
            _segment(vehicle_id=3, route_id=100, lat=-23.550540, lon=-46.633300),
        ]
        cluster_b = [
            _segment(vehicle_id=4, route_id=200, lat=-23.560000, lon=-46.640000),
            _segment(vehicle_id=5, route_id=200, lat=-23.560010, lon=-46.640010),
            _segment(vehicle_id=6, route_id=200, lat=-23.560020, lon=-46.640005),
        ]
        regions = cluster_regions(
            _segments_df(cluster_a + cluster_b), eps_meters=50.0, min_samples=3
        )
        self.assertEqual(len(regions), 2)
        self.assertEqual(set(regions["num_segments"]), {3})


class DiscoverRegionsParquetTests(unittest.TestCase):
    def test_round_trip(self):
        rows = [
            _segment(vehicle_id=1, route_id=100, lat=-23.550520, lon=-46.633309),
            _segment(vehicle_id=2, route_id=100, lat=-23.550530, lon=-46.633310),
            _segment(vehicle_id=3, route_id=200, lat=-23.550540, lon=-46.633300),
        ]
        with TemporaryDirectory() as tmp:
            seg_path = Path(tmp) / "segments.parquet"
            reg_path = Path(tmp) / "out" / "regions.parquet"
            _segments_df(rows).to_parquet(seg_path, index=False)

            regions = discover_regions(seg_path, reg_path, eps_meters=50.0, min_samples=3)

            self.assertEqual(len(regions), 1)
            self.assertTrue(reg_path.exists())
            reloaded = pd.read_parquet(reg_path)
            self.assertEqual(list(reloaded.columns), REGION_COLUMNS)
            self.assertEqual(reloaded.iloc[0]["num_segments"], 3)


if __name__ == "__main__":
    unittest.main()
