# CB-SMoT Algorithm Documentation

## Algorithm Overview

CB-SMoT (Clustering-Based Stops and Moves of Trajectories) is an algorithm designed to identify stops and moves in a trajectory based on the variation of speed. The algorithm was proposed by Palma et al. (2008) and builds upon the work of Alvares et al. (2007).

### Key Concepts

1. **Trajectory**: A sequence of spatiotemporal points representing the movement of an object over time.
2. **Stop**: A segment of a trajectory where an object stayed for a relevant amount of time with minimal movement.
3. **Move**: A segment of a trajectory between two consecutive stops.

## Algorithm Parameters

The CB-SMoT algorithm has two main parameters:

1. **max_average_speed**: The maximum speed threshold (in meters per second) to consider a point as part of a potential stop. Points with speed below this threshold are candidates for stops.

2. **min_time**: The minimum duration (in seconds) required for a segment to be considered a valid stop. Only segments where the object stayed for at least this duration are classified as stops.

## How the Algorithm Works

1. The algorithm processes the trajectory points sequentially.
2. For each pair of consecutive points, it calculates:
   - The time difference between the points
   - The distance between the points
   - The average speed between the points

3. If the average speed is below the `max_average_speed` threshold and the time difference is less than 20 seconds (to handle potential gaps in data collection), the points are considered part of a potential stop.

4. Consecutive points that meet these criteria are grouped together to form a stop candidate.

5. Once a point with speed above the threshold is encountered, the current stop candidate is evaluated:
   - If the total duration of the stop candidate is greater than `min_time`, it is classified as a valid stop.
   - Otherwise, it is discarded.

6. The process continues until all trajectory points are processed.

## Implementation Details

The implementation in this repository consists of several key components:

1. **Haversine Distance Calculation**: Used to calculate the great-circle distance between two points on the Earth's surface.

2. **Stop Class**: Represents a stop in a trajectory, storing:
   - The list of trajectory points in the stop
   - The start time of the stop
   - The end time of the stop
   - The total duration of the stop
   - The total distance covered during the stop

3. **CB-SMoT Function**: The main algorithm implementation that processes a trajectory and returns a list of detected stops.

## Usage Example

```python
from cbsmot_algorithm import cbsmot
from datetime import datetime
from collections import namedtuple

# Create a simple Point class
class Point:
    def __init__(self, x, y):
        self.x = x  # longitude
        self.y = y  # latitude

# Create a simple Trajectory class
class Trajectory:
    def __init__(self, point, datetime):
        self.point = point
        self.datetime = datetime

# Create a trajectory (sequence of points with timestamps)
trajectory_points = [
    Trajectory(Point(-46.633309, -23.550520), datetime(2020, 1, 1, 12, 0, 0)),
    Trajectory(Point(-46.633310, -23.550521), datetime(2020, 1, 1, 12, 0, 10)),
    Trajectory(Point(-46.633311, -23.550522), datetime(2020, 1, 1, 12, 0, 20)),
    # ... more points
]

# Run the CB-SMoT algorithm
# max_average_speed = 1 m/s, min_time = 60 seconds
stops = cbsmot(trajectory_points, 1, 60)

# Process the detected stops
for i, stop in enumerate(stops):
    print(f"Stop {i+1}:")
    print(f"  Start time: {stop.init_time}")
    print(f"  End time: {stop.last_time}")
    print(f"  Duration: {stop.delta_time} seconds")
    print(f"  Number of points: {len(stop.trajectorys)}")
```

## Academic References

1. Palma, A. T., Bogorny, V., Kuijpers, B., & Alvares, L. O. (2008). "A clustering-based approach for discovering interesting places in trajectories." In Proceedings of the 2008 ACM symposium on Applied computing (pp. 863-868).

2. Alvares, L. O., Bogorny, V., Kuijpers, B., de Macedo, J. A. F., Moelans, B., & Vaisman, A. (2007). "A model for enriching trajectories with semantic geographical information." In Proceedings of the 15th annual ACM international symposium on Advances in geographic information systems (pp. 1-8).