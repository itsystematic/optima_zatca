import frappe
import unittest
from unittest.mock import patch, MagicMock
from frappe.tests.utils import FrappeTestCase
import json
import base64
from lxml import etree

from optima_zatca.events.tests import helpers

class TestZatcaIntegration(FrappeTestCase):

    def setUp(self):
        """Set up test dependencies"""
        # Auto-submit commits, which would keep the test's invoice past its rollback.
        commit = patch("frappe.db.commit")
        commit.start()
        self.addCleanup(commit.stop)

        self.company = helpers.get_company()
        self.customer = helpers.get_or_create_customer()
        # Phase Two skips the Phase One QR file, which the rollback could not remove from disk.
        helpers.set_zatca_main_settings(phase="Phase Two", manual_submit=0)

    def create_test_sales_invoice(self, **kwargs):
        """Create a test sales invoice"""
        return helpers.make_sales_invoice(company=self.company, customer=self.customer, **kwargs)

    @patch('optima_zatca.zatca.submission_workflow.make_invoice_request')
    @patch('optima_zatca.zatca.submission_workflow.ZatcaInvoiceData')
    @patch('optima_zatca.zatca.submission_workflow.get_qr_code_from_cleared_invoice')
    @patch('optima_zatca.zatca.submission_workflow.create_qr_code_for_invoice')
    @patch('optima_zatca.zatca.submission_workflow.make_action_log')
    @patch('optima_zatca.zatca.prepayment_invoice.create_prepayment_invoice')
    def test_successful_zatca_integration_with_auto_submit(self, mock_prepayment, mock_action_log, 
                                                            mock_qr_create, mock_qr_get, 
                                                            mock_zatca_data, mock_invoice_request):
        """Test successful ZATCA integration with auto-submit"""
        from optima_zatca.zatca.invoice import send_to_zatca
        
        # Setup mocks
        mock_zatca_instance = MagicMock()
        mock_zatca_instance.get_submission_request_data.return_value = {
            "clearance_status": "CLEARED",
            "authorization": "test-auth",
            "invoice_hash": "test_hash",
            "uuid": "test-uuid",
            "encoded_invoice": "encoded_invoice",
            "company_settings": {"authorization": "test-auth"},
            "endpoint": "test-endpoint",
        }
        mock_zatca_instance.get_generated_qr_code.return_value = "test_qr"
        mock_zatca_instance.get_log_context.return_value = {"uuid": "test-uuid"}
        mock_zatca_instance.get_uuid.return_value = "test-uuid"
        mock_zatca_data.return_value = mock_zatca_instance
        
        # Mock successful ZATCA response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"clearanceStatus": "CLEARED"}
        mock_response.text = "Success"
        mock_invoice_request.return_value = mock_response
        
        mock_qr_get.return_value = "generated_qr"
        mock_qr_create.return_value = "qr_url"
        
        # Create test invoice
        self.valid_invoice = self.create_test_sales_invoice()
        
        # Test the function
        result = send_to_zatca(self.valid_invoice.name)
        
        # Assertions
        self.assertTrue(result)
        
        # Reload invoice to check updates
        self.valid_invoice.reload()
        self.assertEqual(self.valid_invoice.sent_to_zatca, 1)
        self.assertEqual(self.valid_invoice.clearance_or_reporting, "CLEARED")
        self.assertEqual(self.valid_invoice.docstatus, 1)  # Should be submitted

    @patch('optima_zatca.zatca.submission_workflow.make_invoice_request')
    @patch('optima_zatca.zatca.submission_workflow.ZatcaInvoiceData')
    def test_zatca_rejection(self, mock_zatca_data, mock_invoice_request):
        """Test ZATCA rejection scenario"""
        from optima_zatca.zatca.invoice import send_to_zatca
        
        # Setup mocks
        mock_zatca_instance = MagicMock()
        mock_zatca_instance.get_submission_request_data.return_value = {
            "clearance_status": "CLEARED",
            "authorization": "test-auth",
            "invoice_hash": "test_hash",
            "uuid": "test-uuid",
            "encoded_invoice": "encoded_invoice",
            "company_settings": {"authorization": "test-auth"},
            "endpoint": "test-endpoint",
        }
        mock_zatca_instance.get_generated_qr_code.return_value = "test_qr"
        mock_zatca_instance.get_log_context.return_value = {"uuid": "test-uuid"}
        mock_zatca_instance.get_uuid.return_value = "test-uuid"
        mock_zatca_data.return_value = mock_zatca_instance
        
        # Mock ZATCA rejection
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Validation failed"
        mock_invoice_request.return_value = mock_response
        
        # Create test invoice
        invoice = self.create_test_sales_invoice()
        
        # Test the function
        result = send_to_zatca(invoice.name)
        
        # Should return False due to ZATCA rejection
        self.assertFalse(result)
        
        # Invoice should not be submitted
        invoice.reload()
        self.assertEqual(invoice.docstatus, 0)

    def test_missing_required_fields_validation(self):
        """Test validation with missing required fields"""
        from optima_zatca.zatca.invoice import send_to_zatca
        
        # Create invoice with missing customer
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": self.company,
            "currency": "SAR",
            "items": [{
                "item_code": helpers.get_or_create_item(self.company),
                "qty": 1,
                "rate": 100
            }]
            # Missing customer - this should fail validation
        })
        
        with self.assertRaises(Exception):
            invoice.insert()
    
    def tearDown(self):
        """Clean up test data"""
        # Clean up test invoices
        # frappe.db.sql("DELETE FROM `tabSales Invoice` WHERE name in (%s)", (self.valid_invoice.name))
        # frappe.db.commit()

# Additional test scenarios
class TestZatcaValidationScenarios(FrappeTestCase):
    
    def test_duplicate_invoice_submission(self):
        """Test preventing duplicate submissions to ZATCA"""
        # This would test your logic to prevent re-sending already processed invoices
        pass
    
    def test_concurrent_zatca_submission(self):
        """Test handling concurrent ZATCA submissions"""
        # This would test race conditions
        pass
    
    def test_network_timeout_scenarios(self):
        """Test network timeout handling"""
        # This would test timeout scenarios with ZATCA API
        pass
