import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


def _load_invoice_module():
    frappe_module = types.ModuleType("frappe")

    def _whitelist(*args, **kwargs):
        def _decorator(function):
            return function

        return _decorator

    frappe_module.whitelist = _whitelist
    frappe_module._ = lambda message: message
    frappe_module.db = MagicMock()
    frappe_module.get_doc = MagicMock()
    frappe_module.msgprint = MagicMock()

    logs_module = types.ModuleType("optima_zatca.zatca.logs")
    logs_module.make_action_log = MagicMock()

    api_module = types.ModuleType("optima_zatca.zatca.api")
    api_module.make_invoice_request = MagicMock()

    invoice_class_module = types.ModuleType("optima_zatca.zatca.classes.invoice")
    invoice_class_module.ZatcaInvoiceData = MagicMock()

    utils_module = types.ModuleType("optima_zatca.zatca.utils")
    utils_module.create_qr_code_for_invoice = MagicMock()
    utils_module.log_and_throw_error = MagicMock()

    patched_modules = {
        "frappe": frappe_module,
        "optima_zatca.zatca.logs": logs_module,
        "optima_zatca.zatca.api": api_module,
        "optima_zatca.zatca.classes.invoice": invoice_class_module,
        "optima_zatca.zatca.utils": utils_module,
    }

    sys.modules.pop("optima_zatca.zatca.invoice", None)
    with patch.dict(sys.modules, patched_modules):
        return importlib.import_module("optima_zatca.zatca.invoice")


class TestFormatZatcaResponse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def test_returns_error_response_with_red_indicator(self):
        response = {
            "validationResults": {
                "errorMessages": [{"message": "First error"}],
                "warningMessages": [],
            }
        }

        result = self.invoice_module.format_zatca_response(response)

        self.assertTrue(result.startswith("🔴"))
        self.assertIn("First error", result)

    def test_returns_warning_response_with_yellow_indicator(self):
        response = {
            "validationResults": {
                "errorMessages": [],
                "warningMessages": [{"message": "First warning"}],
            }
        }

        result = self.invoice_module.format_zatca_response(response)

        self.assertTrue(result.startswith("🟡"))
        self.assertIn("First warning", result)

    def test_returns_success_response_when_no_errors_or_warnings(self):
        response = {"validationResults": {}}

        result = self.invoice_module.format_zatca_response(response)

        self.assertEqual(result, "🟢 Success Invoice")

    def test_includes_all_error_messages_in_output(self):
        response = {
            "validationResults": {
                "errorMessages": [
                    {"message": "First error"},
                    {"message": "Second error"},
                ]
            }
        }

        result = self.invoice_module.format_zatca_response(response)

        self.assertIn("First error", result)
        self.assertIn("Second error", result)


class TestFormatIssueTime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def test_pads_single_digit_time_components(self):
        self.assertEqual(
            self.invoice_module.format_issue_time("1:5:3"),
            "01:05:03",
        )

    def test_truncates_microseconds(self):
        self.assertEqual(
            self.invoice_module.format_issue_time("10:30:00.123456"),
            "10:30:00",
        )

    def test_returns_empty_string_for_empty_or_none(self):
        self.assertEqual(self.invoice_module.format_issue_time(""), "")
        self.assertEqual(self.invoice_module.format_issue_time(None), "")

    def test_pads_minutes_and_seconds(self):
        self.assertEqual(
            self.invoice_module.format_issue_time("9:0:0"),
            "09:00:00",
        )

