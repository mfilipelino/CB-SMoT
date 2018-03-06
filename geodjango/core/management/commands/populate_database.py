from django.core.management.base import BaseCommand
from core.service import populate_routes, populate_stops_bus, populate_vehicles


class Command(BaseCommand):
    def handle(self, *args, **options):
        populate_routes(['Term PEDRO II'])
        populate_stops_bus()
        populate_vehicles()


