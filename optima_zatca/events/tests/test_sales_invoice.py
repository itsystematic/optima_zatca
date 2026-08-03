"""In-memory matrix tests for the Sales Invoice lifecycle doc_events.

These exercise the pure ``_decide_*`` guards and the pure Phase-1 TLV encoder in
``optima_zatca.events.sales_invoice`` directly, against ``frappe._dict`` stand-in
docs. Nothing is saved, so there is no DB write and no teardown. The two helpers
that read the DB (``_collect_phase_one_qr_inputs`` / ``_sum_vat_amount``) are
tested with ``frappe.db.get_value`` / ``frappe.get_list`` mocked.

The wiring the matrix layer can't prove (hooks actually fire on submit/cancel,
a QR File gets attached) is the integration layer's job.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from optima_zatca.events import sales_invoice as si


def _doc(**fields):
    return frappe._dict(fields)


# ====================================================================================================
# CANCEL / DELETE GUARDS


class TestCancelDeleteGuards(FrappeTestCase):
    def test_not_sent_is_never_blocked(self):
        doc = _doc(sent_to_zatca=0, clearance_or_reporting=None)
        self.assertFalse(si._decide_cancel_blocked(doc, enable_cancel_invoice=0))
        self.assertFalse(si._decide_delete_blocked(doc, enable_delete_invoice=0))

    def test_sent_and_finalized_blocked_when_override_disabled(self):
        for status in ("CLEARED", "REPORTED"):
            with self.subTest(status=status):
                doc = _doc(sent_to_zatca=1, clearance_or_reporting=status)
                self.assertTrue(si._decide_cancel_blocked(doc, enable_cancel_invoice=0))
                self.assertTrue(si._decide_delete_blocked(doc, enable_delete_invoice=0))

    def test_override_enabled_allows(self):
        doc = _doc(sent_to_zatca=1, clearance_or_reporting="CLEARED")
        self.assertFalse(si._decide_cancel_blocked(doc, enable_cancel_invoice=1))
        self.assertFalse(si._decide_delete_blocked(doc, enable_delete_invoice=1))

    def test_sent_but_not_finalized_is_allowed(self):
        # Sent to ZATCA but not yet cleared/reported (e.g. an error state) is not
        # a finalized invoice, so cancel/delete are not blocked.
        doc = _doc(sent_to_zatca=1, clearance_or_reporting="NOT CLEARED")
        self.assertFalse(si._decide_cancel_blocked(doc, enable_cancel_invoice=0))
        self.assertFalse(si._decide_delete_blocked(doc, enable_delete_invoice=0))


# ====================================================================================================
# SUBMIT PHASE GUARD


class TestSubmitAction(FrappeTestCase):
    def test_phase_one_always_generates(self):
        # Phase One ignores the sent/report state entirely.
        doc = _doc(sent_to_zatca=0, clearance_or_reporting=None)
        self.assertEqual(si._decide_submit_action(doc, si.PHASE_ONE), si.SUBMIT_ACTION_GENERATE)

    def test_phase_two_already_sent_skips(self):
        doc = _doc(sent_to_zatca=1, clearance_or_reporting="CLEARED")
        self.assertEqual(si._decide_submit_action(doc, "Phase Two"), si.SUBMIT_ACTION_SKIP)

    def test_phase_two_not_reported_blocks(self):
        doc = _doc(sent_to_zatca=0, clearance_or_reporting=None)
        self.assertEqual(si._decide_submit_action(doc, "Phase Two"), si.SUBMIT_ACTION_BLOCK)

    def test_phase_two_reported_but_flag_unset_generates(self):
        # Finalized without the sent flag set to exactly 1 -> fall through to QR.
        doc = _doc(sent_to_zatca=0, clearance_or_reporting="REPORTED")
        self.assertEqual(si._decide_submit_action(doc, "Phase Two"), si.SUBMIT_ACTION_GENERATE)


# ====================================================================================================
# TLV QR ENCODING


class TestPostingTimestamp(FrappeTestCase):
    def test_date_and_time_combine_to_utc_iso(self):
        doc = _doc(posting_date="2024-01-01", posting_time="13:30:15")
        self.assertEqual(si._posting_timestamp(doc), "2024-01-01T13:30:15Z")


class TestSumVatAmount(FrappeTestCase):
    def _taxes(self, *rows):
        return [frappe._dict(r) for r in rows]

    def test_sums_only_rows_on_vat_accounts(self):
        doc = _doc(
            company="X",
            name="SINV-1",
            taxes=self._taxes(
                {"account_head": "VAT - X", "rate": 15, "tax_amount": 15.0},
                {"account_head": "Freight - X", "rate": 0, "tax_amount": 99.0},
            ),
        )
        with patch.object(si.frappe, "get_list", return_value=[{"tax_type": "VAT - X"}]):
            self.assertEqual(si._sum_vat_amount(doc), 15.0)

    def test_duplicate_rate_throws(self):
        doc = _doc(
            company="X",
            name="SINV-1",
            taxes=self._taxes(
                {"account_head": "VAT - X", "rate": 15, "tax_amount": 15.0},
                {"account_head": "VAT - X", "rate": 15, "tax_amount": 15.0},
            ),
        )
        with patch.object(si.frappe, "get_list", return_value=[{"tax_type": "VAT - X"}]):
            with self.assertRaises(frappe.ValidationError):
                si._sum_vat_amount(doc)


class TestBuildTlvBase64(FrappeTestCase):
    def test_golden_bytes(self):
        # Pins the exact ZATCA Phase-1 payload for known inputs; any change to the
        # TLV byte layout will flip this string.
        self.assertEqual(
            si._build_phase_one_tlv_base64(
                "Optima", "300000000000003", "2024-01-01T00:00:00Z", "115.0", "15.0"
            ),
            "AQZPcHRpbWECDzMwMDAwMDAwMDAwMDAwMwMUMjAyNC0wMS0wMVQwMDowMDowMFoEBTExNS4wBQQxNS4w",
        )

    def test_seller_name_over_255_bytes_raises(self):
        # Pinned current behavior: a single length byte caps a field at 255 bytes,
        # so an over-long Arabic seller name raises. Documented, not fixed.
        long_name = "ا" * 200  # 400 UTF-8 bytes
        with self.assertRaises(ValueError):
            si._build_phase_one_tlv_base64(long_name, "300000000000003", "2024-01-01T00:00:00Z", "1", "0")


class TestCollectPhaseOneQrInputs(FrappeTestCase):
    def test_missing_arabic_name_throws(self):
        doc = _doc(company="X")
        with patch.object(si.frappe.db, "get_value", return_value=None):
            with self.assertRaises(frappe.ValidationError):
                si._collect_phase_one_qr_inputs(doc)

    def test_missing_tax_id_throws(self):
        doc = _doc(company="X")
        # First company read (arabic name) returns a value, second (tax_id) returns None.
        with patch.object(si.frappe.db, "get_value", side_effect=["شركة", None]):
            with self.assertRaises(frappe.ValidationError):
                si._collect_phase_one_qr_inputs(doc)
