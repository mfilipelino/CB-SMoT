# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.contrib.gis.geos import Point
from .models import Route, StopBus, Vehicle, Trajectory
from .service import save_route, save_stop_bus, save_vehicles


class RouteServiceTestCase(TestCase):
    def test_save_route_creates_new_route(self):
        """Test that save_route creates a new Route when it doesn't exist"""
        # Arrange
        code = 1234
        sign = 5678
        direction = 1
        main_to_sec = "Main to Secondary"
        sec_to_main = "Secondary to Main"
        type_route = "Bus"
        
        # Act
        route = save_route(code, sign, direction, main_to_sec, sec_to_main, type_route)
        
        # Assert
        self.assertEqual(route.code, code)
        self.assertEqual(route.sign, sign)
        self.assertEqual(route.direction, direction)
        self.assertEqual(route.main_to_sec, main_to_sec)
        self.assertEqual(route.sec_to_main, sec_to_main)
        self.assertEqual(route.type_route, type_route)
        
        # Verify it was saved to the database
        saved_route = Route.objects.get(code=code)
        self.assertEqual(saved_route.id, route.id)
    
    def test_save_route_updates_existing_route(self):
        """Test that save_route updates an existing Route when it exists"""
        # Arrange
        code = 1234
        sign = 5678
        direction = 1
        main_to_sec = "Main to Secondary"
        sec_to_main = "Secondary to Main"
        type_route = "Bus"
        
        # Create initial route
        initial_route = Route.objects.create(
            code=code,
            sign=sign,
            direction=direction,
            main_to_sec=main_to_sec,
            sec_to_main=sec_to_main,
            type_route=type_route
        )
        
        # New values for update
        new_sign = 9876
        new_direction = 2
        new_main_to_sec = "New Main to Secondary"
        new_sec_to_main = "New Secondary to Main"
        new_type_route = "Minibus"
        
        # Act
        updated_route = save_route(code, new_sign, new_direction, new_main_to_sec, new_sec_to_main, new_type_route)
        
        # Assert
        self.assertEqual(updated_route.id, initial_route.id)  # Same object, just updated
        self.assertEqual(updated_route.code, code)  # Code remains the same
        self.assertEqual(updated_route.sign, new_sign)
        self.assertEqual(updated_route.direction, new_direction)
        self.assertEqual(updated_route.main_to_sec, new_main_to_sec)
        self.assertEqual(updated_route.sec_to_main, new_sec_to_main)
        self.assertEqual(updated_route.type_route, new_type_route)
        
        # Verify it was updated in the database
        saved_route = Route.objects.get(code=code)
        self.assertEqual(saved_route.sign, new_sign)
        self.assertEqual(saved_route.direction, new_direction)


class StopBusServiceTestCase(TestCase):
    def setUp(self):
        # Create a route for testing
        self.route = Route.objects.create(
            code=1234,
            sign=5678,
            direction=1,
            main_to_sec="Main to Secondary",
            sec_to_main="Secondary to Main",
            type_route="Bus"
        )
    
    def test_save_stop_bus_creates_new_stop(self):
        """Test that save_stop_bus creates a new StopBus when it doesn't exist"""
        # Arrange
        latitude = -23.550520
        longitude = -46.633309
        code = 5678
        name = "Test Stop"
        address = "Test Address"
        
        # Act
        stop = save_stop_bus(latitude, longitude, code, name, address, self.route)
        
        # Assert
        self.assertEqual(stop.latitude, latitude)
        self.assertEqual(stop.longitude, longitude)
        self.assertEqual(stop.code, code)
        self.assertEqual(stop.name, name)
        self.assertEqual(stop.address, address)
        self.assertEqual(stop.route, self.route)
        
        # Verify it was saved to the database
        saved_stop = StopBus.objects.get(code=code)
        self.assertEqual(saved_stop.id, stop.id)
    
    def test_save_stop_bus_updates_existing_stop(self):
        """Test that save_stop_bus updates an existing StopBus when it exists"""
        # Arrange
        latitude = -23.550520
        longitude = -46.633309
        code = 5678
        name = "Test Stop"
        address = "Test Address"
        
        # Create initial stop
        initial_stop = StopBus.objects.create(
            latitude=latitude,
            longitude=longitude,
            code=code,
            name=name,
            address=address,
            route=self.route
        )
        
        # New values for update
        new_latitude = -23.551000
        new_longitude = -46.634000
        new_name = "Updated Stop Name"
        
        # Act
        updated_stop = save_stop_bus(new_latitude, new_longitude, code, new_name, address, self.route)
        
        # Assert
        self.assertEqual(updated_stop.id, initial_stop.id)  # Same object, just updated
        self.assertEqual(updated_stop.latitude, new_latitude)
        self.assertEqual(updated_stop.longitude, new_longitude)
        self.assertEqual(updated_stop.code, code)  # Code remains the same
        self.assertEqual(updated_stop.name, new_name)
        self.assertEqual(updated_stop.address, address)
        self.assertEqual(updated_stop.route, self.route)
        
        # Verify it was updated in the database
        saved_stop = StopBus.objects.get(code=code)
        self.assertEqual(saved_stop.latitude, new_latitude)
        self.assertEqual(saved_stop.longitude, new_longitude)
        self.assertEqual(saved_stop.name, new_name)


class VehicleServiceTestCase(TestCase):
    def setUp(self):
        # Create a route for testing
        self.route = Route.objects.create(
            code=1234,
            sign=5678,
            direction=1,
            main_to_sec="Main to Secondary",
            sec_to_main="Secondary to Main",
            type_route="Bus"
        )
    
    def test_save_vehicles_creates_new_vehicle(self):
        """Test that save_vehicles creates a new Vehicle when it doesn't exist"""
        # Arrange
        acessible = True
        prefix = 12345
        
        # Act
        vehicle = save_vehicles(self.route, acessible, prefix)
        
        # Assert
        self.assertEqual(vehicle.route, self.route)
        self.assertEqual(vehicle.acessible, acessible)
        self.assertEqual(vehicle.prefix, prefix)
        
        # Verify it was saved to the database
        saved_vehicle = Vehicle.objects.get(prefix=prefix)
        self.assertEqual(saved_vehicle.id, vehicle.id)
    
    def test_save_vehicles_updates_existing_vehicle(self):
        """Test that save_vehicles updates an existing Vehicle when it exists"""
        # Arrange
        acessible = True
        prefix = 12345
        
        # Create initial vehicle
        initial_vehicle = Vehicle.objects.create(
            route=self.route,
            acessible=acessible,
            prefix=prefix
        )
        
        # New values for update
        new_acessible = False
        
        # Act
        updated_vehicle = save_vehicles(self.route, new_acessible, prefix)
        
        # Assert
        self.assertEqual(updated_vehicle.id, initial_vehicle.id)  # Same object, just updated
        self.assertEqual(updated_vehicle.route, self.route)
        self.assertEqual(updated_vehicle.acessible, new_acessible)
        self.assertEqual(updated_vehicle.prefix, prefix)  # Prefix remains the same
        
        # Verify it was updated in the database
        saved_vehicle = Vehicle.objects.get(prefix=prefix)
        self.assertEqual(saved_vehicle.acessible, new_acessible)
