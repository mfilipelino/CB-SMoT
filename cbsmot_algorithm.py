#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CB-SMoT (Clustering-Based Stops and Moves of Trajectories) Algorithm

This is an implementation of the CB-SMoT algorithm for discovering interesting places
in trajectories based on the variation of speed. The algorithm was proposed by:

Palma, A. T., Bogorny, V., Kuijpers, B., & Alvares, L. O. (2008). 
"A clustering-based approach for discovering interesting places in trajectories." 
In Proceedings of the 2008 ACM symposium on Applied computing (pp. 863-868).

Alvares, L. O., Bogorny, V., Kuijpers, B., de Macedo, J. A. F., Moelans, B., & Vaisman, A. (2007).
"A model for enriching trajectories with semantic geographical information."
In Proceedings of the 15th annual ACM international symposium on Advances in geographic information systems (pp. 1-8).

This file contains the core algorithm functions without Django dependencies, extracted from the
original Django project for better testability and reuse.
"""

import math
from math import radians, cos, sin, asin, sqrt


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


def distance_absolute(a, b):
    """Calculate distance between two points in meters"""
    return haversine(a.x, a.y, b.x, b.y) * 1000


def average_speed(dist, delta_time):
    """Calculate average speed in m/s"""
    return dist / delta_time


def delta_time(a, b):
    """Calculate time difference in seconds between two datetime objects"""
    return (a - b).total_seconds()


class Stop(object):
    """Represents a stop in a trajectory"""
    def __init__(self):
        self.trajectorys = []
        self.init_time = None
        self.delta_time = 0.0
        self.last_time = None
        self.dist = 0.0

    def add(self, trajectory, dist):
        """Add a trajectory point to this stop"""
        self.dist += dist
        if self.init_time is None:
            self.init_time = trajectory.datetime
        else:
            self.delta_time += delta_time(trajectory.datetime, self.last_time)
        self.trajectorys.append(trajectory)
        self.last_time = trajectory.datetime


def cbsmot(trajectorys, max_average_speed, min_time):
    """
    CB-SMoT algorithm implementation for detecting stops in a trajectory.
    
    The algorithm works by analyzing the speed between consecutive points in a trajectory.
    When the speed falls below a threshold (max_average_speed) for a minimum duration (min_time),
    the algorithm identifies this segment as a stop.
    
    The algorithm is based on the papers:
    - Palma et al. (2008) "A clustering-based approach for discovering interesting places in trajectories"
    - Alvares et al. (2007) "A model for enriching trajectories with semantic geographical information"
    
    Parameters:
    trajectorys - List of trajectory points with datetime and point attributes
                 Each trajectory point must have:
                 - datetime: timestamp of the point
                 - point: object with x and y attributes (longitude and latitude)
    max_average_speed - Maximum average speed (m/s) to consider a stop
                       Points with speed below this threshold are candidates for stops
    min_time - Minimum time (seconds) to consider a valid stop
              Only segments where the object stayed for at least this duration are considered stops
    
    Returns:
    List of Stop objects, each containing:
    - trajectorys: list of trajectory points in this stop
    - init_time: timestamp when the stop started
    - last_time: timestamp when the stop ended
    - delta_time: duration of the stop in seconds
    - dist: total distance covered during the stop
    """
    if not trajectorys:
        return []
        
    stops = []
    previous = trajectorys[0]
    stop = None
    
    for trajectory in trajectorys[1:]:
        dt = delta_time(trajectory.datetime, previous.datetime)
        dist = distance_absolute(trajectory.point, previous.point)
        
        # Avoid division by zero
        if dt > 0:
            average_s = average_speed(dist, dt)
        else:
            average_s = float('inf')
            
        if dt < 20.0 and average_s < max_average_speed:
            if stop is None:
                stop = Stop()
                stop.add(previous, 0)
            stop.add(trajectory, dist)
        else:
            if stop and stop.delta_time > min_time:
                stops.append(stop)
            stop = None
        previous = trajectory
        
    # Don't forget to add the last stop if it meets the criteria
    if stop and stop.delta_time > min_time:
        stops.append(stop)
        
    return stops