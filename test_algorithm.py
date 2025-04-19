#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the CB-SMoT algorithm functions directly without Django dependencies.
"""

import unittest
import math
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Import the algorithm functions directly from the source file
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'geodjango'))
from geodjango.core.management.commands.tests import haversine, distance_absolute, average_speed, delta_time, Stop, cbsmot


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
    
    def test_stop_add_trajectory(self):
        """Test adding trajectories to a Stop"""
        # Create a Stop object
        stop = Stop()
        
        # Create mock trajectories
        trajectory1 = MagicMock()
        trajectory1.datetime = datetime(2020, 1, 1, 12, 0, 0)
        
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


class TestCBSMoT(unittest.TestCase):
    """Test the CB-SMoT algorithm"""
    
    def test_cbsmot_with_no_trajectories(self):
        """Test that CB-SMoT returns empty list when no trajectories are provided"""
        # Call the function with empty list
        result = cbsmot([], 10, 60)
        
        # The result should be an empty list
        self.assertEqual(result, [])
    
    def test_cbsmot_with_stationary_trajectories(self):
        """Test that CB-SMoT detects stops when trajectories are stationary"""
        # Create mock trajectories that are close together (stationary)
        trajectories = []
        base_time = datetime(2020, 1, 1, 12, 0, 0)
        
        # Create 10 trajectories very close together, 10 seconds apart
        for i in range(10):
            trajectory = MagicMock()
            point = MagicMock()
            # Set x, y coordinates to simulate minimal movement (1m between each point)
            point.x = -46.633309 + (i * 0.00001)  # Approximately 1m per 0.00001 degree
            point.y = -23.550520
            trajectory.point = point
            trajectory.datetime = base_time + timedelta(seconds=i*10)
            trajectories.append(trajectory)
        
        # Call the function with stationary trajectories
        # min_speed = 1 m/s, min_time = 60 seconds
        result = cbsmot(trajectories, 1, 60)
        
        # The result should contain at least one stop
        self.assertGreater(len(result), 0)
        
        # Check the stop properties
        stop = result[0]
        self.assertGreaterEqual(len(stop.trajectorys), 7)  # At least 7 trajectories (70 seconds)
        self.assertEqual(stop.init_time, trajectories[0].datetime)
        self.assertGreaterEqual(stop.delta_time, 60)  # At least 60 seconds


if __name__ == '__main__':
    unittest.main()