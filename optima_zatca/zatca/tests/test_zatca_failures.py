import frappe
import unittest
from unittest.mock import patch, MagicMock
from frappe.tests.utils import FrappeTestCase

class TestZatcaFailureScenarios(FrappeTestCase):
    
    def create_invoice_with_validation_errors(self):
        """Create various invoices that will fail different validations"""
        
        # Scenario 1: Invoice with negative amounts
        def test_negative_amount_validation():
            invoice = frappe.get_doc({
                "doctype": "Sales Invoice",
                "customer": "Test Customer",
                "company": "Test Company",
                "items": [{
                    "item_code": "Test Item",
                    "qty": -1,  # Negative qty should fail
                    "rate": 100
                }]
            })
            invoice.insert()
            return invoice
        
        # Scenario 2: Invoice with missing mandatory fields
        def test_missing_fields_validation():
            invoice = frappe.get_doc({
                "doctype": "Sales Invoice",
                "customer": "Test Customer",
                "company": "Test Company",
                # Missing items array - should fail
            })
            invoice.insert()
            return invoice
        
        # Scenario 3: Invoice with invalid customer
        def test_invalid_customer_validation():
            invoice = frappe.get_doc({
                "doctype": "Sales Invoice",
                "customer": "Non Existent Customer",  # Invalid customer
                "company": "Test Company",
                "items": [{
                    "item_code": "Test Item",
                    "qty": 1,
                    "rate": 100
                }]
            })
            invoice.insert()
            return invoice
    
    def test_custom_validation_failure(self):
        """Test custom validation that should prevent ZATCA submission"""
        from optima_zatca.zatca.invoice import send_to_zatca
        
        # Create a custom validation hook that fails
        def failing_validation(doc, method):
            if doc.doctype == "Sales Invoice":
                frappe.throw("Custom validation failed - cannot send to ZATCA")
        
        # Register the hook temporarily
        frappe.get_hooks = lambda: {
            "validate": {
                "Sales Invoice": ["test_zatca_failures.failing_validation"]
            }
        }
        
        invoice = self.create_test_sales_invoice()
        
        # This should fail during validation
        result = send_to_zatca(invoice.name)
        self.assertFalse(result)
    
    def test_before_submit_hook_failure(self):
        """Test before_submit hook failure"""
        from optima_zatca.zatca.invoice import send_to_zatca
        
        invoice = self.create_test_sales_invoice()
        
        # Mock before_submit to fail
        original_before_submit = invoice.run_method
        def failing_before_submit(method_name):
            if method_name == "before_submit":
                raise frappe.ValidationError("Before submit validation failed")
            return original_before_submit(method_name)
        
        invoice.run_method = failing_before_submit
        
        with patch('frappe.get_doc') as mock_get_doc:
            mock_get_doc.return_value = invoice
            result = send_to_zatca(invoice.name)
        
        self.assertFalse(result)