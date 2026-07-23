"""Integration smoke tests for the prepayment ``validate`` hook.

These save real Sales Invoices on the site and let the ``validate`` doc_event
fire end-to-end, proving the wiring the in-memory matrix layer cannot: that the
hook is registered, the custom fields carry values by validate time, and a
blocked invoice actually fails ``insert()``.

Because ``validate_prepayments`` funnels every failure through
``log_and_throw_error`` (which re-throws a generic message), these assert only
that a ``ValidationError`` is raised on save -- the specific messages are the
matrix layer's job. Nothing is submitted, so the ZATCA ``on_submit`` path is
never touched, and ``tearDown`` rolls the transaction back.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from optima_zatca.overrides.sales_invoice import CustomSalesInvoice
from optima_zatca.events.tests import helpers


class TestPrepaymentValidationWiring(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_sales_invoice_uses_custom_override(self):
        self.assertIsInstance(frappe.new_doc("Sales Invoice"), CustomSalesInvoice)

    def test_normal_invoice_saves(self):
        si = helpers.make_sales_invoice(sales_invoice_type="Normal")
        self.assertTrue(si.name)
        self.assertEqual(si.docstatus, 0)

    def test_valid_adjustment_saves_and_carries_fields(self):
        # total_grands 100, adjustment 50%, deducted 50 -> within every ceiling.
        si = helpers.make_sales_invoice(sales_invoice_type="Adjustment")
        self.assertTrue(si.name)
        self.assertEqual(si.adjustment_percentage, 50)
        self.assertEqual(si.deducted_grand_total, 50)

    def test_over_limit_adjustment_is_blocked(self):
        # In-range percentage (50) but total_grands 1000 vs a ~100 grand total
        # makes the max limit ~10% -> the limit check must reject it on save.
        si = helpers.make_sales_invoice(
            sales_invoice_type="Adjustment",
            do_not_insert=True,
            total_grands=1000,
            adjustment_percentage=50,
            deducted_grand_total=50,
        )
        with self.assertRaises(frappe.ValidationError):
            si.insert(ignore_permissions=True)

    def test_deducted_over_grand_is_blocked(self):
        si = helpers.make_sales_invoice(
            sales_invoice_type="Adjustment",
            do_not_insert=True,
            deducted_grand_total=99999,
        )
        with self.assertRaises(frappe.ValidationError):
            si.insert(ignore_permissions=True)

    def test_duplicate_initial_prepayment_is_blocked(self):
        so = helpers.make_sales_order()
        helpers.make_sales_invoice(
            sales_invoice_type="Initial Prepayment", prepayment_sales_order=so.name
        )
        duplicate = helpers.make_sales_invoice(
            sales_invoice_type="Initial Prepayment",
            prepayment_sales_order=so.name,
            do_not_insert=True,
        )
        with self.assertRaises(frappe.ValidationError):
            duplicate.insert(ignore_permissions=True)
