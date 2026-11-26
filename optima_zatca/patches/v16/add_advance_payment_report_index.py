"""Index Sales Invoice on (company, sales_invoice_type).

The Advance Payment Report reads a company's chain invoices, and without this index it scans every
Sales Invoice to find them. Sites installed from now on get the index from ensure_customizations().
"""

import frappe
from click import secho


def execute():
    if not frappe.db.has_column("Sales Invoice", "sales_invoice_type"):
        secho("Skipped the Sales Invoice (company, sales_invoice_type) index: no sales_invoice_type column", fg="yellow")
        return

    frappe.db.add_index("Sales Invoice", ["company", "sales_invoice_type"])
