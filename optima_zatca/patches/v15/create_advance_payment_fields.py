import frappe
from click import secho
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    '''
    Create custom fields for Advance Payment
    '''
    secho("Create Advance Payment Fields Patch is running", fg="yellow")

    try:
        custom_fields = create_advance_payment_fields()
        create_custom_fields(custom_fields, update=True)
        secho("Advance Payment custom fields added successfully", fg="green")

    except Exception as e:
        secho(f"Error adding Advance Payment custom fields: {str(e)}", fg="red")


def create_advance_payment_fields():
    custom_fields = {
        "Sales Invoice": [
            {
                "fieldname" : "sales_invoice_type",
                "fieldtype" : "Link",
                "label" : "Sales Invoice Type",
                "insert_after" : "clearance_or_reporting",
                "options" : "Sales Invoice Type",
                "default" : "Normal",
                "reqd" : 1
            },
        ]
    }

    return custom_fields