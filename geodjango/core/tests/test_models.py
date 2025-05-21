# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.gis.geos import LineString, Point

from geodjango.core.models import DetectedSegment, Vehicle, Route, Trajectory

class DetectedSegmentModelTests(TestCase):

    def setUp(self):
        # Create a Route
        self.route = Route.objects.create(
            code=101,
            sign=1,
            direction=1,
            main_to_sec="Main St to Second St",
            sec_to_main="Second St to Main St",
            type_route="Urban"
        )

        # Create a Vehicle
        self.vehicle = Vehicle.objects.create(
            route=self.route,
            acessible=True,
            prefix=12345
        )

        # Create Trajectory points
        self.now = timezone.now()
        self.tp1 = Trajectory.objects.create(
            latitude=10.0, longitude=20.0, 
            datetime=self.now - datetime.timedelta(seconds=30),
            vehicle=self.vehicle,
            point=Point(20.0, 10.0, srid=4326) # lon, lat
        )
        self.tp2 = Trajectory.objects.create(
            latitude=10.001, longitude=20.001,
            datetime=self.now - datetime.timedelta(seconds=20),
            vehicle=self.vehicle,
            point=Point(20.001, 10.001, srid=4326)
        )
        self.tp3 = Trajectory.objects.create(
            latitude=10.002, longitude=20.002,
            datetime=self.now - datetime.timedelta(seconds=10),
            vehicle=self.vehicle,
            point=Point(20.002, 10.002, srid=4326)
        )
        
        self.trajectory_list = [self.tp1, self.tp2, self.tp3]

        # Create a LineString for the segment geometry
        self.segment_geometry = LineString(
            (self.tp1.point.x, self.tp1.point.y),
            (self.tp2.point.x, self.tp2.point.y),
            (self.tp3.point.x, self.tp3.point.y),
            srid=4326
        )

    def test_create_detected_segment(self):
        """Test basic creation and retrieval of a DetectedSegment instance."""
        start_time = self.now - datetime.timedelta(seconds=30)
        end_time = self.now - datetime.timedelta(seconds=10)
        duration = (end_time - start_time).total_seconds()
        distance = 150.5
        num_points = 3
        avg_speed = distance / duration if duration > 0 else 0

        segment = DetectedSegment.objects.create(
            vehicle=self.vehicle,
            route=self.route,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            distance_meters=distance,
            num_points=num_points,
            average_speed_mps=avg_speed,
            segment_geometry=self.segment_geometry
        )
        segment.trajectory_points.set(self.trajectory_list)

        # Retrieve the segment
        retrieved_segment = DetectedSegment.objects.get(id=segment.id)

        self.assertEqual(retrieved_segment.vehicle, self.vehicle)
        self.assertEqual(retrieved_segment.route, self.route)
        self.assertEqual(retrieved_segment.start_time, start_time)
        self.assertEqual(retrieved_segment.end_time, end_time)
        self.assertAlmostEqual(retrieved_segment.duration_seconds, duration)
        self.assertAlmostEqual(retrieved_segment.distance_meters, distance)
        self.assertEqual(retrieved_segment.num_points, num_points)
        self.assertAlmostEqual(retrieved_segment.average_speed_mps, avg_speed)
        
        self.assertTrue(retrieved_segment.segment_geometry.equals_exact(self.segment_geometry, tolerance=0.00001))
        
        self.assertEqual(retrieved_segment.trajectory_points.count(), 3)
        self.assertIn(self.tp1, retrieved_segment.trajectory_points.all())
        self.assertIn(self.tp2, retrieved_segment.trajectory_points.all())
        self.assertIn(self.tp3, retrieved_segment.trajectory_points.all())

    def test_relationships(self):
        """Test the relationships of the DetectedSegment model."""
        segment = DetectedSegment.objects.create(
            vehicle=self.vehicle,
            route=self.route,
            start_time=self.now,
            end_time=self.now + datetime.timedelta(seconds=60),
            duration_seconds=60.0,
            distance_meters=100.0,
            num_points=10,
            average_speed_mps=1.66,
            segment_geometry=LineString((0,0), (1,1), srid=4326)
        )
        segment.trajectory_points.set(self.trajectory_list)

        self.assertEqual(segment.vehicle.prefix, self.vehicle.prefix)
        self.assertEqual(segment.route.code, self.route.code)
        self.assertEqual(segment.trajectory_points.count(), len(self.trajectory_list))
        for tp in self.trajectory_list:
            self.assertIn(tp, segment.trajectory_points.all())

    def test_segment_without_route(self):
        """Test creating a segment without an associated route."""
        segment = DetectedSegment.objects.create(
            vehicle=self.vehicle,
            route=None, # No route
            start_time=self.now,
            end_time=self.now + datetime.timedelta(seconds=60),
            duration_seconds=60.0,
            distance_meters=100.0,
            num_points=10,
            average_speed_mps=1.66,
            segment_geometry=LineString((0,0), (1,1), srid=4326)
        )
        retrieved_segment = DetectedSegment.objects.get(id=segment.id)
        self.assertIsNone(retrieved_segment.route)
        self.assertEqual(retrieved_segment.vehicle, self.vehicle)

    def test_segment_without_vehicle(self):
        """Test creating a segment without an associated vehicle (if allowed by model)."""
        # Note: The model sets on_delete=models.SET_NULL for vehicle, so it's allowed.
        segment = DetectedSegment.objects.create(
            vehicle=None, # No vehicle
            route=self.route,
            start_time=self.now,
            end_time=self.now + datetime.timedelta(seconds=60),
            duration_seconds=60.0,
            distance_meters=100.0,
            num_points=10,
            average_speed_mps=1.66,
            segment_geometry=LineString((0,0), (1,1), srid=4326)
        )
        retrieved_segment = DetectedSegment.objects.get(id=segment.id)
        self.assertIsNone(retrieved_segment.vehicle)
        self.assertEqual(retrieved_segment.route, self.route)

    def test_segment_geometry_srid(self):
        """Test the SRID of the segment_geometry field."""
        segment = DetectedSegment.objects.create(
            start_time=self.now,
            end_time=self.now + datetime.timedelta(seconds=60),
            segment_geometry=self.segment_geometry  # Uses SRID 4326 from setUp
        )
        retrieved_segment = DetectedSegment.objects.get(id=segment.id)
        self.assertEqual(retrieved_segment.segment_geometry.srid, 4326)

    def test_segment_with_no_trajectory_points(self):
        """Test creating a segment and not adding any trajectory points yet."""
        segment = DetectedSegment.objects.create(
            vehicle=self.vehicle,
            route=self.route,
            start_time=self.now,
            end_time=self.now + datetime.timedelta(seconds=60),
            duration_seconds=60.0,
            distance_meters=100.0,
            num_points=0, # Explicitly 0 points
            average_speed_mps=1.66,
            segment_geometry=LineString((0,0), (1,1), srid=4326)
        )
        # No trajectory_points.set() called
        retrieved_segment = DetectedSegment.objects.get(id=segment.id)
        self.assertEqual(retrieved_segment.trajectory_points.count(), 0)
        self.assertEqual(retrieved_segment.num_points, 0)

    def test_on_delete_vehicle(self):
        """Test that DetectedSegment.vehicle is set to NULL when Vehicle is deleted."""
        segment = DetectedSegment.objects.create(vehicle=self.vehicle, route=self.route, start_time=self.now, end_time=self.now)
        self.vehicle.delete()
        segment.refresh_from_db()
        self.assertIsNone(segment.vehicle)

    def test_on_delete_route(self):
        """Test that DetectedSegment.route is set to NULL when Route is deleted."""
        segment = DetectedSegment.objects.create(vehicle=self.vehicle, route=self.route, start_time=self.now, end_time=self.now)
        self.route.delete()
        segment.refresh_from_db()
        self.assertIsNone(segment.route)

    def test_on_delete_trajectory_point(self):
        """Test that deleting a Trajectory point does not delete the segment, but it might affect ManyToManyField integrity if not handled well by app logic."""
        segment = DetectedSegment.objects.create(vehicle=self.vehicle, route=self.route, start_time=self.now, end_time=self.now)
        segment.trajectory_points.set(self.trajectory_list)
        self.assertEqual(segment.trajectory_points.count(), 3)
        
        # Deleting a trajectory point that is part of a segment
        self.tp1.delete()
        segment.refresh_from_db() # Refresh to see changes in ManyToMany
        
        # The segment itself should still exist
        self.assertTrue(DetectedSegment.objects.filter(id=segment.id).exists())
        # The ManyToManyField should reflect the deletion
        self.assertEqual(segment.trajectory_points.count(), 2)
        self.assertNotIn(self.tp1, segment.trajectory_points.all())
        self.assertIn(self.tp2, segment.trajectory_points.all())

        # If the application logic relies on num_points field, it would now be out of sync
        # This test just verifies DB behavior. Application logic for consistency is separate.
        # For example, num_points was set at creation and is not auto-updated by DB.
        # self.assertEqual(segment.num_points, 2) # This would fail unless num_points is also updated
