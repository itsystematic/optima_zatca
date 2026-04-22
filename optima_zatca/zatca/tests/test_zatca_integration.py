import frappe
import unittest
from unittest.mock import patch, MagicMock
from frappe.tests.utils import FrappeTestCase
import json
import base64
from lxml import etree

class TestZatcaIntegration(FrappeTestCase):
    
    def setUp(self):
        """Set up test dependencies"""
        self.setup_address()
        self.setup_test_company()
        self.setup_test_customer()
        self.setup_zatca_settings()
        self.setup_commercial_register()
    
    def setup_address(self):
        """Create or get test address"""
        if not frappe.db.exists("Address", "Test Address ZATCA"):
            address = frappe.get_doc({
                "doctype": "Address",
                "address_title": "Test Address ZATCA",
                "address_line1": "123 Test St",
                "city": "Test City",
                "country": "Saudi Arabia",
                "pincode": "12345"
            })
            address.insert()
        self.address = address.name
    
    def setup_test_company(self):
        """Create or get test company"""
        if not frappe.db.exists("Company", "Test Company ZATCA"):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": "Test Company ZATCA",
                "country": "Saudi Arabia",
                "default_currency": "SAR",
                'abbr': 'TCZ',
                'otp': '123456',
                'custom_organization_name': 'Test Org ZATCA',
                'organization_unit': 'Test Unit ZATCA',
                'registered_address': self.address,
            })
            company.insert()
        self.company = "Techno Seal"
    
    def setup_test_customer(self):
        """Create or get test customer"""
        if not frappe.db.exists("Customer", "Test Customer ZATCA"):
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "Test Customer ZATCA",
                "customer_type": "Individual"
            })
            customer.insert()
        self.customer = "Test Customer ZATCA"
    
    def setup_zatca_settings(self):
        """Setup ZATCA settings"""
        if not frappe.db.exists("Zatca Main Settings"):
            settings = frappe.get_doc({
                "doctype": "Zatca Main Settings",
                "manual_submit": 0  # Enable auto-submit for testing
            })
            settings.insert()
    
    def setup_commercial_register(self):
        """Create or get commercial register for the test item"""
        if not frappe.db.exists("Commercial Register", "Test Commercial Register ZATCA"):
            register = frappe.get_doc({
                "doctype": "Commercial Register",
                "commercial_register_name": "Test Commercial Register ZATCA",
                "commercial_register": "Test Commercial Register ZATCA",
                "company": self.company,
                "address": self.address,
            })
            register.insert()
        self.commercial_register = "Test Commercial Register ZATCA"
    
    def create_test_sales_invoice(self, **kwargs):
        """Create a test sales invoice"""
        # Create item if doesn't exist
        if not frappe.db.exists("Item", "Test Item ZATCA"):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": "Test Item ZATCA",
                "item_name": "Test Item ZATCA",
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
            })
            item.insert()
        
        invoice_data = {
            "doctype": "Sales Invoice",
            "customer": self.customer,
            "company": self.company,
            "commercial_register": "1010863352",
            "currency": "SAR",
            "items": [{
                "item_code": "Test Item ZATCA",
                "item_name": "Test Item ZATCA",
                "qty": 1,
                "rate": 100,
                "amount": 100,
                "uom": "Nos",
                "description": "VETOPROOF CM745 GREY عزل مائي اسمنتي (20KG)",
                "income_account": "411 - ايراد المبيعات - TS",
                "item_tax_rate": '{"VAT 15% - TS": 15.0}',
                "cost_center": "رئيسي - TS",
                "item_tax_template": "KSA VAT 15% - TS"
            }],
            "taxes": [{
                "account_head": "VAT 15% - TS",
                "description": "VAT 15%",
                "rate": 0.00,
                "tax_amount": 15.00,
                "total": 115.00,
                "charge_type": "On Net Total",
            }],
        }
        invoice_data.update(kwargs)
        
        invoice = frappe.get_doc(invoice_data)
        invoice.insert()
        return invoice
    
    def create_invalid_sales_invoice(self):
        """Create an invalid sales invoice that will fail validation"""
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": self.customer,
            "company": self.company,
            "currency": "SAR",
            # Missing required items - this will cause validation to fail
            "items": []
        })
        invoice.insert()
        return invoice
    
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
    
    def test_validation_failure_before_zatca(self):
        """Test that validation failures prevent ZATCA submission"""
        from optima_zatca.zatca.invoice import send_to_zatca
        
        # Create invalid invoice
        invoice = self.create_invalid_sales_invoice()
        
        # Test the function
        result = send_to_zatca(invoice.name)
        
        # Should return False due to validation failure
        self.assertFalse(result)
        
        # Invoice should not be marked as sent to ZATCA
        invoice.reload()
        self.assertEqual(invoice.get("sent_to_zatca"), 0)
        self.assertEqual(invoice.docstatus, 0)  # Should remain draft
    
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
    
    @patch('optima_zatca.zatca.submission_workflow.make_invoice_request')
    @patch('optima_zatca.zatca.submission_workflow.ZatcaInvoiceData')
    def test_submit_failure_after_zatca_success(self, mock_zatca_data, mock_invoice_request):
        """Test submit failure after successful ZATCA response"""
        from optima_zatca.zatca.invoice import send_to_zatca
        
        # Setup mocks for successful ZATCA
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
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"clearanceStatus": "CLEARED"}
        mock_response.text = "Success"
        mock_invoice_request.return_value = mock_response
        
        # Create test invoice
        invoice = self.create_test_sales_invoice()
        
        # Mock submit to fail
        def failing_submit():
            raise frappe.ValidationError("Submit validation failed")
        invoice.submit = failing_submit
        
        # Test the function
        with patch('frappe.get_doc') as mock_get_doc:
            mock_get_doc.return_value = invoice
            result = send_to_zatca(invoice.name)
        
        # Should still return True (ZATCA was successful)
        self.assertTrue(result)
        
        # But invoice should not be submitted
        invoice.reload()
        self.assertEqual(invoice.docstatus, 0)
    
    def test_permission_failure_before_zatca(self):
        """Test permission failure before ZATCA"""
        from optima_zatca.zatca.invoice import send_to_zatca
        
        # Create test invoice
        invoice = self.create_test_sales_invoice()
        
        # Mock permission check to fail
        with patch.object(invoice, 'check_permission') as mock_check:
            mock_check.side_effect = frappe.PermissionError("No submit permission")
            
            result = send_to_zatca(invoice.name)
        
        # Should return False due to permission failure
        self.assertFalse(result)
        
        # Invoice should not be processed
        invoice.reload()
        self.assertEqual(invoice.get("sent_to_zatca"), 0)
    
    def test_missing_required_fields_validation(self):
        """Test validation with missing required fields"""
        from optima_zatca.zatca.invoice import send_to_zatca
        
        # Create invoice with missing customer
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": self.company,
            "currency": "SAR",
            "items": [{
                "item_code": "Test Item ZATCA",
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
