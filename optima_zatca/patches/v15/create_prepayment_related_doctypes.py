import frappe
from frappe import _
from click import secho


def execute():
    """
    Create Prepayment Sales Invoice Types and related setup.
    
    This patch creates:
    - Sales Invoice Types for prepayment workflows
    - Item Group for prepayment services
    - Default advance payment item
    """
    frappe.logger().info("Starting Prepayment Doctypes Patch")
    secho("Creating Prepayment related Doctypes...", fg='yellow')
    
    create_sales_invoice_types()
    create_prepayment_item_group()
    create_advance_payment_item()
    
    frappe.logger().info("Completed Prepayment Doctypes Patch")
    secho("Completed Prepayment related Doctypes.", fg='green')


def create_sales_invoice_types():
    """Create Sales Invoice Type documents for prepayment workflows."""
    invoice_types = [
        "Normal",
        "Initial Prepayment",
        "Prepayment",
        "Adjustment",
        "Final Adjustment"
    ]
    
    try:
        for invoice_type in invoice_types:
            if not frappe.db.exists("Sales Invoice Type", invoice_type):
                doc = frappe.get_doc({
                    "doctype": "Sales Invoice Type",
                    "type": invoice_type
                })
                doc.insert(ignore_permissions=True)
                frappe.logger().info(f"Created Sales Invoice Type: {invoice_type}")
        
        frappe.db.commit()
        frappe.logger().info("All Sales Invoice Types created successfully")
        secho("Sales Invoice Types created successfully!", fg='green')
        
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=_("Error creating Sales Invoice Types")
        )
        secho("Failed to create Sales Invoice Types.", fg='red')


def create_prepayment_item_group():
    """Create Item Group for Prepayment Services."""
    item_group_name = "Prepayment Services"
    
    try:
        if not frappe.db.exists("Item Group", item_group_name):
            doc = frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": item_group_name,
                "is_group": 0,
                "parent_item_group": frappe.db.get_value(
                    "Item Group", 
                    {"is_group": 1}, 
                    "name"
                ) or "All Item Groups"
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            frappe.logger().info(f"Created Item Group: {item_group_name}")
            
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=_("Error creating Item Group")
        )
        secho("Failed to create Item Group.", fg='red')


def create_advance_payment_item():
    """Create default Advance Payment item."""
    item_code = "advance payment"
    
    try:
        if frappe.db.exists("Item", item_code):
            frappe.logger().info(f"Item {item_code} already exists, skipping creation")
            secho(f"Item {item_code} already exists, skipping creation", fg='yellow')
            return
        
        # Temporarily change item naming setting if needed
        original_naming_by = frappe.db.get_single_value("Stock Settings", "item_naming_by")
        naming_changed = False
        
        if original_naming_by == "Naming Series":
            update_stock_settings("Item Code")
            naming_changed = True
        
        try:
            # Create the item
            doc = frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": "Advance Payment",
                "item_group": "Prepayment Services",
                "is_fixed_asset": 0,
                "is_stock_item": 0,
                "stock_uom": frappe.db.get_single_value("Stock Settings", "stock_uom") or "Nos",
                # `set_item_taxes_reqd` makes this table mandatory on Item, so an
                # advance payment created without it is refused — by this app's own
                # rule. A prepayment against a standard-rated supply is itself
                # standard-rated, so the 15% selling template is the right row.
                "taxes": default_tax_rows(),
            })
            # Only when nothing could be filled in: on a site whose VAT templates
            # have not been created yet there is no correct row to add, and an
            # advance payment item with no tax template is still better than none
            # at all. Whoever uses it will be asked for the template on the invoice.
            doc.insert(ignore_permissions=True, ignore_mandatory=not doc.taxes)
            frappe.db.commit()
            frappe.logger().info(f"Created Item: {item_code}")
            
        finally:
            # Restore original naming setting
            if naming_changed:
                update_stock_settings(original_naming_by)
                
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=_("Error creating Advance Payment Item")
        )
        secho("Failed to create Advance Payment Item.", fg='red')


def default_tax_rows():
    """One standard-rated selling template per company, for the advance payment item.

    An Item's tax table is keyed by template, and each template belongs to a
    company, so a site with three companies needs three rows for the item to be
    usable in all of them.
    """
    rows = []
    for company in frappe.get_all("Company", pluck="name"):
        template = frappe.db.get_value(
            "Item Tax Template",
            {"company": company, "disabled": 0, "name": ["like", "KSA VAT 15% Selling%"]},
            "name",
        )
        if template:
            rows.append({"item_tax_template": template})
    return rows


def update_stock_settings(item_naming_by):
    """Update Stock Settings item naming configuration.
    
    Args:
        item_naming_by (str): The naming method to set ('Item Code' or 'Naming Series')
    """
    try:
        stock_settings = frappe.get_doc("Stock Settings")
        stock_settings.item_naming_by = item_naming_by
        stock_settings.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype="Stock Settings")
        frappe.logger().info(f"Updated Stock Settings item_naming_by to: {item_naming_by}")
        secho(f"Updated Stock Settings item_naming_by to: {item_naming_by}", fg='green')
        
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=_("Error updating Stock Settings")
        )
        raise