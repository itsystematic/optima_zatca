"""Integration smoke tests for the prepayment ``validate`` hook.

These save real Sales Invoices on the site and let the ``validate`` doc_event
fire end-to-end, proving the wiring the in-memory matrix layer cannot: that the
hook is registered, the custom fields carry values by validate time, and a
blocked invoice actually fails ``insert()``.

``validate_prepayments`` now re-raises ``ValidationError`` untouched, so the
real business-rule message reaches the caller. These still assert only that a
``ValidationError`` is raised on save -- exhaustive message coverage is the
matrix layer's job. Nothing is submitted, so the ZATCA ``on_submit`` path is
never touched, and ``tearDown`` rolls the transaction back.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from optima_zatca.overrides.sales_invoice import CustomSalesInvoice
from optima_zatca.events import prepayment
from optima_zatca.events.tests import helpers
from optima_zatca.zatca.prepayment_invoice import create_prepayment_invoice


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

    def test_return_accepts_link_made_by_its_own_zatca_send(self):
        # Regression: a draft return is sent to ZATCA before submit, and the
        # successful send creates its own Prepayment Invoice record and marks
        # return_against is_linked. Submit re-runs validate, which used to reject
        # that link as "already linked with another Sales Invoice".
        # A return can't be inserted here without submitting its original, so this
        # replays send-then-submit on a saved draft with the real bookkeeping.
        returned = helpers.make_prepayment_invoice()
        si = helpers.make_sales_invoice(sales_invoice_type="Initial Prepayment")
        si.update({"is_return": 1, "return_against": returned.name, "adjustment_percentage": 0})

        create_prepayment_invoice(si, frappe.generate_hash())

        self.assertTrue(frappe.db.get_value("Prepayment Invoice", returned.name, "is_linked"))
        prepayment._validate_prepayment_linkage(si)

        other = helpers.make_sales_invoice(sales_invoice_type="Initial Prepayment")
        other.return_against = returned.name
        with self.assertRaises(frappe.ValidationError):
            prepayment._validate_prepayment_linkage(other)
