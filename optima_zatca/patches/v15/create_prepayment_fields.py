import frappe
from click import secho
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    '''
    Create custom fields for Prepayment Cycle in Sales Invoice
    '''
    secho("Create Prepayment Sales Invoice Fields Patch is running", fg="yellow")

    try:
        custom_fields = get_prepayment_fields()
        create_custom_fields(custom_fields, update=True)
        secho("Prepayment Sales Invoice custom fields added successfully", fg="green")

    except Exception as e:
        secho(f"Error adding Prepayment Sales Invoice custom fields: {str(e)}", fg="red")


def get_prepayment_fields():
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
            {
                "fieldname" : "prepayments_tab",
                "fieldtype" : "Tab Break",
                "label" : "Prepayments",
                "insert_after" : "Connections",
            },
            {
                "fieldname" : "previous_prepayment",
                "fieldtype" : "Link",
                "label" : "Previous Prepayment",
                "options": "Prepayment Invoice",
                "insert_after" : "Prepayments",
            },
            {
                "fieldname" : "adjustment_percentage",
                "fieldtype" : "Percent",
                "label" : "Adjustment Percentage",
                "insert_after" : "Previous Prepayment",
                "default" : 0
            },
            {
                "fieldname" : "prepayments_details_table",
                "fieldtype" : "Section Break",
                "label" : "Prepayment Details Table",
                "insert_after" : "Adjustment Percentage",
            },
            {
                "fieldname" : "prepayments_invcoies",
                "fieldtype" : "Table",
                "label" : "Prepayments Invoices",
                "options" : "Prepayment Details",
                "insert_after" : "Prepayment Details Table",
            },
            {
                "fieldname" : "prepayment_totals",
                "fieldtype" : "Section Break",
                "label" : "Prepayment Totals",
                "insert_after" : "Prepayments Invoices",
            },
            {
                "fieldname" : "total_tax_amount",
                "fieldtype" : "Currency",
                "label" : "Total Tax Amount",
                "insert_after" : "Prepayment Totals",
                "read_only" : 1,
                "default" : 0
            },
            {
                "fieldname" : "total_taxable_amount",
                "fieldtype" : "Currency",
                "label" : "Total Taxable Amount",
                "insert_after" : "Total Tax Amount",
                "read_only" : 1,
                "default" : 0
            },
            {
                "fieldname" : "total_grands",
                "fieldtype" : "Currency",
                "label" : "Total Grands",
                "insert_after" : "Total Taxable Amount",
                "read_only" : 1,
                "default" : 0
            },
            {
                "fieldname" : "prepayment_subtotal",
                "fieldtype" : "Currency",
                "label" : "Prepayment Subtotal",
                "insert_after" : "Total Grands",
                "read_only" : 1,
                "default" : 0
            },
        ]
    }

    return custom_fields