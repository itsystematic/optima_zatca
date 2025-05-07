import frappe
from click import secho
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    '''Create custom tab for Prepayments in Sales Invoice'''
    secho("Create Prepayments Tab Patch is running", fg="yellow")

    try:
        create_custom_fields(create_prepayments_tab_in_sales_invoice(), update=True)
        secho("Prepayments Tab added successfully", fg="green")
    except Exception as e:
        secho(f"Error adding Prepayments Tab: {str(e)}", fg="red")


def create_prepayments_tab_in_sales_invoice():
    custom_fields = {
        "Sales Invoice": [
            {
                "fieldname" : "prepayments",
                "fieldtype" : "Tab Break",
                "label" : "Prepayments",
                "insert_after" : "Connections",
            },
            {
                "fieldname" : "previous_sales_invoice",
                "fieldtype" : "Link",
                "label" : "Previous Sales Invoice",
                "insert_after" : "prepayments",
            },
            {
                "fieldname" : "prepayments",
                "fieldtype" : "Table",
                "label" : "Prepayments",
                "options" : "Sales Invoice Prepayment",
                "insert_after" : "previous_sales_invoice",
            },
        ]
    }

    return custom_fields