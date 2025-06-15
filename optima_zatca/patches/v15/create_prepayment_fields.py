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
                "insert_after" : "connections_tab",
                "depends_on" : "eval:['Prepayment', 'Adjustment', 'Final Adjustment'].includes(doc.sales_invoice_type)",
            },
            {
                "fieldname" : "previous_prepayment",
                "fieldtype" : "Link",
                "label" : "Previous Prepayment",
                "options": "Prepayment Invoice",
                "insert_after" : "prepayments_tab",
                "no_copy" : 1,
                "read_only_depends_on": "eval: doc.return_against",
                "mandatory_depends_on" : "eval:['Prepayment', 'Adjustment', 'Final Adjustment'].includes(doc.sales_invoice_type)",
            },
            {
                "fieldname" : "prepayments_details",
                "fieldtype" : "Section Break",
                "label" : "Prepayment Details",
                "insert_after" : "previous_prepayment",
            },
            {
                "fieldname" : "prepayments_invcoies",
                "fieldtype" : "Table",
                "label" : "Prepayments Invoices",
                "options" : "Prepayment Details",
                "insert_after" : "prepayments_details",
                "depends_on" : "eval:doc.previous_prepayment",
                "read_only" : 1,
            },
            {
                "fieldname" : "prepayment_totals",
                "fieldtype" : "Section Break",
                "label" : "Prepayment Totals",
                "insert_after" : "prepayments_invcoies",
                "depends_on" : "eval:doc.previous_prepayment",
            },
            {
                "fieldname" : "total_tax_amount",
                "fieldtype" : "Currency",
                "label" : "Total Tax Amount",
                "insert_after" : "prepayment_totals",
                "read_only" : 1,
                "default" : 0
            },
            {
                "fieldname" : "column_break_eiwq",
                "fieldtype" : "Column Break",
                "insert_after" : "total_tax_amount",
            },
            {
                "fieldname" : "total_taxable_amount",
                "fieldtype" : "Currency",
                "label" : "Total Taxable Amount",
                "insert_after" : "column_break_eiwq",
                "read_only" : 1,
                "default" : 0
            },
            {
                "fieldname" : "column_break_eiwe",
                "fieldtype" : "Column Break",
                "insert_after" : "total_taxable_amount",
            },
            {
                "fieldname" : "total_grands",
                "fieldtype" : "Currency",
                "label" : "Total Grands",
                "insert_after" : "column_break_eiwe",
                "read_only" : 1,
                "default" : 0
            },
            {
                "fieldname" : "prepayment_percentages",
                "fieldtype" : "Section Break",
                "label" : "Prepayment Percentages",
                "insert_after" : "total_grands",
                "depends_on" : "eval:['Adjustment', 'Final Adjustment'].includes(doc.sales_invoice_type) && doc.previous_prepayment",
                "read_only_depends_on" : "eval:doc.sales_invoice_type == 'Final Adjustment'",
            },
            {
                "fieldname" : "adjustment_percentage",
                "fieldtype" : "Percent",
                "label" : "Adjustment Percentage",
                "insert_after" : "prepayment_percentages",
                "depends_on" : "eval:doc.previous_prepayment",
                "mandatory_depends_on" : "eval:doc.sales_invoice_type == 'Adjustment'",
                "read_only_depends_on" : "eval:doc.sales_invoice_type == 'Final Adjustment'",
                "precision" : 0, 
            },
            # {
            #     "fieldname" : "prepayment_subtotal",
            #     "fieldtype" : "Currency",
            #     "label" : "Prepayment Subtotal",
            #     "insert_after" : "adjustment_percentage",
            #     "read_only" : 1,
            #     "depends_on" : "eval:doc.adjustment_percentage != 0",
            #     "default" : 0
            # },
            {
                "fieldname" : "column_break_eikd",
                "fieldtype" : "Column Break",
                "insert_after" : "adjustment_percentage",
            },
            {
                "fieldname" : "remaining_percentage",
                "fieldtype" : "Percent",
                "label" : "Remaining Percentage",
                "insert_after" : "column_break_eikd",
                "precision" : 0,
                "default" : 100,
                "read_only" : 1,
            },
        ]
    }

    return custom_fields