"""Pure-Python tests for the CB-SMoT algorithm primitives."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from cbsmot.algorithm import (
    Stop,
    average_speed,
    cbsmot,
    delta_time,
    distance_absolute,
    haversine,
)


class TestHaversine(unittest.TestCase):
    def test_short_distance(self):
        distance = haversine(-46.633309, -23.550520, -46.634000, -23.551000)
        self.assertLess(distance, 1.0)
        self.assertGreater(distance, 0.0)

    def test_sao_paulo_to_rio(self):
        distance = haversine(-46.633309, -23.550520, -43.172897, -22.906847)
        self.assertGreater(distance, 350.0)
        self.assertLess(distance, 380.0)


class TestDistanceAbsolute(unittest.TestCase):
    def test_returns_meters(self):
        a = MagicMock(x=-46.633309, y=-23.550520)
        b = MagicMock(x=-46.634000, y=-23.551000)
        distance = distance_absolute(a, b)
        self.assertLess(distance, 1000.0)
        self.assertGreater(distance, 0.0)


class TestAverageSpeed(unittest.TestCase):
    def test_simple_division(self):
        self.assertEqual(average_speed(100.0, 20.0), 5.0)


class TestDeltaTime(unittest.TestCase):
    def test_seconds_between_datetimes(self):
        t1 = datetime(2020, 1, 1, 12, 0, 0)
        t2 = datetime(2020, 1, 1, 12, 0, 30)
        self.assertEqual(delta_time(t2, t1), 30.0)


class TestStop(unittest.TestCase):
    def test_initial_state(self):
        stop = Stop()
        self.assertEqual(stop.trajectorys, [])
        self.assertIsNone(stop.init_time)
        self.assertEqual(stop.delta_time, 0.0)
        self.assertIsNone(stop.last_time)
        self.assertEqual(stop.dist, 0.0)

    def test_add_accumulates_time_and_distance(self):
        stop = Stop()
        t1 = MagicMock(datetime=datetime(2020, 1, 1, 12, 0, 0))
        t2 = MagicMock(datetime=datetime(2020, 1, 1, 12, 0, 30))
        stop.add(t1, 0.0)
        stop.add(t2, 100.0)
        self.assertEqual(stop.trajectorys, [t1, t2])
        self.assertEqual(stop.init_time, t1.datetime)
        self.assertEqual(stop.delta_time, 30.0)
        self.assertEqual(stop.last_time, t2.datetime)
        self.assertEqual(stop.dist, 100.0)


class TestCBSMoT(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(cbsmot([], 1, 60), [])

    def test_single_point_yields_no_stop(self):
        trajectory = MagicMock(point=MagicMock(), datetime=datetime(2020, 1, 1, 12, 0, 0))
        self.assertEqual(cbsmot([trajectory], 1, 60), [])

    def test_moving_trajectory_yields_no_stop(self):
        base_time = datetime(2020, 1, 1, 12, 0, 0)
        trajectories = []
        for i in range(10):
            trajectory = MagicMock(
                point=MagicMock(x=-46.633309 + (i * 0.001), y=-23.550520),
                datetime=base_time + timedelta(seconds=i * 10),
            )
            trajectories.append(trajectory)
        self.assertEqual(cbsmot(trajectories, 1, 60), [])

    def test_stationary_trajectory_yields_stop(self):
        base_time = datetime(2020, 1, 1, 12, 0, 0)
        trajectories = []
        for i in range(10):
            trajectory = MagicMock(
                point=MagicMock(x=-46.633309 + (i * 0.00001), y=-23.550520),
                datetime=base_time + timedelta(seconds=i * 10),
            )
            trajectories.append(trajectory)
        result = cbsmot(trajectories, 1, 60)
        self.assertGreater(len(result), 0)
        stop = result[0]
        self.assertGreaterEqual(len(stop.trajectorys), 7)
        self.assertEqual(stop.init_time, trajectories[0].datetime)
        self.assertGreaterEqual(stop.delta_time, 60)

    def test_duplicate_stationary_timestamps_do_not_break_stop(self):
        same_point = MagicMock(x=-46.633309, y=-23.550520)
        trajectories = [
            MagicMock(point=same_point, datetime=datetime(2020, 1, 1, 12, 0, 0)),
            MagicMock(point=same_point, datetime=datetime(2020, 1, 1, 12, 0, 10)),
            MagicMock(point=same_point, datetime=datetime(2020, 1, 1, 12, 0, 10)),
            MagicMock(point=same_point, datetime=datetime(2020, 1, 1, 12, 0, 20)),
        ]
        result = cbsmot(trajectories, 1, 15)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].delta_time, 20.0)

    def test_max_gap_seconds_breaks_stop_when_gap_exceeds_bound(self):
        base_time = datetime(2020, 1, 1, 12, 0, 0)
        trajectories = []
        for i in range(10):
            trajectory = MagicMock(
                point=MagicMock(x=-46.633309 + (i * 0.00001), y=-23.550520),
                datetime=base_time + timedelta(seconds=i * 30),
            )
            trajectories.append(trajectory)
        # Default max_gap_seconds=20 breaks every gap (30s apart) -> no stop emitted.
        self.assertEqual(cbsmot(trajectories, 1, 60), [])
        # Relaxing the gap bound admits the same sparse data as a single stop.
        relaxed = cbsmot(trajectories, 1, 60, max_gap_seconds=45.0)
        self.assertEqual(len(relaxed), 1)
        self.assertGreaterEqual(relaxed[0].delta_time, 60)


if __name__ == "__main__":
    unittest.main()
