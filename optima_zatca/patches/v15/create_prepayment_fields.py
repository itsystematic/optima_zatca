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
                "fieldname" : "prepayment_sales_order",
                "fieldtype" : "Link",
                "label" : "Sales Order",
                "options" : "Sales Order",
                "insert_after" : "due_date",
                "read_only" : 1,
                "description" : "Prepayment Sales Invoice is for this Sales Order"
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
                "fieldname": "deducted_prepayment_totals",
                "fieldtype": "Section Break",
                "label": "Deducted Prepayment Totals",
                "insert_after": "total_grands",
                "depends_on": "eval:doc.adjustment_percentage",
            },
            {
                "fieldname": "deducted_tax_amount",
                "fieldtype": "Currency",
                "label": "Deducted Tax Amount",
                "insert_after": "deducted_prepayment_totals",
                "read_only": 1,
                "default": 0
            },
            {
                "fieldname": "column_break_efde",
                "fieldtype": "Column Break",
                "insert_after": "deducted_tax_amount",
            },
            {
                "fieldname": "deducted_taxable_amount",
                "fieldtype": "Currency",
                "label": "Deducted Taxable Amount",
                "insert_after": "column_break_efde",
                "read_only": 1,
                "default": 0
            },
            {
                "fieldname": "column_break_eifde",
                "fieldtype": "Column Break",
                "insert_after": "deducted_taxable_amount",
            },
            {
                "fieldname": "deducted_grand_total",
                "fieldtype": "Currency",
                "label": "Deducted Grand Total",
                "insert_after": "column_break_eifde",
                "read_only": 1,
                "default": 0
            },
            {
                "fieldname": "adjustment_totals",
                "fieldtype": "Section Break",
                "label": "Adjustment Totals",
                "insert_after": "deducted_grand_total",
                "depends_on" : "eval:doc.adjustment_percentage",
            },
            {
                "fieldname" : "adjustment_tax_amount",
                "fieldtype" : "Currency",
                "label" : "Adjustment Tax Amount",
                "insert_after" : "adjustment_totals",
                "read_only" : 1,
                "default" : 0
            },
            {
                "fieldname" : "column_break_eiwqwe",
                "fieldtype" : "Column Break",
                "insert_after" : "adjustment_tax_amount",
            },
            {
                "fieldname" : "adjustment_taxable_amount",
                "fieldtype" : "Currency",
                "label" : "Adjustment Taxable Amount",
                "insert_after" : "column_break_eiwqwe",
                "read_only" : 1,
                "default" : 0
            },
            {
                "fieldname" : "column_break_eiweqwe",
                "fieldtype" : "Column Break",
                "insert_after" : "adjustment_taxable_amount",
            },
            {
                "fieldname" : "adjustment_grands",
                "fieldtype" : "Currency",
                "label" : "Adjustment Grands",
                "insert_after" : "column_break_eiweqwe",
                "read_only" : 1,
                "default" : 0
            },
            {
                "fieldname" : "prepayment_percentages",
                "fieldtype" : "Section Break",
                "label" : "Prepayment Percentages",
                "insert_after" : "adjustment_grands",
                "depends_on" : "eval:['Adjustment', 'Final Adjustment'].includes(doc.sales_invoice_type) && doc.previous_prepayment",
                "read_only_depends_on" : "eval:doc.sales_invoice_type == 'Final Adjustment'",
            },
            {
                "fieldname" : "remaining_percentage",
                "fieldtype" : "Percent",
                "label" : "Remaining Percentage",
                "insert_after" : "prepayment_percentages",
                "precision" : 0,
                "default" : 100,
                "read_only" : 1,
                "precision" : 5,
            },
            {
                "fieldname" : "column_break_eikd",
                "fieldtype" : "Column Break",
                "insert_after" : "remaining_percentage",
            },
            {
                "fieldname" : "max_adjustment_limit",
                "fieldtype" : "Percent",
                "label" : "Max Limit Percentage",
                "insert_after" : "column_break_eikd",
                "read_only" : 1,
                "default" : 0,
                "precision" : 5,
            },
            {
                "fieldname" : "column_break_eikder",
                "fieldtype" : "Column Break",
                "insert_after" : "max_adjustment_limit",
            },
            {
                "fieldname" : "adjustment_percentage",
                "fieldtype" : "Percent",
                "label" : "Adjustment Percentage",
                "insert_after" : "column_break_eikder",
                "precision" : 5,
                "depends_on" : "eval:doc.previous_prepayment",
                "mandatory_depends_on" : "eval:doc.sales_invoice_type == 'Adjustment'",
                "read_only_depends_on" : "eval:doc.sales_invoice_type == 'Final Adjustment'  || doc.is_return",
            },
        ]
    }

    return custom_fields