"""Stop requiring an Item Tax row on every Item.

Deletes the Property Setter Item / taxes / reqd = 1 that the app created at install and through
`set_item_taxes_reqd`. It applied to every Item on the site, including ones no ZATCA invoice uses.
Saving a Phase Two Sales Invoice of a Saudi company now refuses a line without an Item Tax Template
instead.
"""

import frappe


def execute():
    frappe.db.delete(
        "Property Setter", {"doc_type": "Item", "field_name": "taxes", "property": "reqd", "value": "1"}
    )
    frappe.clear_cache(doctype="Item")
