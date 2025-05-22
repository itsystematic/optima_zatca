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
    