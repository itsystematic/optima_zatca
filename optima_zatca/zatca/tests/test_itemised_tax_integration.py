"""A Saudi invoice's lines carry their VAT after a real save.

The matrix layer (test_itemised_tax.py) covers the arithmetic. These prove the wiring: that
ERPNext resolves its regional hook to this app, and that the breakup it hands over on save is
one the override can read.
"""

import frappe
from frappe.tests import IntegrationTestCase

from optima_zatca.events.tests import helpers

HOOKED_FUNCTION = "erpnext.controllers.taxes_and_totals.update_itemised_tax_data"
OVERRIDE = "optima_zatca.zatca.itemised_tax.update_itemised_tax_data"


class TestItemisedTaxWiring(IntegrationTestCase):
    def tearDown(self):
        frappe.db.rollback()
        frappe.clear_cache()

    def test_saudi_arabia_resolves_to_this_app(self):
        """ERPNext maps Saudi Arabia to its own UAE override as well, and the last app wins."""
        overrides = frappe.get_hooks("regional_overrides")["Saudi Arabia"][HOOKED_FUNCTION]
        self.assertEqual(overrides[-1], OVERRIDE)

    def test_a_standard_rated_line_carries_its_vat(self):
        company = helpers.get_company()
        self.assertEqual(
            frappe.get_cached_value("Company", company, "country"),
            "Saudi Arabia",
            "the override runs only for Saudi companies",
        )
        template = f"KSA VAT 15% Selling - {frappe.get_cached_value('Company', company, 'abbr')}"
        self.assertTrue(frappe.db.exists("Item Tax Template", template), "after_install creates it for each company")

        item = frappe.get_doc("Item", helpers.get_or_create_item(company))
        item.set("taxes", [{"item_tax_template": template}])
        item.save(ignore_permissions=True)

        account = frappe.db.get_value("Item Tax Template Detail", {"parent": template}, "tax_type")
        si = helpers.make_sales_invoice(
            taxes=[
                {
                    "charge_type": "On Net Total",
                    "account_head": account,
                    "rate": 15,
                    "cost_center": helpers.get_cost_center(company),
                    "description": account,
                }
            ]
        )

        line = si.items[0]
        self.assertEqual((line.tax_rate, line.tax_amount, line.line_extension_amount), (15, 15, 100))
