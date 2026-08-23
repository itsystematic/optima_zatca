"""
Create the opt-in switch for the PDF/A-3 Letter Head footer band.

**Deliberately not listed in `patches.txt`.** Every other patch in this folder runs
automatically on `bench migrate`; this one must not. Enabling the footer reserves a
strip at the bottom of every page and reflows the invoice body, so a deployment has
to ask for it rather than inherit it from an app update. Where the Custom Field is
absent, `ZatcaPDFA3Generator` reads `None` and produces exactly the PDF it did before.

Run it by hand on the sites that want the footer:

    bench --site <site> execute optima_zatca.patches.v15.create_pdfa3_letterhead_footer_field.execute

Then tick **Show Letter Head Footer in PDF/A-3** on Zatca Main Settings.

Idempotent — safe to re-run. See `docs/pdfa3/reference.md`.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from optima_zatca.zatca.pdfa3 import LETTERHEAD_FOOTER_FIELD


def execute():
    create_custom_fields(
        {
            "Zatca Main Settings": [
                {
                    "fieldname": LETTERHEAD_FOOTER_FIELD,
                    "label": "Show Letter Head Footer in PDF/A-3",
                    "fieldtype": "Check",
                    "insert_after": "letter_head",
                    "default": "0",
                    "description": (
                        "Draws the selected Letter Head's footer at the bottom of every "
                        "PDF/A-3 page."
                    ),
                }
            ]
        },
        update=True,
    )
    frappe.db.commit()
