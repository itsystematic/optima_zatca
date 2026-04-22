import frappe

from optima_zatca.zatca.submission_workflow import submit_sales_invoice_to_zatca


# Public API

@frappe.whitelist()
def send_to_zatca(sales_invoice_name) -> bool:
    """Public entry point for sending a Sales Invoice to ZATCA."""
    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
    return submit_sales_invoice_to_zatca(sales_invoice)
