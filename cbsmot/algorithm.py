"""Core CB-SMoT algorithm. Pure Python, no I/O, no framework dependencies.

The algorithm consumes an iterable of objects carrying a `.datetime`
attribute and a `.point` attribute whose `.x` / `.y` are longitude and
latitude in decimal degrees.
"""

from math import asin, cos, radians, sin, sqrt


def haversine(lon1, lat1, lon2, lat2):
    """Great-circle distance between two lon/lat points, in kilometers."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r


def distance_absolute(a, b):
    """Distance between two `.x`/`.y` points in meters."""
    return haversine(a.x, a.y, b.x, b.y) * 1000


def average_speed(dist, delta_time):
    """Average speed in m/s."""
    return dist / delta_time


def delta_time(a, b):
    """Seconds between two datetimes (a - b)."""
    return (a - b).total_seconds()


class Stop(object):
    """A contiguous low-speed segment within a trajectory."""

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


DEFAULT_MAX_GAP_SECONDS = 20.0


def cbsmot(trajectorys, max_average_speed, min_time, max_gap_seconds=DEFAULT_MAX_GAP_SECONDS):
    """Detect low-speed stops in a single-vehicle trajectory.

    Parameters
    ----------
    trajectorys : sequence
        Points with `.datetime` and `.point` (where `.point.x` / `.point.y`
        are longitude / latitude). Must be sorted by datetime ascending.
    max_average_speed : float
        Upper bound on segment speed (m/s) to count as "low speed".
    min_time : float
        Minimum accumulated duration (seconds) for a stop to be emitted.
    max_gap_seconds : float
        Upper bound on the gap between consecutive points (seconds).
        A gap at or above this value breaks the current stop so sparse
        data cannot inflate a segment. Tune this to the polling cadence
        of the source (e.g. SPTrans polls ~15s, so 30-45s is reasonable).
    """
    if not trajectorys:
        return []

    stops = []
    previous = trajectorys[0]
    stop = None

    for trajectory in trajectorys[1:]:
        dt = delta_time(trajectory.datetime, previous.datetime)
        dist = distance_absolute(trajectory.point, previous.point)
        if dt > 0:
            average_s = average_speed(dist, dt)
        elif dt == 0 and dist == 0:
            # Duplicate stationary fixes should not break an in-progress stop.
            average_s = 0.0
        else:
            average_s = float("inf")

        if 0 <= dt < max_gap_seconds and average_s < max_average_speed:
            if stop is None:
                stop = Stop()
                stop.add(previous, 0)
            stop.add(trajectory, dist)
        else:
            if stop and stop.delta_time > min_time:
                stops.append(stop)
            stop = None
        previous = trajectory

    if stop and stop.delta_time > min_time:
        stops.append(stop)

    return stops
