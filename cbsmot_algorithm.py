#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CB-SMoT algorithm implementation extracted from the Django project.
This file contains the core algorithm functions without Django dependencies.
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
    CB-SMoT algorithm implementation
    
    Parameters:
    trajectorys - List of trajectory points with datetime and point attributes
    max_average_speed - Maximum average speed (m/s) to consider a stop
    min_time - Minimum time (seconds) to consider a valid stop
    
    Returns:
    List of Stop objects
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