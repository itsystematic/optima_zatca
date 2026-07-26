"""In-memory matrix tests for the prepayment/adjustment validation rules.

These exercise the private ``_validate_*`` helpers in
``optima_zatca.events.prepayment`` directly, against an unsaved
``frappe.new_doc("Sales Invoice")``. Nothing is inserted, so there is no DB
write and no teardown.

Why the helpers and not ``validate_prepayments``: the public entry point re-raises
``ValidationError`` untouched but still funnels *unexpected* exceptions through
``log_and_throw_error`` (generic message + Error Log row). Calling the helpers
directly keeps every assertion on the real business-rule message and touches no
DB, except the two lookup helpers, whose ``frappe.db.get_value`` calls are mocked
here.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from optima_zatca.events import prepayment


def _si(**fields):
    """Build an unsaved Sales Invoice carrying just the fields under test."""
    doc = frappe.new_doc("Sales Invoice")
    doc.update(fields)
    return doc


class TestAdjustmentPercentageRange(FrappeTestCase):
    def test_below_minimum_throws(self):
        doc = _si(adjustment_percentage=-0.000000001)
        with self.assertRaises(frappe.ValidationError):
            prepayment._validate_adjustment_percentage_range(doc)

    def test_above_maximum_throws(self):
        doc = _si(adjustment_percentage=100.000000001)
        with self.assertRaises(frappe.ValidationError):
            prepayment._validate_adjustment_percentage_range(doc)

    def test_boundaries_pass(self):
        # 0 and 100 are inclusive-valid; neither should raise.
        prepayment._validate_adjustment_percentage_range(_si(adjustment_percentage=0))
        prepayment._validate_adjustment_percentage_range(_si(adjustment_percentage=100))


class TestRequiredFields(FrappeTestCase):
    def _complete(self):
        return _si(adjustment_percentage=50, total_grands=100, grand_total=50)

    def test_all_present_passes(self):
        prepayment._validate_required_fields(self._complete())

    def test_missing_each_field_throws(self):
        for field in ("adjustment_percentage", "total_grands", "grand_total"):
            with self.subTest(field=field):
                doc = self._complete()
                doc.set(field, 0)  # falsy -> treated as missing
                with self.assertRaises(frappe.ValidationError):
                    prepayment._validate_required_fields(doc)


class TestDeductedTotals(FrappeTestCase):
    def test_deducted_greater_than_grand_throws(self):
        doc = _si(deducted_grand_total=150, grand_total=100)
        with self.assertRaises(frappe.ValidationError):
            prepayment._validate_deducted_totals(doc)

    def test_equal_and_less_pass(self):
        prepayment._validate_deducted_totals(_si(deducted_grand_total=100, grand_total=100))
        prepayment._validate_deducted_totals(_si(deducted_grand_total=40, grand_total=100))

    def test_negative_invoice_compares_absolute_values(self):
        # A credit note carries negative totals; the check is on magnitudes.
        prepayment._validate_deducted_totals(_si(deducted_grand_total=-40, grand_total=-100))
        with self.assertRaises(frappe.ValidationError):
            prepayment._validate_deducted_totals(_si(deducted_grand_total=-150, grand_total=-100))

    def test_base_grand_total_preferred_over_grand_total(self):
        # Multi-currency: base_grand_total wins; deducted <= base passes.
        prepayment._validate_deducted_totals(
            _si(deducted_grand_total=90, base_grand_total=100, grand_total=1)
        )


class TestCalculateMaxAdjustmentLimit(FrappeTestCase):
    def test_repeating_decimal_kept_at_nine_dp(self):
        # 2/3 * 100 = 66.6666...%, the value that historically truncated to a
        # whole number and produced false "exceeds max limit" rejections.
        self.assertEqual(
            prepayment._calculate_max_adjustment_limit(grand_total=2, total_grands=3),
            66.666666667,
        )

    def test_zero_total_grands_returns_zero(self):
        self.assertEqual(
            prepayment._calculate_max_adjustment_limit(grand_total=2, total_grands=0), 0
        )


class TestAdjustmentPercentageLimit(FrappeTestCase):
    def test_zero_total_grands_throws(self):
        doc = _si(total_grands=0, grand_total=2, adjustment_percentage=10)
        with self.assertRaises(frappe.ValidationError):
            prepayment._validate_adjustment_percentage_limit(doc)

    def test_at_repeating_decimal_limit_passes(self):
        # The regression guard: exactly at a 9-dp repeating-decimal limit must pass.
        doc = _si(total_grands=3, grand_total=2, adjustment_percentage=66.666666667)
        prepayment._validate_adjustment_percentage_limit(doc)

    def test_just_above_limit_throws(self):
        doc = _si(total_grands=3, grand_total=2, adjustment_percentage=66.666666668)
        with self.assertRaises(frappe.ValidationError):
            prepayment._validate_adjustment_percentage_limit(doc)


class TestPosPaymentForAdjustment(FrappeTestCase):
    def test_non_pos_short_circuits(self):
        # is_pos != 1 -> the POS ceiling never runs, even with impossible amounts.
        prepayment._validate_pos_payment_for_adjustment(
            _si(is_pos=0, deducted_grand_total=999, paid_amount=999, grand_total=1)
        )

    def test_deducted_plus_paid_over_grand_throws(self):
        doc = _si(is_pos=1, deducted_grand_total=60, paid_amount=60, grand_total=100)
        with self.assertRaises(frappe.ValidationError):
            prepayment._validate_pos_payment_for_adjustment(doc)

    def test_deducted_plus_paid_within_grand_passes(self):
        prepayment._validate_pos_payment_for_adjustment(
            _si(is_pos=1, deducted_grand_total=40, paid_amount=60, grand_total=100)
        )


class TestNonPosPaymentForAdjustment(FrappeTestCase):
    def test_pos_short_circuits(self):
        # is_pos != 0 -> the non-POS ceiling never runs.
        prepayment._validate_non_pos_payment_for_adjustment(
            _si(is_pos=1, deducted_grand_total=999, total_advance=999, grand_total=1)
        )

    def test_deducted_plus_advance_over_grand_throws(self):
        doc = _si(is_pos=0, deducted_grand_total=60, total_advance=60, grand_total=100)
        with self.assertRaises(frappe.ValidationError):
            prepayment._validate_non_pos_payment_for_adjustment(doc)

    def test_deducted_plus_advance_within_grand_passes(self):
        prepayment._validate_non_pos_payment_for_adjustment(
            _si(is_pos=0, deducted_grand_total=40, total_advance=60, grand_total=100)
        )


class TestUniqueInitialPrepayment(FrappeTestCase):
    def test_non_initial_prepayment_type_short_circuits(self):
        doc = _si(sales_invoice_type="Adjustment", prepayment_sales_order="SO-0001")
        with patch.object(prepayment, "_get_existing_initial_prepayment") as lookup:
            prepayment._validate_unique_initial_prepayment(doc)
        lookup.assert_not_called()

    def test_missing_sales_order_short_circuits(self):
        doc = _si(sales_invoice_type=prepayment.INITIAL_PREPAYMENT_TYPE)
        with patch.object(prepayment, "_get_existing_initial_prepayment") as lookup:
            prepayment._validate_unique_initial_prepayment(doc)
        lookup.assert_not_called()

    def test_existing_duplicate_throws(self):
        doc = _si(
            sales_invoice_type=prepayment.INITIAL_PREPAYMENT_TYPE,
            prepayment_sales_order="SO-0001",
        )
        with patch.object(prepayment, "_get_existing_initial_prepayment", return_value="SINV-0009"):
            with self.assertRaises(frappe.ValidationError):
                prepayment._validate_unique_initial_prepayment(doc)

    def test_no_duplicate_passes(self):
        doc = _si(
            sales_invoice_type=prepayment.INITIAL_PREPAYMENT_TYPE,
            prepayment_sales_order="SO-0001",
        )
        with patch.object(prepayment, "_get_existing_initial_prepayment", return_value=None):
            prepayment._validate_unique_initial_prepayment(doc)


class TestPrepaymentLinkage(FrappeTestCase):
    def test_missing_prepayment_throws(self):
        doc = _si(return_against="PRE-404")
        with patch("optima_zatca.events.prepayment.frappe.db.get_value", return_value=None):
            with self.assertRaises(frappe.ValidationError):
                prepayment._validate_prepayment_linkage(doc)

    def test_already_linked_throws(self):
        doc = _si(return_against="PRE-001")
        linked = frappe._dict({"is_linked": 1, "name": "PRE-001"})
        with patch("optima_zatca.events.prepayment.frappe.db.get_value", return_value=linked):
            with self.assertRaises(frappe.ValidationError):
                prepayment._validate_prepayment_linkage(doc)

    def test_unlinked_prepayment_passes(self):
        doc = _si(return_against="PRE-001")
        unlinked = frappe._dict({"is_linked": 0, "name": "PRE-001"})
        with patch("optima_zatca.events.prepayment.frappe.db.get_value", return_value=unlinked):
            prepayment._validate_prepayment_linkage(doc)


class TestReturnRequirements(FrappeTestCase):
    def test_non_return_short_circuits(self):
        # is_return falsy -> linkage is never consulted.
        doc = _si(is_return=0, return_against="")
        with patch.object(prepayment, "_validate_prepayment_linkage") as linkage:
            prepayment._validate_return_requirements(doc)
        linkage.assert_not_called()

    def test_return_without_return_against_throws(self):
        doc = _si(is_return=1, return_against="")
        with self.assertRaises(frappe.ValidationError):
            prepayment._validate_return_requirements(doc)


class TestValidatePrepaymentsDispatch(FrappeTestCase):
    """The public entry point's routing only: assert *which* checks run, not
    their text (message content is the individual helpers' concern above)."""

    def test_normal_invoice_returns_before_any_check(self):
        doc = _si(sales_invoice_type=prepayment.NORMAL_INVOICE_TYPE)
        with (
            patch.object(prepayment, "_validate_unique_initial_prepayment") as unique,
            patch.object(prepayment, "_validate_return_requirements") as returns,
            patch.object(prepayment, "_validate_adjustment_requirements") as adjustment,
        ):
            prepayment.validate_prepayments(doc, "validate")
        unique.assert_not_called()
        returns.assert_not_called()
        adjustment.assert_not_called()

    def test_adjustment_invoice_runs_full_suite(self):
        doc = _si(sales_invoice_type="Adjustment")
        with (
            patch.object(prepayment, "_validate_unique_initial_prepayment") as unique,
            patch.object(prepayment, "_validate_return_requirements") as returns,
            patch.object(prepayment, "_validate_adjustment_requirements") as adjustment,
        ):
            prepayment.validate_prepayments(doc, "validate")
        unique.assert_called_once_with(doc)
        returns.assert_called_once_with(doc)
        adjustment.assert_called_once_with(doc)

    def test_prepayment_invoice_skips_adjustment_suite(self):
        doc = _si(sales_invoice_type="Initial Prepayment")
        with (
            patch.object(prepayment, "_validate_unique_initial_prepayment"),
            patch.object(prepayment, "_validate_return_requirements"),
            patch.object(prepayment, "_validate_adjustment_requirements") as adjustment,
        ):
            prepayment.validate_prepayments(doc, "validate")
        adjustment.assert_not_called()
