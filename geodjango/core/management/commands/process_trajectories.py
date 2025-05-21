# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import LineString
from geodjango.core.models import Trajectory, Vehicle, Route, DetectedSegment

# Attempt to import cbsmot from the root directory
# This assumes that the script is run from the 'geodjango' directory (where manage.py is)
# or that the root directory is in PYTHONPATH.
try:
    from cbsmot_algorithm import cbsmot
except ImportError:
    # If the direct import fails, try adding the project root to sys.path
    # This is a common approach for Django projects where BASE_DIR is the project root.
    # Ensure BASE_DIR is defined in your settings.py, pointing to the repo root.
    # For this specific environment, we might need a more robust way if BASE_DIR is not set
    # or if the structure is different.
    # A simpler alternative if settings.BASE_DIR is not available here:
    # Assuming the script is in geodjango/core/management/commands/
    # and cbsmot_algorithm.py is in the root (two levels up from commands/)
    import os
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
    try:
        from cbsmot_algorithm import cbsmot
    except ImportError as e:
        # If it still fails, we raise an error to indicate the problem.
        raise ImportError(
            "cbsmot_algorithm could not be imported. "
            "Ensure cbsmot_algorithm.py is in the project root "
            "and the project root is in sys.path. Error: {}".format(e)
        )


class Command(BaseCommand):
    help = 'Processes trajectories to detect low-speed segments and saves them.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vehicle_ids',
            nargs='+',
            type=int,
            help='Specific vehicle IDs to process.'
        )
        parser.add_argument(
            '--route_ids',
            nargs='+',
            type=int,
            help='Specific route IDs to process. Will be ignored if vehicle_ids is provided.'
        )
        parser.add_argument(
            '--max_speed',
            type=float,
            default=3.0,
            help='Maximum average speed (m/s) for a segment to be considered low-speed (default: 3.0).'
        )
        parser.add_argument(
            '--min_time',
            type=float,
            default=60.0,
            help='Minimum time duration (seconds) for a segment to be considered (default: 60.0).'
        )
        parser.add_argument(
            '--clear_existing',
            action='store_true',
            help='Clear all existing DetectedSegment records before processing.'
        )

    def handle(self, *args, **options):
        max_speed = options['max_speed']
        min_time = options['min_time']

        if options['clear_existing']:
            count, _ = DetectedSegment.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully cleared {count} existing DetectedSegment records.'))

        vehicles_to_process = None
        if options['vehicle_ids']:
            vehicles_to_process = Vehicle.objects.filter(id__in=options['vehicle_ids'])
            self.stdout.write(f"Processing for specified vehicle IDs: {options['vehicle_ids']}")
        elif options['route_ids']:
            vehicles_to_process = Vehicle.objects.filter(route_id__in=options['route_ids'])
            self.stdout.write(f"Processing for specified route IDs: {options['route_ids']}")
        else:
            vehicles_to_process = Vehicle.objects.all()
            self.stdout.write("Processing for all vehicles.")

        if not vehicles_to_process.exists():
            self.stdout.write(self.style.WARNING('No vehicles found for the given criteria. Exiting.'))
            return

        total_vehicles = vehicles_to_process.count()
        processed_count = 0

        for vehicle in vehicles_to_process:
            self.stdout.write(f"Processing vehicle ID: {vehicle.id} (Prefix: {vehicle.prefix})...")
            
            # Order by datetime to ensure correct sequence for trajectory analysis
            trajectory_points_list = list(Trajectory.objects.filter(vehicle=vehicle).order_by('datetime'))

            if not trajectory_points_list:
                self.stdout.write(self.style.NOTICE(f"No trajectory points found for vehicle ID: {vehicle.id}. Skipping."))
                processed_count += 1
                continue

            # The cbsmot function expects a list of objects, each having 'datetime' and 'point' attributes.
            # Trajectory model instances already fit this if 'point' is the GEOSGeometry object.
            # Ensure that trajectory_points_list contains objects with .point (GEOS Point) and .datetime
            
            # Convert Trajectory Django model objects to simple objects cbsmot expects,
            # if Trajectory model itself is not directly usable or has extra fields causing issues.
            # However, the problem description implies Trajectory objects are directly usable.
            # Let's assume Trajectory objects have .point (GEOS Point) and .datetime attributes.

            detected_stops = cbsmot(
                trajectory_points_list,
                max_average_speed=max_speed,
                min_time=min_time
            )

            num_segments_found = 0
            for stop_obj in detected_stops:
                if not stop_obj.trajectorys: # cbsmot might return stops with no points if min_time is very small
                    continue

                # Construct LineString from trajectory points in the segment
                # Points should be (longitude, latitude)
                # trajectory.point.x is longitude, trajectory.point.y is latitude
                line_points = [(tp.point.x, tp.point.y) for tp in stop_obj.trajectorys if tp.point]
                
                if len(line_points) < 2: # LineString requires at least 2 points
                    self.stdout.write(self.style.WARNING(f"Segment for vehicle {vehicle.id} has < 2 valid points. Skipping segment."))
                    continue
                
                segment_ls = LineString(line_points, srid=4326)

                duration = stop_obj.delta_time
                distance = stop_obj.dist
                avg_speed = distance / duration if duration > 0 else 0

                segment = DetectedSegment.objects.create(
                    vehicle=vehicle,
                    route=vehicle.route,
                    start_time=stop_obj.init_time,
                    end_time=stop_obj.last_time,
                    duration_seconds=duration,
                    distance_meters=distance,
                    num_points=len(stop_obj.trajectorys),
                    average_speed_mps=avg_speed,
                    segment_geometry=segment_ls
                )
                # Add trajectory points to the ManyToManyField
                segment.trajectory_points.set(stop_obj.trajectorys)
                num_segments_found += 1
            
            processed_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed vehicle ID: {vehicle.id}. Found {num_segments_found} segments. "
                    f"({processed_count}/{total_vehicles})"
                )
            )

        self.stdout.write(self.style.SUCCESS('Processing complete.'))
