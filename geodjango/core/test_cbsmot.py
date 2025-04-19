# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.contrib.gis.geos import Point
from datetime import datetime, timedelta
from .models import Vehicle, Trajectory
from core.management.commands.tests import haversine, distance_absolute, average_speed, delta_time, Stop, cbsmot


class HaversineTestCase(TestCase):
    def test_haversine_distance_calculation(self):
        """Test that haversine correctly calculates distance between two points"""
        # São Paulo coordinates
        lon1, lat1 = -46.633309, -23.550520  # São Paulo city center
        lon2, lat2 = -46.634000, -23.551000  # A nearby point
        
        # Calculate distance
        distance = haversine(lon1, lat1, lon2, lat2)
        
        # The distance should be small (less than 1 km)
        self.assertLess(distance, 1.0)
        self.assertGreater(distance, 0.0)
    
    def test_haversine_known_distance(self):
        """Test haversine with known distance between two cities"""
        # São Paulo and Rio de Janeiro coordinates (approximate)
        lon1, lat1 = -46.633309, -23.550520  # São Paulo
        lon2, lat2 = -43.172897, -22.906847  # Rio de Janeiro
        
        # Calculate distance
        distance = haversine(lon1, lat1, lon2, lat2)
        
        # The distance should be around 360-370 km (as the crow flies)
        self.assertGreater(distance, 350.0)
        self.assertLess(distance, 380.0)


class DistanceAbsoluteTestCase(TestCase):
    def test_distance_absolute_calculation(self):
        """Test that distance_absolute correctly calculates distance between two points"""
        # Create two points
        point1 = Point(-46.633309, -23.550520)  # x=longitude, y=latitude
        point2 = Point(-46.634000, -23.551000)
        
        # Calculate distance in meters
        distance = distance_absolute(point1, point2)
        
        # The distance should be small (less than 1000 meters)
        self.assertLess(distance, 1000.0)
        self.assertGreater(distance, 0.0)


class AverageSpeedTestCase(TestCase):
    def test_average_speed_calculation(self):
        """Test that average_speed correctly calculates speed"""
        # Distance in meters, time in seconds
        distance = 100.0  # 100 meters
        time = 20.0  # 20 seconds
        
        # Calculate speed (m/s)
        speed = average_speed(distance, time)
        
        # The speed should be 5 m/s
        self.assertEqual(speed, 5.0)


class DeltaTimeTestCase(TestCase):
    def test_delta_time_calculation(self):
        """Test that delta_time correctly calculates time difference"""
        # Create two datetime objects
        time1 = datetime(2020, 1, 1, 12, 0, 0)  # 12:00:00
        time2 = datetime(2020, 1, 1, 12, 0, 30)  # 12:00:30
        
        # Calculate time difference in seconds
        dt = delta_time(time2, time1)
        
        # The difference should be 30 seconds
        self.assertEqual(dt, 30.0)


class StopTestCase(TestCase):
    def test_stop_initialization(self):
        """Test that Stop is correctly initialized"""
        # Create a Stop object
        stop = Stop()
        
        # Check initial values
        self.assertEqual(stop.trajectorys, [])
        self.assertIsNone(stop.init_time)
        self.assertEqual(stop.delta_time, 0.0)
        self.assertIsNone(stop.last_time)
        self.assertEqual(stop.dist, 0.0)
    
    def test_stop_add_first_trajectory(self):
        """Test adding the first trajectory to a Stop"""
        # Create a Stop object
        stop = Stop()
        
        # Create a trajectory
        vehicle = Vehicle(prefix=12345, acessible=True)
        trajectory = Trajectory(
            latitude=-23.550520,
            longitude=-46.633309,
            datetime=datetime(2020, 1, 1, 12, 0, 0),
            vehicle=vehicle,
            point=Point(-46.633309, -23.550520)
        )
        
        # Add trajectory to stop
        stop.add(trajectory, 0.0)
        
        # Check values
        self.assertEqual(stop.trajectorys, [trajectory])
        self.assertEqual(stop.init_time, trajectory.datetime)
        self.assertEqual(stop.delta_time, 0.0)
        self.assertEqual(stop.last_time, trajectory.datetime)
        self.assertEqual(stop.dist, 0.0)
    
    def test_stop_add_subsequent_trajectory(self):
        """Test adding a subsequent trajectory to a Stop"""
        # Create a Stop object
        stop = Stop()
        
        # Create a vehicle
        vehicle = Vehicle(prefix=12345, acessible=True)
        
        # Create first trajectory
        trajectory1 = Trajectory(
            latitude=-23.550520,
            longitude=-46.633309,
            datetime=datetime(2020, 1, 1, 12, 0, 0),
            vehicle=vehicle,
            point=Point(-46.633309, -23.550520)
        )
        
        # Create second trajectory
        trajectory2 = Trajectory(
            latitude=-23.551000,
            longitude=-46.634000,
            datetime=datetime(2020, 1, 1, 12, 0, 30),
            vehicle=vehicle,
            point=Point(-46.634000, -23.551000)
        )
        
        # Add trajectories to stop
        stop.add(trajectory1, 0.0)
        stop.add(trajectory2, 100.0)  # 100 meters distance
        
        # Check values
        self.assertEqual(stop.trajectorys, [trajectory1, trajectory2])
        self.assertEqual(stop.init_time, trajectory1.datetime)
        self.assertEqual(stop.delta_time, 30.0)  # 30 seconds difference
        self.assertEqual(stop.last_time, trajectory2.datetime)
        self.assertEqual(stop.dist, 100.0)


class CBSMoTTestCase(TestCase):
    def test_cbsmot_identifies_stops(self):
        """Test that cbsmot correctly identifies stops in a trajectory"""
        # Create a vehicle
        vehicle = Vehicle(prefix=12345, acessible=True)
        
        # Create a list of trajectories representing a vehicle that stops for a while
        trajectories = []
        
        # Starting time
        base_time = datetime(2020, 1, 1, 12, 0, 0)
        
        # Moving phase (5 points, 10 seconds apart, moving at about 5 m/s)
        for i in range(5):
            time = base_time + timedelta(seconds=i*10)
            # Moving along a straight line
            lat = -23.550520 + (i * 0.0001)  # Small increment in latitude
            lon = -46.633309 + (i * 0.0001)  # Small increment in longitude
            trajectory = Trajectory(
                id=i+1,
                latitude=lat,
                longitude=lon,
                datetime=time,
                vehicle=vehicle,
                point=Point(lon, lat)
            )
            trajectories.append(trajectory)
        
        # Stopped phase (10 points, 10 seconds apart, barely moving - simulating a stop)
        for i in range(10):
            time = base_time + timedelta(seconds=50 + i*10)  # Continuing from last time
            # Very small random-like movements around a point (simulating GPS jitter)
            lat = -23.550920 + (i % 3) * 0.000005  # Tiny variations
            lon = -23.633709 + (i % 3) * 0.000005  # Tiny variations
            trajectory = Trajectory(
                id=i+6,
                latitude=lat,
                longitude=lon,
                datetime=time,
                vehicle=vehicle,
                point=Point(lon, lat)
            )
            trajectories.append(trajectory)
        
        # Moving again (5 points, 10 seconds apart, moving at about 5 m/s)
        for i in range(5):
            time = base_time + timedelta(seconds=150 + i*10)  # Continuing from last time
            # Moving along a straight line
            lat = -23.550920 + (i * 0.0001)  # Small increment in latitude
            lon = -23.633709 + (i * 0.0001)  # Small increment in longitude
            trajectory = Trajectory(
                id=i+16,
                latitude=lat,
                longitude=lon,
                datetime=time,
                vehicle=vehicle,
                point=Point(lon, lat)
            )
            trajectories.append(trajectory)
        
        # Run CB-SMoT algorithm
        stops = cbsmot(trajectories, min_time=60, max_average_speed=0.5)
        
        # We should have identified one stop
        self.assertEqual(len(stops), 1)
        
        # The stop should have a duration of at least 60 seconds
        self.assertGreaterEqual(stops[0].delta_time, 60.0)
        
        # The stop should contain multiple trajectory points
        self.assertGreater(len(stops[0].trajectorys), 1)