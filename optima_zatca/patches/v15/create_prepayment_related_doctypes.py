import frappe
from click import secho


def execute():
    """
    create Prepayment Sales Invoice Doctypes like:
    Normal
    Initial Prepayment
    Prepayment
    Adjustment
    Final Adjustment
    """
    secho("Create Prepayment Doctypes Patch is running", fg="yellow")

    doctypes = [
        "Normal",
        "Initial Prepayment",
        "Prepayment",
        "Adjustment",
        "Final Adjustment"
    ]

    try:
        for doctype in doctypes:
            if not frappe.db.exists("Sales Invoice Type", doctype):
                frappe.get_doc({
                    "doctype": "Sales Invoice Type",
                    "type": doctype
                }).insert()

        secho("Prepayment doctypes added successfully", fg="green")

    except Exception as e:
        secho(f"Error adding Prepayment doctypes: {str(e)}", fg="red")

    # Create Item group Prepayment Services
    
    try:
        if not frappe.db.exists("Item Group", "Prepayment Services"):
            frappe.get_doc({
                "doctype": "Item Group",
                "parent_item_group": "All Item Groups",
                "item_group_name": "Prepayment Services",
                "name": "Prepayment Services",
                "old_parent": "All Item Groups",
                "parent_item_group": "All Item Groups",
                "is_group": 0
            }).insert()

            secho("Item Group Prepayment Services added successfully", fg="green")
            
            # create Advance Payment Default Item
            if not frappe.db.exists("Item", "advance payment"):
                frappe.get_doc({
                    "doctype": "Item",
                    "item_group": "Prepayment Services",
                    "item_name": "Ad",
                    "item_code": "advance payment",
                    "is_fixed_asset": 0,
                    "is_stock_item": 0,
                }).insert()

                secho("Item Advance Payment added successfully", fg="green")

    except Exception as e:
        secho(f"Error adding Item Group Prepayment Services: {str(e)}", fg="red")
        