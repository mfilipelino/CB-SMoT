# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.gis.db import models


class Route(models.Model):
    code = models.IntegerField()
    sign = models.IntegerField()
    direction = models.IntegerField()
    main_to_sec = models.CharField(max_length=100)
    sec_to_main = models.CharField(max_length=100)
    type_route = models.CharField(max_length=10)


class StopBus(models.Model):
    latitude = models.DecimalField(max_digits=11, decimal_places=9)
    longitude = models.DecimalField(max_digits=11, decimal_places=9)
    point = models.PointField(srid=4326, null=True)
    poly = models.PolygonField(srid=4326, null=True)
    code = models.IntegerField()
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)


class Vehicle(models.Model):
    route = models.ForeignKey(Route, null=True, on_delete=models.SET_NULL)
    acessible = models.BooleanField()
    prefix = models.IntegerField()


class Trajectory(models.Model):
    latitude = models.DecimalField(max_digits=11, decimal_places=9)
    longitude = models.DecimalField(max_digits=11, decimal_places=9)
    datetime = models.DateTimeField()
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    point = models.PointField(srid=4326, null=True)


class DetectedSegment(models.Model):
    vehicle = models.ForeignKey(Vehicle, null=True, on_delete=models.SET_NULL)
    route = models.ForeignKey(Route, null=True, on_delete=models.SET_NULL)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_seconds = models.FloatField()
    distance_meters = models.FloatField()
    num_points = models.IntegerField()
    average_speed_mps = models.FloatField()
    trajectory_points = models.ManyToManyField(Trajectory)
    segment_geometry = models.LineStringField(srid=4326, null=True)
