# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
from datetime import datetime
from unittest.mock import MagicMock
from core.management.commands.tests import haversine, distance_absolute, average_speed, delta_time, Stop


class TestHaversine(unittest.TestCase):
    """Test the haversine function"""
    
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


class TestDistanceAbsolute(unittest.TestCase):
    """Test the distance_absolute function"""
    
    def test_distance_absolute_calculation(self):
        """Test that distance_absolute correctly calculates distance between two points"""
        # Create two mock points
        point1 = MagicMock()
        point1.x = -46.633309
        point1.y = -23.550520
        
        point2 = MagicMock()
        point2.x = -46.634000
        point2.y = -23.551000
        
        # Calculate distance in meters
        distance = distance_absolute(point1, point2)
        
        # The distance should be small (less than 1000 meters)
        self.assertLess(distance, 1000.0)
        self.assertGreater(distance, 0.0)


class TestAverageSpeed(unittest.TestCase):
    """Test the average_speed function"""
    
    def test_average_speed_calculation(self):
        """Test that average_speed correctly calculates speed"""
        # Distance in meters, time in seconds
        distance = 100.0  # 100 meters
        time = 20.0  # 20 seconds
        
        # Calculate speed (m/s)
        speed = average_speed(distance, time)
        
        # The speed should be 5 m/s
        self.assertEqual(speed, 5.0)


class TestDeltaTime(unittest.TestCase):
    """Test the delta_time function"""
    
    def test_delta_time_calculation(self):
        """Test that delta_time correctly calculates time difference"""
        # Create two datetime objects
        time1 = datetime(2020, 1, 1, 12, 0, 0)  # 12:00:00
        time2 = datetime(2020, 1, 1, 12, 0, 30)  # 12:00:30
        
        # Calculate time difference in seconds
        dt = delta_time(time2, time1)
        
        # The difference should be 30 seconds
        self.assertEqual(dt, 30.0)


class TestStop(unittest.TestCase):
    """Test the Stop class"""
    
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
        
        # Create a mock trajectory
        trajectory = MagicMock()
        trajectory.datetime = datetime(2020, 1, 1, 12, 0, 0)
        
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
        
        # Create first trajectory
        trajectory1 = MagicMock()
        trajectory1.datetime = datetime(2020, 1, 1, 12, 0, 0)
        
        # Create second trajectory
        trajectory2 = MagicMock()
        trajectory2.datetime = datetime(2020, 1, 1, 12, 0, 30)
        
        # Add trajectories to stop
        stop.add(trajectory1, 0.0)
        stop.add(trajectory2, 100.0)  # 100 meters distance
        
        # Check values
        self.assertEqual(stop.trajectorys, [trajectory1, trajectory2])
        self.assertEqual(stop.init_time, trajectory1.datetime)
        self.assertEqual(stop.delta_time, 30.0)  # 30 seconds difference
        self.assertEqual(stop.last_time, trajectory2.datetime)
        self.assertEqual(stop.dist, 100.0)


if __name__ == '__main__':
    unittest.main()