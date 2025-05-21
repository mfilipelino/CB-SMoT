# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Sum
from geodjango.core.models import DetectedSegment, Route
from collections import Counter

class Command(BaseCommand):
    help = 'Generates a statistical report on detected low-speed segments.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--top_n_routes',
            type=int,
            default=5,
            help='Number of top routes to list by segment count (default: 5).'
        )

    def handle(self, *args, **options):
        top_n = options['top_n_routes']
        
        segments = DetectedSegment.objects.all()
        total_segments = segments.count()

        if total_segments == 0:
            self.stdout.write(self.style.NOTICE('No detected segments found in the database. Nothing to report.'))
            return

        self.stdout.write(self.style.SUCCESS(f"--- Overall Segment Statistics ---"))
        self.stdout.write(f"Total Detected Segments: {total_segments}")

        avg_duration = segments.aggregate(avg_val=Avg('duration_seconds'))['avg_val']
        self.stdout.write(f"Average Segment Duration: {avg_duration:.2f} seconds")

        avg_speed = segments.aggregate(avg_val=Avg('average_speed_mps'))['avg_val']
        self.stdout.write(f"Average Segment Speed: {avg_speed:.2f} m/s")

        avg_points = segments.aggregate(avg_val=Avg('num_points'))['avg_val']
        self.stdout.write(f"Average Points per Segment: {avg_points:.2f}")

        total_distance = segments.aggregate(sum_val=Sum('distance_meters'))['sum_val']
        self.stdout.write(f"Total Distance Covered by Segments: {total_distance:.2f} meters")
        
        self.stdout.write("") # Newline for spacing

        # Top N Routes by Segment Count
        self.stdout.write(self.style.SUCCESS(f"--- Top {top_n} Routes by Segment Count ---"))
        
        # Group by route_id, count segments, order by count descending.
        # Then fetch route details for the top N.
        routes_data = DetectedSegment.objects.values('route') \
            .annotate(segment_count=Count('id')) \
            .order_by('-segment_count')
        
        if not routes_data:
            self.stdout.write("No segments found with route information.")
        else:
            for i, item in enumerate(routes_data[:top_n]):
                route_id = item['route']
                count = item['segment_count']
                if route_id:
                    try:
                        route_obj = Route.objects.get(id=route_id)
                        # Attempt to create a more descriptive name
                        route_name = f"Route ID {route_obj.id} ({route_obj.main_to_sec} / {route_obj.sec_to_main}, Sign: {route_obj.sign}, Code: {route_obj.code})"
                    except Route.DoesNotExist:
                        route_name = f"Route ID {route_id} (Details not found)"
                else:
                    route_name = "Segments with no associated route"
                self.stdout.write(f"{i+1}. {route_name}: {count} segments")
            
            # Check if there are segments with no route assigned and report them separately if not already covered
            segments_no_route_count = DetectedSegment.objects.filter(route__isnull=True).count()
            if segments_no_route_count > 0 and not any(r['route'] is None for r in routes_data[:top_n]):
                 self.stdout.write(f"Segments with no associated route: {segments_no_route_count} segments")


        self.stdout.write("") # Newline for spacing

        # Distribution of Segments by Hour of the Day
        self.stdout.write(self.style.SUCCESS(f"--- Segment Distribution by Start Hour ---"))
        
        # Fetch only start_time for efficiency
        start_times = segments.values_list('start_time', flat=True)
        hour_counts = Counter(st.hour for st in start_times if st) # Ensure st is not None

        if not hour_counts:
            self.stdout.write("No segment start times available for hourly distribution.")
        else:
            for hour in range(24): # Iterate 0-23 to ensure all hours are listed
                count = hour_counts.get(hour, 0)
                self.stdout.write(f"Hour {hour:02d}: {count} segments")
        
        self.stdout.write("") # Newline for spacing
        self.stdout.write(self.style.SUCCESS("Report generation complete."))
