from sptrans.v0 import Client
from .models import Route, StopBus, Vehicle, Trajectory
from datetime import datetime

TOKEN = '153bc35d149b8a337da0881349e2d297f149c3421c500c4ebcb038ae3e4b60d5'


def client_authenticate_api_sptrans():
    client = Client()
    client.authenticate(TOKEN)
    return client


def save_route(code, sign, direction, main_to_sec, sec_to_main, type_route):
    try:
        route = Route.objects.get(code=code)
        route.sign = sign
        route.direction = direction
        route.main_to_sec = main_to_sec
        route.sec_to_main = sec_to_main
        route.type_route = type_route
    except Route.DoesNotExist:
        route = Route(
            code=code,
            sign=sign,
            direction=direction,
            main_to_sec=main_to_sec,
            sec_to_main=sec_to_main,
            type_route=type_route
        )
    route.save()
    return route


def populate_routes(search_routes):
    client = client_authenticate_api_sptrans()
    for search_route in search_routes:
        for route in client.search_routes(search_route):
            save_route(
                code=route.code,
                sign=route.sign,
                direction=route.direction,
                main_to_sec=route.main_to_sec,
                sec_to_main=route.sec_to_main,
                type_route=route.type
            )


def save_stop_bus(latitude, longitude, code, name, address, route):
    try:
        stop = StopBus.objects.get(code=code)
        stop.latitude = latitude
        stop.longitude = longitude
        stop.name = name
        stop.route = route
    except StopBus.DoesNotExist:
        stop = StopBus(
            latitude=latitude,
            longitude=longitude,
            code=code,
            name=name,
            address=address,
            route=route
        )
    stop.save()
    return stop


def populate_stops_bus():
    client = client_authenticate_api_sptrans()
    for route in Route.objects.all():
        for stop in client.search_stops_by_route(route.code):
            save_stop_bus(
                latitude=stop.latitude,
                longitude=stop.longitude,
                name=stop.name,
                address=stop.address,
                code=stop.code,
                route=route
            )


def save_vehicles(route, acessible, prefix):
    try:
        vehicle = Vehicle.objects.get(prefix=prefix)
        vehicle.acessible = acessible
    except Vehicle.DoesNotExist:
        vehicle = Vehicle(
            route=route,
            acessible=acessible,
            prefix=prefix,
        )
    vehicle.save()
    return vehicle


def populate_vehicles():
    client = client_authenticate_api_sptrans()
    for route in Route.objects.all():
        positions = client.get_positions(route.code)
        for vehicle in positions.vehicles:
            save_vehicles(
                route=route,
                acessible=vehicle.accessible,
                prefix=vehicle.prefix
            )


def populate_track():
    client = client_authenticate_api_sptrans()
    for route in Route.objects.all():
        positions = client.get_positions(route.code)
        for vehicle_api in positions.vehicles:
            try:
                vehicle = Vehicle.objects.get(prefix=vehicle_api.prefix)
                point = 'POINT({} {})'.format(vehicle_api.longitude, vehicle_api.latitude)
                track = Trajectory(
                    latitude=vehicle_api.latitude,
                    longitude=vehicle_api.longitude,
                    datetime=datetime.now(),
                    point=point,
                    vehicle=vehicle,
                )
                track.save()
                print(vehicle.prefix)
            except Vehicle.DoesNotExist:
                pass

