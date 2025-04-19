# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
from unittest.mock import patch, MagicMock
from core.service import save_route, save_stop_bus, save_vehicles


class TestSaveRoute(unittest.TestCase):
    """Test the save_route function without using the Django ORM"""
    
    @patch('core.service.Route')
    def test_save_route_creates_new_route(self, MockRoute):
        """Test that save_route creates a new Route when it doesn't exist"""
        # Setup mock
        mock_route_instance = MagicMock()
        mock_objects = MagicMock()
        mock_objects.get.side_effect = Exception("DoesNotExist")
        MockRoute.objects = mock_objects
        MockRoute.DoesNotExist = Exception
        MockRoute.return_value = mock_route_instance
        
        # Call the function
        code = 1234
        sign = 5678
        direction = 1
        main_to_sec = "Main to Secondary"
        sec_to_main = "Secondary to Main"
        type_route = "Bus"
        
        result = save_route(code, sign, direction, main_to_sec, sec_to_main, type_route)
        
        # Assertions
        self.assertTrue(MockRoute.called)
        mock_route_instance.save.assert_called_once()
        self.assertEqual(result, mock_route_instance)
    
    @patch('core.service.Route')
    def test_save_route_updates_existing_route(self, MockRoute):
        """Test that save_route updates an existing Route when it exists"""
        # Setup mock
        mock_route_instance = MagicMock()
        MockRoute.objects.get.return_value = mock_route_instance
        
        # Call the function
        code = 1234
        sign = 5678
        direction = 1
        main_to_sec = "Main to Secondary"
        sec_to_main = "Secondary to Main"
        type_route = "Bus"
        
        result = save_route(code, sign, direction, main_to_sec, sec_to_main, type_route)
        
        # Assertions
        MockRoute.objects.get.assert_called_once_with(code=code)
        self.assertEqual(mock_route_instance.sign, sign)
        self.assertEqual(mock_route_instance.direction, direction)
        self.assertEqual(mock_route_instance.main_to_sec, main_to_sec)
        self.assertEqual(mock_route_instance.sec_to_main, sec_to_main)
        self.assertEqual(mock_route_instance.type_route, type_route)
        mock_route_instance.save.assert_called_once()
        self.assertEqual(result, mock_route_instance)


class TestSaveStopBus(unittest.TestCase):
    """Test the save_stop_bus function without using the Django ORM"""
    
    @patch('core.service.StopBus')
    def test_save_stop_bus_creates_new_stop(self, MockStopBus):
        """Test that save_stop_bus creates a new StopBus when it doesn't exist"""
        # Setup mock
        mock_stop_instance = MagicMock()
        mock_objects = MagicMock()
        mock_objects.get.side_effect = Exception("DoesNotExist")
        MockStopBus.objects = mock_objects
        MockStopBus.DoesNotExist = Exception
        MockStopBus.return_value = mock_stop_instance
        
        # Mock route
        mock_route = MagicMock()
        
        # Call the function
        latitude = -23.550520
        longitude = -46.633309
        code = 5678
        name = "Test Stop"
        address = "Test Address"
        
        result = save_stop_bus(latitude, longitude, code, name, address, mock_route)
        
        # Assertions
        self.assertTrue(MockStopBus.called)
        mock_stop_instance.save.assert_called_once()
        self.assertEqual(result, mock_stop_instance)
    
    @patch('core.service.StopBus')
    def test_save_stop_bus_updates_existing_stop(self, MockStopBus):
        """Test that save_stop_bus updates an existing StopBus when it exists"""
        # Setup mock
        mock_stop_instance = MagicMock()
        MockStopBus.objects.get.return_value = mock_stop_instance
        
        # Mock route
        mock_route = MagicMock()
        
        # Call the function
        latitude = -23.550520
        longitude = -46.633309
        code = 5678
        name = "Test Stop"
        address = "Test Address"
        
        result = save_stop_bus(latitude, longitude, code, name, address, mock_route)
        
        # Assertions
        MockStopBus.objects.get.assert_called_once_with(code=code)
        self.assertEqual(mock_stop_instance.latitude, latitude)
        self.assertEqual(mock_stop_instance.longitude, longitude)
        self.assertEqual(mock_stop_instance.name, name)
        self.assertEqual(mock_stop_instance.route, mock_route)
        mock_stop_instance.save.assert_called_once()
        self.assertEqual(result, mock_stop_instance)


class TestSaveVehicles(unittest.TestCase):
    """Test the save_vehicles function without using the Django ORM"""
    
    @patch('core.service.Vehicle')
    def test_save_vehicles_creates_new_vehicle(self, MockVehicle):
        """Test that save_vehicles creates a new Vehicle when it doesn't exist"""
        # Setup mock
        mock_vehicle_instance = MagicMock()
        mock_objects = MagicMock()
        mock_objects.get.side_effect = Exception("DoesNotExist")
        MockVehicle.objects = mock_objects
        MockVehicle.DoesNotExist = Exception
        MockVehicle.return_value = mock_vehicle_instance
        
        # Mock route
        mock_route = MagicMock()
        
        # Call the function
        acessible = True
        prefix = 12345
        
        result = save_vehicles(mock_route, acessible, prefix)
        
        # Assertions
        self.assertTrue(MockVehicle.called)
        mock_vehicle_instance.save.assert_called_once()
        self.assertEqual(result, mock_vehicle_instance)
    
    @patch('core.service.Vehicle')
    def test_save_vehicles_updates_existing_vehicle(self, MockVehicle):
        """Test that save_vehicles updates an existing Vehicle when it exists"""
        # Setup mock
        mock_vehicle_instance = MagicMock()
        MockVehicle.objects.get.return_value = mock_vehicle_instance
        
        # Mock route
        mock_route = MagicMock()
        
        # Call the function
        acessible = True
        prefix = 12345
        
        result = save_vehicles(mock_route, acessible, prefix)
        
        # Assertions
        MockVehicle.objects.get.assert_called_once_with(prefix=prefix)
        self.assertEqual(mock_vehicle_instance.acessible, acessible)
        mock_vehicle_instance.save.assert_called_once()
        self.assertEqual(result, mock_vehicle_instance)


if __name__ == '__main__':
    unittest.main()