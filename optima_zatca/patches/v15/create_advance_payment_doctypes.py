import frappe
from click import secho


def execute():
    '''
    Create Four advance payment doctypes:
    Normal, Advance Payment, Adjust Payment, Elementary Advance Payment
    '''
    secho("Create Advance Payment Doctypes Patch is running", fg="yellow")

    doctypes = [
        "Normal",
        "Advance Payment",
        "Adjust Payment",
        "Elementary Advance Payment"
    ]

    try:
        for doctype in doctypes:
            if not frappe.db.exists("Sales Invoice Type", doctype):
                frappe.get_doc({
                    "doctype": "Sales Invoice Type",
                    "sales_invoice_type": doctype
                }).insert()

        secho("Advance Payment doctypes added successfully", fg="green")

    except Exception as e:
        secho(f"Error adding Advance Payment doctypes: {str(e)}", fg="red")
    