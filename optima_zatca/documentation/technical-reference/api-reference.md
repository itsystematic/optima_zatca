
# API Reference

## Overview

The ZATCA Integration provides both internal APIs for ERPNext integration and external API interfaces for ZATCA communication.

## Internal APIs (Whitelisted Functions)

### Company Registration

#### register_company
Registers a company with ZATCA.

```python
@frappe.whitelist()
def register_company(**kwargs):
    """
    Register company with ZATCA
    
    Args:
        company (str): Company name in ERPNext
        company_name_in_arabic (str): Arabic company name
        tax_id (str): 15-digit VAT number
        commercial_register (list): List of branch details
        phase (str): Registration phase
        
    Returns:
        dict: Success message
        
    Example:
        frappe.call('optima_zatca.zatca.api.register_company', {
            'company': 'Test Company',
            'company_name_in_arabic': 'شركة تجريبية',
            'tax_id': '123456789012345',
            'commercial_register': [{
                'commercial_register_name': 'Main Branch',
                'commercial_register_number': '1234567890',
                'building_no': '1234',
                'address_line1': 'King Fahd Road',
                'district': 'Al Olaya',
                'city': 'Riyadh',
                'pincode': '12345'
            }]
        })
    """
```