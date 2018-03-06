from django.core.management.base import BaseCommand
import time
from core.service import populate_track


def run():
    while True:
        populate_track()
        time.sleep(15)


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            run()
        except Exception as ex:
            print ex.message
            time.sleep(60)
            run()


