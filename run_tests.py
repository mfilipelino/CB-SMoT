#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test runner that doesn't rely on Django's test runner.
This allows us to test the core functionality without database setup.
"""

import unittest
import sys
import os

# Add the geodjango directory to the path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'geodjango'))

# Import the test modules
from geodjango.core.test_service_functions import TestSaveRoute, TestSaveStopBus, TestSaveVehicles
from geodjango.core.test_utils import (
    TestHaversine, TestDistanceAbsolute, TestAverageSpeed, 
    TestDeltaTime, TestStop
)

if __name__ == '__main__':
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add the test cases
    test_suite.addTest(unittest.makeSuite(TestSaveRoute))
    test_suite.addTest(unittest.makeSuite(TestSaveStopBus))
    test_suite.addTest(unittest.makeSuite(TestSaveVehicles))
    test_suite.addTest(unittest.makeSuite(TestHaversine))
    test_suite.addTest(unittest.makeSuite(TestDistanceAbsolute))
    test_suite.addTest(unittest.makeSuite(TestAverageSpeed))
    test_suite.addTest(unittest.makeSuite(TestDeltaTime))
    test_suite.addTest(unittest.makeSuite(TestStop))
    
    # Run the tests
    runner = unittest.TextTestRunner()
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(not result.wasSuccessful())