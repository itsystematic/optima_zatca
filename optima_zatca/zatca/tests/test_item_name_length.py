"""ZATCA's minimum item name length (BR-KSA-F-06-C19), checked before an invoice is signed."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from optima_zatca.zatca.classes.validate import ZatcaInvoiceValidate, find_short_item_names


def _rows(*names):
    return [{"idx": idx, "item_name": name} for idx, name in enumerate(names, start=1)]


def _validator(*names):
    """A validator holding these item names, built without running every check on construction."""
    with patch.object(ZatcaInvoiceValidate, "validate"):
        return ZatcaInvoiceValidate({}, {"items": _rows(*names)}, {}, {}, {})


class TestFindShortItemNames(FrappeTestCase):
    def test_reports_every_row_under_three_characters(self):
        # "Tea" sits on the minimum, and the second short row must not be lost behind the first.
        self.assertEqual(find_short_item_names(_rows("Ad", "Tea", "TV")), [(1, "Ad"), (3, "TV")])

    def test_surrounding_spaces_do_not_count(self):
        self.assertEqual(find_short_item_names(_rows("Ad ", "   ")), [(1, "Ad "), (2, "   ")])


class TestValidateItemNameLengths(FrappeTestCase):
    def test_blocks_and_names_only_the_short_rows(self):
        with self.assertRaises(frappe.ValidationError) as raised:
            _validator("Tea", "TV").validate_item_name_lengths()

        message = str(raised.exception)
        self.assertIn("TV", message)
        self.assertNotIn("Tea", message)

    def test_valid_names_are_not_blocked(self):
        _validator("Tea", "Advance Payment").validate_item_name_lengths()
