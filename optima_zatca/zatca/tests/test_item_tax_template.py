"""Every line of a Phase Two invoice needs an Item Tax Template, checked at save and again at send."""

from unittest.mock import DEFAULT, Mock, patch

import frappe
from frappe.tests import UnitTestCase

from optima_zatca.zatca.classes import validate
from optima_zatca.zatca.classes.validate import (
    ZatcaInvoiceValidate,
    find_rows_without_tax_template,
    validate_item_tax_templates,
)


def _rows(*templates):
    return [
        {"idx": idx, "item_code": f"ITEM-{idx}", "item_tax_template": template}
        for idx, template in enumerate(templates, start=1)
    ]


class TestFindRowsWithoutTaxTemplate(UnitTestCase):
    def test_reports_every_row_without_one(self):
        # A row cleared on the form keeps "", which must count as missing like None does.
        self.assertEqual(
            find_rows_without_tax_template(_rows("KSA VAT 15% Selling", None, "")),
            [(2, "ITEM-2"), (3, "ITEM-3")],
        )


class TestValidateItemTaxTemplates(UnitTestCase):
    def test_blocks_and_names_only_the_missing_rows(self):
        with self.assertRaises(frappe.ValidationError) as raised:
            validate_item_tax_templates(_rows("KSA VAT 15% Selling", None))
        message = str(raised.exception)
        self.assertIn("ITEM-2", message)
        self.assertNotIn("ITEM-1", message)

    def test_complete_lines_are_not_blocked(self):
        validate_item_tax_templates(_rows("KSA VAT 15% Selling", "KSA VAT 0% Selling"))


class TestSendChecksTaxTemplates(UnitTestCase):
    def test_send_runs_the_check_on_the_invoice_lines(self):
        # Drafts saved before the save-time check existed reach ZATCA only through this one.
        items = _rows(None)
        validator = Mock(sales_invoice={"items": items})
        with patch.multiple(
            validate,
            validate_optima_settings_info=DEFAULT,
            validate_address=DEFAULT,
            validate_item_tax_templates=DEFAULT,
        ) as checks:
            ZatcaInvoiceValidate.validate(validator)
        checks["validate_item_tax_templates"].assert_called_once_with(items)
