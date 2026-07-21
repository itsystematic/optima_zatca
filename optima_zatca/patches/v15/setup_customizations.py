"""
Set up ZATCA customizations (custom fields, property setters, roles).

The definitions now live in the single source of truth
(optima_zatca.setup.customizations). This patch re-applies them idempotently so
sites that predate the consolidation converge to the canonical schema.
"""

import frappe

from optima_zatca.setup.customizations import ensure_customizations


def execute():
    frappe.reload_doc("custom", "doctype", "custom_field")
    frappe.reload_doc("custom", "doctype", "property_setter")

    try:
        ensure_customizations()
        frappe.db.commit()
        print("✓ ZATCA customizations setup completed successfully")
    except Exception as e:
        frappe.log_error(f"Error in ZATCA customizations setup: {str(e)}", "ZATCA Migration Patch")
        print(f"✗ Error in ZATCA customizations setup: {str(e)}")
