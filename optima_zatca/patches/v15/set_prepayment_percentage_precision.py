"""
Raise the precision of the Sales Invoice prepayment percentage fields to 9 dp.

Patches run once, so bumping precision in the field definitions alone would only
affect fresh installs. This migrates already-installed sites. The target value
lives in the single source of truth (setup.customizations.PERCENTAGE_PRECISION).
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from optima_zatca.setup.customizations import PERCENTAGE_PRECISION

PERCENTAGE_FIELDS = ["remaining_percentage", "max_adjustment_limit", "adjustment_percentage"]


def execute():
    fields = {
        "Sales Invoice": [
            {"fieldname": fieldname, "fieldtype": "Percent", "precision": PERCENTAGE_PRECISION}
            for fieldname in PERCENTAGE_FIELDS
        ]
    }
    # update=True: only the precision is changed; other field attributes are preserved.
    create_custom_fields(fields, update=True)
