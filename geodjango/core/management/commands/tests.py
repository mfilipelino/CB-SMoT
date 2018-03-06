from django.core.management.base import BaseCommand
from core.service import populate_routes, populate_stops_bus, populate_vehicles
from core.models import Vehicle, Trajectory, Route, StopBus
import math
from math import radians, cos, sin, asin, sqrt


def haversine(lon1, lat1, lon2, lat2):

    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r


def distance_absolute(a, b):
    return haversine(a.x, a.y, b.x, b.y) * 1000


def average_speed(dist, delta_time):
    return dist / delta_time


def delta_time(a, b):
    return (a - b).total_seconds()


class Stop(object):
    def __init__(self):
        self.trajectorys = []
        self.init_time = None
        self.delta_time = 0.0
        self.last_time = None
        self.dist = 0.0

    def add(self, trajectory, dist):
        self.dist += dist
        if self.init_time is None:
            self.init_time = trajectory.datetime
        else:
            self.delta_time += delta_time(trajectory.datetime, self.last_time)
        self.trajectorys.append(trajectory)
        self.last_time = trajectory.datetime


def cbsmot(tracjectorys, min_time, max_average_speed):
    stops = []
    previous = tracjectorys[0]
    stop = None
    for trajectory in tracjectorys[1:]:
        dt = delta_time(trajectory.datetime, previous.datetime)
        dist = distance_absolute(trajectory.point, previous.point)
        average_s = average_speed(dist, dt)
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
    return stops


def print_example(tracjectorys):
    anterior = tracjectorys[0]
    soma = 0
    for t in tracjectorys[1:]:
        dx = abs(anterior.point.x - t.point.x)
        dy = abs(anterior.point.y - t.point.y)
        dist = distance_absolute(anterior.point, t.point)
        ax = anterior.point.x
        tx = t.point.x
        ay = anterior.point.y
        ty = t.point.y
        dt = (t.datetime - anterior.datetime).total_seconds()
        vm = dist / dt
        print('id:{:<6} vm:{:<14} dist:{:<14} dx:{:<14} dy:{:<14} dt:{:<14} pa: {:<15},{:<15} pt: {:<15},{:<15}'.format(
            t.id, vm, dist, dx, dy, dt, ay, ax, ty, tx
        ))
        soma += dy + dx
        anterior = t
    print(soma)
    print(soma / (tracjectorys[0].datetime - anterior.datetime).total_seconds())


class Command(BaseCommand):
    def handle(self, *args, **options):
        tracjectorys = Trajectory.objects.filter(vehicle_id=13).order_by('datetime')
        stops = cbsmot(tracjectorys, min_time=600, max_average_speed=1.0)
        # print_example(tracjectorys)

        for stop in stops:

            fmt = '{:<9},{:<9}'.format(
                stop.trajectorys[0].point.y,
                stop.trajectorys[0].point.x,
            )
            print(fmt)