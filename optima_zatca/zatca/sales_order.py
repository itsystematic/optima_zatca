import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def make_advance_sales_invoice(source_name, target_doc=None):
    """Create an Advance (Prepayment) Sales Invoice from Sales Order"""
    
    def set_missing_values(source, target):
        target.sales_invoice_type = "Initial Prepayment"
        target.prepayment_sales_order = source.name
        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")
        
        # Clear existing items
        target.items = []
        
        # Add advance payment item
        advance_item = target.append("items", {})
        advance_item.item_code = "advance payment"
        advance_item.qty = 1
        advance_item.conversion_factor = 1.0
        advance_item.rate = 0
        advance_item.price_list_rate = 0
        advance_item.amount = 0
        
        # Get item details for advance payment
        from optima_zatca.zatca.utils import get_item_details
        
        item_details = get_item_details({
            "item_code": "advance payment",
            "doctype": "Sales Invoice",
            "customer": target.customer,
            "company": target.company,
            "currency": target.currency,
            "conversion_rate": target.conversion_rate,
            "price_list": target.selling_price_list,
            "price_list_currency": target.price_list_currency,
            "plc_conversion_rate": target.plc_conversion_rate,
            "sales_invoice_type": "Initial Prepayment"
        })
        
        # Update advance item with fetched details
        if item_details:
            for key, value in item_details.items():
                if hasattr(advance_item, key):
                    setattr(advance_item, key, value)
        
        target.update_stock = 0
        target.run_method("calculate_taxes_and_totals")
    
# for reviwed code only-------------------------------------------------------------
    doclist = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "name": "prepayment_sales_order",
                },
                "validation": {
                    "docstatus": ["=", 1]
                }
            },
            "Sales Taxes and Charges": {
                "doctype": "Sales Taxes and Charges",
                "add_if_empty": True
            },
            "Sales Team": {
                "doctype": "Sales Team",
                "add_if_empty": True
            }
        },
        target_doc,
        set_missing_values,
    )
    
    return doclist
