import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, call, patch


class FakeDoc(dict):
    """Tiny dict-backed doc stub for unit tests."""

    def __getattr__(self, item):
        return self.get(item)


def _load_prepayment_module():
    frappe_module = types.ModuleType("frappe")
    frappe_module.db = MagicMock()
    frappe_module.get_doc = MagicMock()

    utils_module = types.ModuleType("optima_zatca.zatca.utils")
    utils_module.log_and_throw_error = MagicMock()

    patched_modules = {
        "frappe": frappe_module,
        "optima_zatca.zatca.utils": utils_module,
    }

    sys.modules.pop("optima_zatca.zatca.prepayment_invoice", None)
    with patch.dict(sys.modules, patched_modules):
        return importlib.import_module("optima_zatca.zatca.prepayment_invoice")


class TestFormatIssueTime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepayment_module = _load_prepayment_module()

    def test_pads_single_digit_time_components(self):
        self.assertEqual(
            self.prepayment_module.format_issue_time("1:5:3"),
            "01:05:03",
        )

    def test_truncates_microseconds(self):
        self.assertEqual(
            self.prepayment_module.format_issue_time("10:30:00.123456"),
            "10:30:00",
        )

    def test_returns_empty_string_for_empty_or_none(self):
        self.assertEqual(self.prepayment_module.format_issue_time(""), "")
        self.assertEqual(self.prepayment_module.format_issue_time(None), "")


class TestResolveSalesOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepayment_module = _load_prepayment_module()

    def test_prefers_explicit_prepayment_sales_order(self):
        invoice = FakeDoc(
            prepayment_sales_order="SO-DIRECT",
            items=[{"sales_order": "SO-ITEM"}],
        )

        result = self.prepayment_module._resolve_sales_order(invoice)

        self.assertEqual(result, "SO-DIRECT")

    def test_falls_back_to_first_item_sales_order(self):
        invoice = FakeDoc(items=[{"sales_order": "SO-ITEM"}])

        result = self.prepayment_module._resolve_sales_order(invoice)

        self.assertEqual(result, "SO-ITEM")


class TestCompanyCurrencyAmounts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepayment_module = _load_prepayment_module()

    def test_prefers_base_amounts_when_present(self):
        invoice = FakeDoc(
            base_grand_total=230,
            grand_total=115,
            base_total_taxes_and_charges=30,
            total_taxes_and_charges=15,
            base_net_total=200,
            net_total=100,
        )

        result = self.prepayment_module._get_company_currency_amounts(invoice)

        self.assertEqual(result.grand_total, 230)
        self.assertEqual(result.tax_amount, 30)
        self.assertEqual(result.taxable_amount, 200)


class TestCreatePrepaymentInvoice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepayment_module = _load_prepayment_module()

    def setUp(self):
        self.prepayment_module.frappe.db.reset_mock()
        self.prepayment_module.frappe.get_doc.reset_mock()

    def test_creates_prepayment_with_chain_updates_and_company_amounts(self):
        invoice = FakeDoc(
            name="SINV-0001",
            posting_time="1:2:3.123456",
            previous_prepayment="PRE-OLD",
            return_against="PRE-RET",
            sales_invoice_type="Final Adjustment",
            adjustment_percentage=15,
            is_return=True,
            items=[{"tax_rate": 15, "sales_order": "SO-ITEM"}],
            prepayment_sales_order="SO-DIRECT",
            posting_date="2026-04-15",
            customer="Test Customer",
            currency="SAR",
            tax_category="Standard",
            is_debit_note=0,
            remaining_percentage=40,
            base_grand_total=230,
            grand_total=115,
            base_total_taxes_and_charges=30,
            total_taxes_and_charges=15,
            base_net_total=200,
            net_total=100,
        )
        inserted_doc = MagicMock()
        self.prepayment_module.frappe.get_doc.return_value = inserted_doc

        self.prepayment_module.create_prepayment_invoice(invoice, "uuid-123")

        payload = self.prepayment_module.frappe.get_doc.call_args.args[0]

        self.assertEqual(payload["doctype"], "Prepayment Invoice")
        self.assertEqual(payload["uuid"], "uuid-123")
        self.assertEqual(payload["percent"], 15)
        self.assertEqual(payload["issue_time"], "01:02:03")
        self.assertEqual(payload["sales_order"], "SO-DIRECT")
        self.assertEqual(payload["prepayment_type"], "Adjustment")
        self.assertEqual(payload["previous_prepayment_invoice"], "PRE-RET")
        self.assertTrue(payload["has_previous_prepayment"])
        self.assertEqual(payload["adjustment_percentage"], -15)
        self.assertEqual(payload["grand_total"], 230)
        self.assertEqual(payload["tax_amount"], 30)
        self.assertEqual(payload["taxable_amount"], 200)

        self.prepayment_module.frappe.db.set_value.assert_has_calls(
            [
                call("Prepayment Invoice", "PRE-OLD", "is_linked", 1),
                call("Prepayment Invoice", "PRE-RET", "been_return", 1),
                call("Prepayment Invoice", "PRE-RET", "is_linked", 1),
                call("Prepayment Invoice", "PRE-RET", "prepayment_type", "Adjustment"),
            ]
        )
        inserted_doc.insert.assert_called_once_with(ignore_permissions=True)

    def test_logs_errors_when_prepayment_creation_fails(self):
        invoice = FakeDoc(name="SINV-0002")
        self.prepayment_module.frappe.get_doc.side_effect = RuntimeError("boom")

        self.prepayment_module.create_prepayment_invoice(invoice, "uuid-123")

        self.prepayment_module.log_and_throw_error.assert_called_once()
