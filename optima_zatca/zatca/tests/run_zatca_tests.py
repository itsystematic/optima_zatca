#!/usr/bin/env python3

import frappe
import unittest
import sys

def run_zatca_tests():
    """Run all ZATCA-related tests"""
    
    # Initialize Frappe
    frappe.init(site="your_site_name")
    frappe.connect()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    from optima_zatca.zatca.tests.test_zatca_integration import TestZatcaIntegration, TestZatcaValidationScenarios
    from optima_zatca.zatca.tests.test_zatca_failures import TestZatcaFailureScenarios
    
    suite.addTests(loader.loadTestsFromTestCase(TestZatcaIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestZatcaValidationScenarios))
    suite.addTests(loader.loadTestsFromTestCase(TestZatcaFailureScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Cleanup
    frappe.destroy()
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_zatca_tests()
    sys.exit(0 if success else 1)