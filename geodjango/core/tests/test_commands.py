# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import sys
import os
from unittest.mock import patch, MagicMock, ANY

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from django.contrib.gis.geos import Point, LineString
from io import StringIO

from geodjango.core.models import Vehicle, Route, Trajectory, DetectedSegment

# Ensure cbsmot_algorithm can be imported for creating mock Stop objects
# This assumes cbsmot_algorithm.py is in the project root.
# Adjust path if your project structure is different.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from cbsmot_algorithm import Stop as CbsmotStop
except ImportError:
    # Create a dummy class if the import fails, so tests can be defined.
    # The tests that rely on this will likely fail if cbsmot_algorithm is truly missing.
    class CbsmotStop:
        def __init__(self, init_time, last_time, delta_time, dist, trajectorys):
            self.init_time = init_time
            self.last_time = last_time
            self.delta_time = delta_time
            self.dist = dist
            self.trajectorys = trajectorys


class ProcessTrajectoriesCommandTests(TestCase):

    def setUp(self):
        self.now = timezone.now()

        # Route 1
        self.route1 = Route.objects.create(code=1, sign=1, direction=1, main_to_sec="R1 M-S", sec_to_main="R1 S-M", type_route="U")
        # Route 2
        self.route2 = Route.objects.create(code=2, sign=2, direction=1, main_to_sec="R2 M-S", sec_to_main="R2 S-M", type_route="U")

        # Vehicle 1 (on Route 1, will have segments)
        self.vehicle1 = Vehicle.objects.create(route=self.route1, acessible=True, prefix=1001)
        self.v1_traj_points = []
        for i in range(5):
            dt = self.now - datetime.timedelta(minutes=5-i)
            # Points simulating movement then a stop
            lon = 20.0 + i * 0.0001 if i < 2 else 20.0002 # Stays at 20.0002 for last 3 points
            lat = 10.0 + i * 0.0001 if i < 2 else 10.0002 # Stays at 10.0002 for last 3 points
            tp = Trajectory.objects.create(
                vehicle=self.vehicle1, datetime=dt, latitude=lat, longitude=lon,
                point=Point(lon, lat, srid=4326)
            )
            self.v1_traj_points.append(tp)
        
        # Vehicle 2 (on Route 1, no segments - points too far apart or too fast for default cbsmot)
        self.vehicle2 = Vehicle.objects.create(route=self.route1, acessible=False, prefix=1002)
        self.v2_traj_points = []
        for i in range(3):
            dt = self.now - datetime.timedelta(minutes=3-i)
            # Points simulating continuous movement
            tp = Trajectory.objects.create(
                vehicle=self.vehicle2, datetime=dt, latitude=10.1 + i * 0.01, longitude=20.1 + i * 0.01,
                point=Point(20.1 + i * 0.01, 10.1 + i * 0.01, srid=4326)
            )
            self.v2_traj_points.append(tp)

        # Vehicle 3 (on Route 2, will have segments)
        self.vehicle3 = Vehicle.objects.create(route=self.route2, acessible=True, prefix=1003)
        self.v3_traj_points = []
        for i in range(4):
            dt = self.now - datetime.timedelta(minutes=4-i)
            # Points simulating another stop
            lon = 21.0001
            lat = 11.0001
            tp = Trajectory.objects.create(
                vehicle=self.vehicle3, datetime=dt, latitude=lat, longitude=lon,
                point=Point(lon, lat, srid=4326)
            )
            self.v3_traj_points.append(tp)


        # Vehicle 4 (no trajectory points)
        self.vehicle4 = Vehicle.objects.create(route=self.route2, acessible=False, prefix=1004)

        # Define mock cbsmot output
        # Mock segment for Vehicle 1 (using its last 3 points)
        self.mock_segment1_points = self.v1_traj_points[2:] # Points that form the stop
        self.mock_stop1 = CbsmotStop(
            init_time=self.mock_segment1_points[0].datetime,
            last_time=self.mock_segment1_points[-1].datetime,
            delta_time=(self.mock_segment1_points[-1].datetime - self.mock_segment1_points[0].datetime).total_seconds(),
            dist=10.0, # Dummy distance
            trajectorys=self.mock_segment1_points
        )

        # Mock segment for Vehicle 3 (using all its points)
        self.mock_segment3_points = self.v3_traj_points
        self.mock_stop3 = CbsmotStop(
            init_time=self.mock_segment3_points[0].datetime,
            last_time=self.mock_segment3_points[-1].datetime,
            delta_time=(self.mock_segment3_points[-1].datetime - self.mock_segment3_points[0].datetime).total_seconds(),
            dist=5.0, # Dummy distance
            trajectorys=self.mock_segment3_points
        )
    
    def _get_expected_line_string(self, traj_points):
        if len(traj_points) < 2:
            return None
        return LineString([p.point.coords for p in traj_points], srid=4326)

    @patch('geodjango.core.management.commands.process_trajectories.cbsmot')
    def test_process_all_vehicles_default_params(self, mock_cbsmot):
        # Configure mock_cbsmot to return different results based on input
        def side_effect(trajectory_list, max_average_speed, min_time):
            if trajectory_list[0].vehicle == self.vehicle1:
                return [self.mock_stop1]
            elif trajectory_list[0].vehicle == self.vehicle2:
                return [] # No stops for vehicle 2
            elif trajectory_list[0].vehicle == self.vehicle3:
                return [self.mock_stop3]
            return []

        mock_cbsmot.side_effect = side_effect
        
        call_command('process_trajectories', stdout=StringIO())

        # Assertions for cbsmot calls
        # Vehicle 1 should be called
        # Vehicle 2 should be called
        # Vehicle 3 should be called
        # Vehicle 4 has no points, so cbsmot won't be called for it.
        self.assertEqual(mock_cbsmot.call_count, 3) 
        
        # Check default parameters were used (example for one call)
        mock_cbsmot.assert_any_call(
            ANY, # The list of trajectory points
            max_average_speed=3.0, # default
            min_time=60.0          # default
        )

        # Assertions for DetectedSegment creation
        segments = DetectedSegment.objects.all().order_by('vehicle__prefix')
        self.assertEqual(segments.count(), 2)

        # Segment for Vehicle 1
        seg1 = segments.filter(vehicle=self.vehicle1).first()
        self.assertIsNotNone(seg1)
        self.assertEqual(seg1.vehicle, self.vehicle1)
        self.assertEqual(seg1.route, self.vehicle1.route)
        self.assertEqual(seg1.start_time, self.mock_stop1.init_time)
        self.assertEqual(seg1.end_time, self.mock_stop1.last_time)
        self.assertAlmostEqual(seg1.duration_seconds, self.mock_stop1.delta_time)
        self.assertAlmostEqual(seg1.distance_meters, self.mock_stop1.dist)
        self.assertEqual(seg1.num_points, len(self.mock_stop1.trajectorys))
        expected_ls1 = self._get_expected_line_string(self.mock_stop1.trajectorys)
        self.assertTrue(seg1.segment_geometry.equals_exact(expected_ls1, tolerance=0.00001))
        self.assertSetEqual(set(seg1.trajectory_points.all()), set(self.mock_stop1.trajectorys))

        # Segment for Vehicle 3
        seg3 = segments.filter(vehicle=self.vehicle3).first()
        self.assertIsNotNone(seg3)
        self.assertEqual(seg3.vehicle, self.vehicle3)
        self.assertEqual(seg3.route, self.vehicle3.route)
        # ... other assertions for seg3 similar to seg1 ...
        self.assertEqual(seg3.num_points, len(self.mock_stop3.trajectorys))
        expected_ls3 = self._get_expected_line_string(self.mock_stop3.trajectorys)
        self.assertTrue(seg3.segment_geometry.equals_exact(expected_ls3, tolerance=0.00001))
        self.assertSetEqual(set(seg3.trajectory_points.all()), set(self.mock_stop3.trajectorys))


    @patch('geodjango.core.management.commands.process_trajectories.cbsmot')
    def test_process_with_vehicle_ids(self, mock_cbsmot):
        mock_cbsmot.return_value = [self.mock_stop1] # Only vehicle1 will be processed

        call_command('process_trajectories', vehicle_ids=[self.vehicle1.id], stdout=StringIO())
        
        mock_cbsmot.assert_called_once_with(
            list(Trajectory.objects.filter(vehicle=self.vehicle1).order_by('datetime')),
            max_average_speed=3.0,
            min_time=60.0
        )
        self.assertEqual(DetectedSegment.objects.count(), 1)
        self.assertTrue(DetectedSegment.objects.filter(vehicle=self.vehicle1).exists())

    @patch('geodjango.core.management.commands.process_trajectories.cbsmot')
    def test_process_with_route_ids(self, mock_cbsmot):
        # Vehicle 1 and 2 are on Route 1. Mock cbsmot to return a segment for V1, none for V2.
        def side_effect_route1(trajectory_list, **kwargs):
            if trajectory_list[0].vehicle == self.vehicle1:
                return [self.mock_stop1]
            return []
        mock_cbsmot.side_effect = side_effect_route1

        call_command('process_trajectories', route_ids=[self.route1.id], stdout=StringIO())
        
        # cbsmot should be called for vehicle1 and vehicle2 (both on route1)
        self.assertEqual(mock_cbsmot.call_count, 2) 
        mock_cbsmot.assert_any_call(list(self.v1_traj_points), max_average_speed=3.0, min_time=60.0)
        mock_cbsmot.assert_any_call(list(self.v2_traj_points), max_average_speed=3.0, min_time=60.0)

        self.assertEqual(DetectedSegment.objects.count(), 1)
        self.assertTrue(DetectedSegment.objects.filter(vehicle=self.vehicle1).exists())
        self.assertFalse(DetectedSegment.objects.filter(vehicle=self.vehicle2).exists()) # No segment for v2

    @patch('geodjango.core.management.commands.process_trajectories.cbsmot')
    def test_process_with_custom_speed_time(self, mock_cbsmot):
        mock_cbsmot.return_value = [self.mock_stop1]
        
        call_command('process_trajectories', vehicle_ids=[self.vehicle1.id], max_speed=2.0, min_time=30.0, stdout=StringIO())
        
        mock_cbsmot.assert_called_once_with(
            ANY, # trajectory list
            max_average_speed=2.0,
            min_time=30.0
        )

    @patch('geodjango.core.management.commands.process_trajectories.cbsmot')
    def test_clear_existing_segments(self, mock_cbsmot):
        # First run: create a segment
        mock_cbsmot.return_value = [self.mock_stop1]
        call_command('process_trajectories', vehicle_ids=[self.vehicle1.id], stdout=StringIO())
        self.assertEqual(DetectedSegment.objects.count(), 1)
        first_segment_id = DetectedSegment.objects.first().id

        # Second run: with clear_existing. Mock cbsmot to return a different segment or none.
        # For simplicity, let's say it finds a new segment for vehicle3 this time.
        mock_stop_alt = CbsmotStop(
            init_time=self.now, last_time=self.now + datetime.timedelta(minutes=2),
            delta_time=120, dist=50, trajectorys=self.v3_traj_points[:2] # Use a subset for different geometry
        )
        mock_cbsmot.return_value = [mock_stop_alt] # New segment for v3
        
        # Important: target all vehicles for the clear to make sense, or ensure v1 is processed again
        call_command('process_trajectories', clear_existing=True, vehicle_ids=[self.vehicle3.id], stdout=StringIO())
        
        self.assertEqual(DetectedSegment.objects.count(), 1)
        # The old segment for vehicle1 should be gone
        self.assertFalse(DetectedSegment.objects.filter(id=first_segment_id).exists())
        # The new segment for vehicle3 should exist
        self.assertTrue(DetectedSegment.objects.filter(vehicle=self.vehicle3).exists())
        new_segment = DetectedSegment.objects.filter(vehicle=self.vehicle3).first()
        self.assertEqual(new_segment.start_time, mock_stop_alt.init_time)

    @patch('geodjango.core.management.commands.process_trajectories.cbsmot')
    def test_vehicle_with_no_trajectories(self, mock_cbsmot):
        call_command('process_trajectories', vehicle_ids=[self.vehicle4.id], stdout=StringIO())
        
        mock_cbsmot.assert_not_called() # cbsmot should not be called for vehicle4
        self.assertEqual(DetectedSegment.objects.count(), 0)

    @patch('geodjango.core.management.commands.process_trajectories.cbsmot')
    def test_cbsmot_returns_empty_list(self, mock_cbsmot):
        mock_cbsmot.return_value = [] # Simulate cbsmot finding no segments

        call_command('process_trajectories', vehicle_ids=[self.vehicle1.id], stdout=StringIO())
        
        mock_cbsmot.assert_called_once()
        self.assertEqual(DetectedSegment.objects.count(), 0)

    @patch('geodjango.core.management.commands.process_trajectories.cbsmot')
    def test_segment_geometry_line_string_creation(self, mock_cbsmot):
        # Ensure LineString requires at least 2 points in the command logic
        # Mock cbsmot to return a segment with only one point
        one_point_traj = [self.v1_traj_points[0]]
        mock_stop_one_point = CbsmotStop(
            init_time=one_point_traj[0].datetime,
            last_time=one_point_traj[0].datetime, # init_time and last_time are the same
            delta_time=0, dist=0, trajectorys=one_point_traj
        )
        mock_cbsmot.return_value = [mock_stop_one_point]

        call_command('process_trajectories', vehicle_ids=[self.vehicle1.id], stdout=StringIO())
        
        # No segment should be created because LineString needs at least 2 points
        self.assertEqual(DetectedSegment.objects.count(), 0)
        
        # Now test with 2 points
        two_point_traj = self.v1_traj_points[:2]
        mock_stop_two_points = CbsmotStop(
            init_time=two_point_traj[0].datetime,
            last_time=two_point_traj[-1].datetime,
            delta_time=(two_point_traj[-1].datetime - two_point_traj[0].datetime).total_seconds(),
            dist=1, trajectorys=two_point_traj
        )
        mock_cbsmot.return_value = [mock_stop_two_points]
        DetectedSegment.objects.all().delete() # Clean from previous part of test
        
        call_command('process_trajectories', vehicle_ids=[self.vehicle1.id], stdout=StringIO())
        self.assertEqual(DetectedSegment.objects.count(), 1)
        segment = DetectedSegment.objects.first()
        self.assertIsInstance(segment.segment_geometry, LineString)
        self.assertEqual(len(segment.segment_geometry.coords), 2)


    @patch('geodjango.core.management.commands.process_trajectories.cbsmot')
    def test_no_vehicles_found(self, mock_cbsmot):
        # Use a vehicle ID that doesn't exist
        call_command('process_trajectories', vehicle_ids=[9999], stdout=StringIO())
        mock_cbsmot.assert_not_called()
        self.assertEqual(DetectedSegment.objects.count(), 0)

        # Use a route ID that doesn't exist
        call_command('process_trajectories', route_ids=[9999], stdout=StringIO())
        mock_cbsmot.assert_not_called()
        self.assertEqual(DetectedSegment.objects.count(), 0)

    @patch('geodjango.core.management.commands.process_trajectories.cbsmot')
    def test_trajectory_points_m2m_link(self, mock_cbsmot):
        mock_cbsmot.return_value = [self.mock_stop1]
        
        call_command('process_trajectories', vehicle_ids=[self.vehicle1.id], stdout=StringIO())
        
        self.assertEqual(DetectedSegment.objects.count(), 1)
        segment = DetectedSegment.objects.first()
        self.assertEqual(segment.trajectory_points.count(), len(self.mock_stop1.trajectorys))
        for tp_mock in self.mock_stop1.trajectorys:
            self.assertIn(tp_mock, segment.trajectory_points.all())

# To run these tests:
# python manage.py test geodjango.core.tests.test_commands.ProcessTrajectoriesCommandTests
# or if your apps are setup:
# python manage.py test core.tests.test_commands.ProcessTrajectoriesCommandTests
# or simply:
# python manage.py test core


class ReportSegmentsCommandTests(TestCase):
    maxDiff = None # Show full diff on assertion failure

    def setUp(self):
        self.now = timezone.now()

        # Create Routes
        self.route1 = Route.objects.create(code=101, sign=1, direction=1, main_to_sec="R101 A-B", sec_to_main="R101 B-A", type_route="Urban")
        self.route2 = Route.objects.create(code=102, sign=2, direction=1, main_to_sec="R102 C-D", sec_to_main="R102 D-C", type_route="Intercity")
        self.route3 = Route.objects.create(code=103, sign=3, direction=1, main_to_sec="R103 E-F", sec_to_main="R103 F-E", type_route="Urban")

        # Create DetectedSegments
        # Segment 1 (Route 1, Hour 9)
        DetectedSegment.objects.create(
            route=self.route1,
            start_time=self.now.replace(hour=9, minute=0, second=0, microsecond=0),
            end_time=self.now.replace(hour=9, minute=10, second=0, microsecond=0),
            duration_seconds=600.0,
            distance_meters=1000.0,
            num_points=50,
            average_speed_mps=1000.0/600.0,
            segment_geometry=LineString((0,0), (1,1), srid=4326)
        )
        # Segment 2 (Route 1, Hour 10)
        DetectedSegment.objects.create(
            route=self.route1,
            start_time=self.now.replace(hour=10, minute=5, second=0, microsecond=0),
            end_time=self.now.replace(hour=10, minute=15, second=0, microsecond=0),
            duration_seconds=600.0, # Same duration
            distance_meters=800.0,  # Different distance
            num_points=40,
            average_speed_mps=800.0/600.0,
            segment_geometry=LineString((1,1), (2,2), srid=4326)
        )
        # Segment 3 (Route 2, Hour 9) - This will be the top route by count
        DetectedSegment.objects.create(
            route=self.route2,
            start_time=self.now.replace(hour=9, minute=30, second=0, microsecond=0),
            end_time=self.now.replace(hour=9, minute=40, second=0, microsecond=0),
            duration_seconds=600.0, 
            distance_meters=500.0,
            num_points=60,
            average_speed_mps=500.0/600.0,
            segment_geometry=LineString((2,2), (3,3), srid=4326)
        )
        # Segment 4 (Route 2, Hour 11)
        DetectedSegment.objects.create(
            route=self.route2,
            start_time=self.now.replace(hour=11, minute=0, second=0, microsecond=0),
            end_time=self.now.replace(hour=11, minute=5, second=0, microsecond=0),
            duration_seconds=300.0,
            distance_meters=200.0,
            num_points=20,
            average_speed_mps=200.0/300.0,
            segment_geometry=LineString((3,3), (4,4), srid=4326)
        )
        # Segment 5 (Route 2, Hour 11, another one for R2)
        DetectedSegment.objects.create(
            route=self.route2, # Route 2 gets 3 segments
            start_time=self.now.replace(hour=11, minute=10, second=0, microsecond=0),
            end_time=self.now.replace(hour=11, minute=18, second=0, microsecond=0),
            duration_seconds=480.0,
            distance_meters=250.0,
            num_points=25,
            average_speed_mps=250.0/480.0,
            segment_geometry=LineString((4,4), (5,5), srid=4326)
        )
        # Segment 6 (No Route, Hour 14)
        DetectedSegment.objects.create(
            route=None,
            start_time=self.now.replace(hour=14, minute=0, second=0, microsecond=0),
            end_time=self.now.replace(hour=14, minute=12, second=0, microsecond=0),
            duration_seconds=720.0,
            distance_meters=1200.0,
            num_points=70,
            average_speed_mps=1200.0/720.0,
            segment_geometry=LineString((5,5), (6,6), srid=4326)
        )
        # Segment 7 (Route 3, Hour 10) - Only one segment for Route 3
        DetectedSegment.objects.create(
            route=self.route3,
            start_time=self.now.replace(hour=10, minute=0, second=0, microsecond=0),
            end_time=self.now.replace(hour=10, minute=20, second=0, microsecond=0),
            duration_seconds=1200.0,
            distance_meters=3000.0,
            num_points=100,
            average_speed_mps=3000.0/1200.0,
            segment_geometry=LineString((6,6), (7,7), srid=4326)
        )
        
        # Total: 7 segments
        # Route1: 2 segments
        # Route2: 3 segments
        # Route3: 1 segment
        # No Route: 1 segment

        # Expected overall stats:
        # Total Segments: 7
        # Durations: 600, 600, 600, 300, 480, 720, 1200. Sum = 4500. Avg = 4500/7 = 642.857
        # Distances: 1000, 800, 500, 200, 250, 1200, 3000. Sum = 6950. Avg = 6950/7 = 992.857 (Total Dist for report)
        # Num Points: 50, 40, 60, 20, 25, 70, 100. Sum = 365. Avg = 365/7 = 52.14
        # Avg Speeds: 1.666, 1.333, 0.833, 0.666, 0.520, 1.666, 2.5. Sum = 9.184. Avg = 9.184/7 = 1.312

    def test_no_segments_report(self):
        DetectedSegment.objects.all().delete()
        out = StringIO()
        call_command('report_segments', stdout=out)
        self.assertIn("No detected segments found in the database. Nothing to report.", out.getvalue())

    def test_report_with_segments_default_top_n(self):
        out = StringIO()
        call_command('report_segments', stdout=out) # Default top_n is 5
        output = out.getvalue()

        # Overall Statistics
        self.assertIn("--- Overall Segment Statistics ---", output)
        self.assertIn("Total Detected Segments: 7", output)
        self.assertIn("Average Segment Duration: 642.86 seconds", output) # 4500/7
        self.assertIn("Average Segment Speed: 1.31 m/s", output) # 9.184 / 7 (approx)
        self.assertIn("Average Points per Segment: 52.14", output) # 365/7
        self.assertIn("Total Distance Covered by Segments: 6950.00 meters", output)

        # Top N Routes (default N=5)
        self.assertIn("--- Top 5 Routes by Segment Count ---", output)
        # Order: Route2 (3), Route1 (2), Route3 (1), No Route (1)
        self.assertIn(f"1. Route ID {self.route2.id} ({self.route2.main_to_sec} / {self.route2.sec_to_main}, Sign: {self.route2.sign}, Code: {self.route2.code}): 3 segments", output)
        self.assertIn(f"2. Route ID {self.route1.id} ({self.route1.main_to_sec} / {self.route1.sec_to_main}, Sign: {self.route1.sign}, Code: {self.route1.code}): 2 segments", output)
        self.assertIn(f"3. Route ID {self.route3.id} ({self.route3.main_to_sec} / {self.route3.sec_to_main}, Sign: {self.route3.sign}, Code: {self.route3.code}): 1 segments", output) # Note: "1 segments" is current output from command
        self.assertIn("4. Segments with no associated route: 1 segments", output)

        # Hourly Distribution
        self.assertIn("--- Segment Distribution by Start Hour ---", output)
        self.assertIn("Hour 09: 2 segments", output) # Seg 1 (R1), Seg 3 (R2)
        self.assertIn("Hour 10: 2 segments", output) # Seg 2 (R1), Seg 7 (R3)
        self.assertIn("Hour 11: 2 segments", output) # Seg 4 (R2), Seg 5 (R2)
        self.assertIn("Hour 14: 1 segments", output) # Seg 6 (No Route)
        self.assertIn("Hour 00: 0 segments", output) # Check one empty hour

    def test_report_with_custom_top_n_routes(self):
        out = StringIO()
        call_command('report_segments', top_n_routes=2, stdout=out)
        output = out.getvalue()

        self.assertIn("--- Top 2 Routes by Segment Count ---", output)
        self.assertIn(f"1. Route ID {self.route2.id}", output) # Route 2 has 3
        self.assertIn(": 3 segments", output)
        self.assertIn(f"2. Route ID {self.route1.id}", output) # Route 1 has 2
        self.assertIn(": 2 segments", output)
        # Route3 should not be listed in the top 2
        self.assertNotIn(f"Route ID {self.route3.id}", output.split("--- Segment Distribution by Start Hour ---")[0]) # Check only top N section

    def test_report_segments_with_no_route_prominence(self):
        """ Test that 'Segments with no associated route' is listed correctly, especially if it's in top N """
        # Delete all but the "no route" segment and one "route1" segment
        DetectedSegment.objects.filter(route=self.route2).delete()
        DetectedSegment.objects.filter(route=self.route3).delete()
        # Keep one from route1 (seg1, hour 9), and the one with no route (seg6, hour 14)
        # Delete seg2 (from route1) to make route1 have 1 segment
        DetectedSegment.objects.filter(pk=DetectedSegment.objects.get(route=self.route1, start_time__hour=10).pk).delete()

        # Now: Route1 has 1 segment, No Route has 1 segment.
        # Total 2 segments.
        
        out = StringIO()
        call_command('report_segments', top_n_routes=3, stdout=out) # top_n = 3
        output = out.getvalue()

        self.assertIn("Total Detected Segments: 2", output) # Seg1 (R1), Seg6 (None)
        # Expected route counts: Route1 (1), No Route (1)
        # The order between route1 and "no route" might vary based on internal sorting if counts are equal.
        # The report command's current logic sorts by segment_count DESC, then by route_id ASC (None might be first or last)
        # Let's check that both are present in the top N list
        
        top_n_section = output.split("--- Top 3 Routes by Segment Count ---")[1].split("--- Segment Distribution by Start Hour ---")[0]

        self.assertIn(f"Route ID {self.route1.id}", top_n_section)
        self.assertIn(": 1 segments", top_n_section)
        self.assertIn("Segments with no associated route: 1 segments", top_n_section)

        # Check hourly distribution for these two remaining segments
        self.assertIn("Hour 09: 1 segments", output) # Seg1
        self.assertIn("Hour 14: 1 segments", output) # Seg6 (No Route)
        self.assertIn("Hour 10: 0 segments", output)

# To run these tests:
# python manage.py test geodjango.core.tests.test_commands.ReportSegmentsCommandTests
# or if your apps are setup:
# python manage.py test core.tests.test_commands.ReportSegmentsCommandTests
