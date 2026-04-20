# to run this test: pytest -q test_invoice.py --cov=optima_zatca.zatca.invoice --cov-report=term-missing

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch
from optima_zatca.zatca.invoice import (
    format_zatca_response,
)


def _build_invoice_test_dependencies():
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

    prepayment_module = types.ModuleType("optima_zatca.zatca.prepayment_invoice")
    prepayment_module.create_prepayment_invoice = MagicMock()

    utils_module = types.ModuleType("optima_zatca.zatca.utils")
    utils_module.create_qr_code_for_invoice = MagicMock()
    utils_module.log_and_throw_error = MagicMock()

    transport_module = types.ModuleType("optima_zatca.zatca.xml_transport")
    transport_module.encode_invoice_xml_for_api = MagicMock()
    transport_module.get_qr_code_from_cleared_invoice = MagicMock()
    transport_module.serialize_invoice_xml = MagicMock()

    return {
        "frappe": frappe_module,
        "optima_zatca.zatca.logs": logs_module,
        "optima_zatca.zatca.api": api_module,
        "optima_zatca.zatca.classes.invoice": invoice_class_module,
        "optima_zatca.zatca.prepayment_invoice": prepayment_module,
        "optima_zatca.zatca.utils": utils_module,
        "optima_zatca.zatca.xml_transport": transport_module,
    }


def _load_invoice_module():
    sys.modules.pop("optima_zatca.zatca.invoice", None)

    with patch.dict(sys.modules, _build_invoice_test_dependencies()):
        return importlib.import_module("optima_zatca.zatca.invoice")


INVOICE = _load_invoice_module()
send_to_zatca = INVOICE.send_to_zatca
validate_before_send = INVOICE._validate_before_send
submit_to_zatca_api = INVOICE._submit_to_zatca_api
is_successful_response = INVOICE._is_successful_response
get_response_qrcode = INVOICE._get_response_qrcode
update_invoice_document = INVOICE._update_invoice_document
log_action = INVOICE._log_action
handle_post_success = INVOICE._handle_post_success


class InvoiceTestCase(unittest.TestCase):
    pass


class TestFormatZatcaResponse(InvoiceTestCase):
    def test_returns_error_response_with_red_indicator(self):
        response = {
            "validationResults": {
                "errorMessages": [{"message": "First error"}],
                "warningMessages": [],
            }
        }

        result = format_zatca_response(response)

        self.assertTrue(result.startswith("🔴"))
        self.assertIn("First error", result)

    def test_returns_warning_response_with_yellow_indicator(self):
        response = {
            "validationResults": {
                "errorMessages": [],
                "warningMessages": [{"message": "First warning"}],
            }
        }

        result = format_zatca_response(response)

        self.assertTrue(result.startswith("🟡"))
        self.assertIn("First warning", result)

    def test_returns_success_response_when_no_errors_or_warnings(self):
        response = {"validationResults": {}}

        result = format_zatca_response(response)

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

        result = format_zatca_response(response)

        self.assertIn("First error", result)
        self.assertIn("Second error", result)


class TestValidateBeforeSend(InvoiceTestCase):
    def test_validate_before_send_returns_false_on_exception(self):
        mock_invoice = MagicMock()
        mock_invoice.run_method.side_effect = Exception("Validation failed")

        with patch.object(INVOICE, "log_and_throw_error") as mock_log:
            result = validate_before_send(mock_invoice)

        self.assertFalse(result)
        mock_log.assert_called_once()

    def test_validate_before_send_returns_true_on_success(self):
        mock_invoice = MagicMock()
        mock_invoice.run_method.return_value = None
        mock_invoice.check_permission.return_value = None

        result = validate_before_send(mock_invoice)

        self.assertTrue(result)


class TestSubmitToZatcaApi(InvoiceTestCase):
    def test_submit_to_zatca_api_calls_make_invoice_request_with_expected_payload(self):
        mock_invoice = MagicMock()
        mock_invoice.zatca_invoice = {
            "Clearance-Status": "1",
            "UUID": "test-uuid",
            "EndPoint": "https://example.com",
        }
        mock_invoice.company_settings = {"authorization": "Bearer token"}
        mock_invoice.xml.hash = "abc123"

        with patch.object(INVOICE, "make_invoice_request") as mock_request:
            mock_request.return_value = MagicMock(status_code=200)

            result = submit_to_zatca_api(mock_invoice, "encoded_xml")

        self.assertEqual(result.status_code, 200)
        mock_request.assert_called_once_with(
            "1",
            "Bearer token",
            "abc123",
            "test-uuid",
            "encoded_xml",
            mock_invoice.company_settings,
            "https://example.com",
        )


class TestSuccessfulResponseHelpers(InvoiceTestCase):
    def test_is_successful_response_accepts_200_and_202(self):
        self.assertTrue(is_successful_response(MagicMock(status_code=200)))
        self.assertTrue(is_successful_response(MagicMock(status_code=202)))

    def test_is_successful_response_rejects_other_status_codes(self):
        self.assertFalse(is_successful_response(MagicMock(status_code=400)))

    def test_get_response_qrcode_returns_empty_string_when_response_failed(self):
        result = get_response_qrcode(MagicMock(status_code=400), MagicMock(), False)

        self.assertEqual(result, "")

    def test_get_response_qrcode_reads_qr_from_cleared_invoice_when_successful(self):
        invoice = MagicMock()
        invoice.xml.qr_code = "generated_qr"

        with patch.object(
            INVOICE,
            "get_qr_code_from_cleared_invoice",
            return_value="response_qr",
        ) as mock_get_qr:
            result = get_response_qrcode(MagicMock(status_code=200), invoice, True)

        self.assertEqual(result, "response_qr")
        mock_get_qr.assert_called_once_with(unittest.mock.ANY, "generated_qr")


class TestUpdateInvoiceDocument(InvoiceTestCase):
    def test_update_invoice_document_on_success(self):
        mock_invoice_doc = MagicMock()
        mock_invoice_doc.name = "SINV-0001"
        mock_response = MagicMock()
        mock_response.json.return_value = {"clearanceStatus": "CLEARED"}

        with (
            patch.object(INVOICE, "create_qr_code_for_invoice") as mock_qr,
            patch.object(INVOICE, "frappe"),
        ):
            mock_qr.return_value = "/path/to/qr.png"

            update_invoice_document(
                mock_invoice_doc,
                MagicMock(),
                mock_response,
                "qrcode_value",
                True,
            )

        self.assertEqual(mock_invoice_doc.sent_to_zatca, 1)
        self.assertEqual(mock_invoice_doc.clearance_or_reporting, "CLEARED")
        mock_invoice_doc.save.assert_called_once_with(
            ignore_permissions=True,
            ignore_version=True,
        )

    def test_update_invoice_document_on_failure_does_not_save(self):
        mock_invoice_doc = MagicMock()

        with patch.object(INVOICE, "frappe"):
            update_invoice_document(
                mock_invoice_doc,
                MagicMock(),
                MagicMock(),
                "",
                False,
            )

        mock_invoice_doc.save.assert_not_called()


class TestLogAction(InvoiceTestCase):
    def setUp(self):
        super().setUp()
        self.mock_response = MagicMock()
        self.mock_response.status_code = 200
        self.mock_response.text = "raw response"

        self.mock_invoice_doc = MagicMock()
        self.mock_invoice_doc.name = "SINV-0001"
        self.mock_invoice_doc.get.return_value = ""

        self.mock_invoice = MagicMock()
        self.mock_invoice.zatca_invoice = {
            "UUID": "uuid",
            "EndPoint": "ep",
            "Environment": "sim",
            "PIH": "pih",
            "InvoiceCounter": 1,
        }
        self.mock_invoice.xml.hash = "hash"
        self.mock_invoice.xml.qr_code = "qr"

    def test_log_action_uses_formatted_response_when_json_is_available(self):
        self.mock_response.json.return_value = {}

        with (
            patch.object(INVOICE, "make_action_log") as mock_log,
            patch.object(INVOICE, "serialize_invoice_xml", return_value=b"<xml/>"),
            patch.object(INVOICE, "format_zatca_response", return_value="formatted"),
        ):
            log_action(
                self.mock_invoice_doc,
                self.mock_invoice,
                self.mock_response,
                "encoded",
                "qrcode",
                True,
            )

        self.assertEqual(mock_log.call_args.kwargs["conclusion"], "formatted")
        self.assertEqual(mock_log.call_args.kwargs["status"], "Success")

    def test_log_action_falls_back_to_raw_text_when_json_parsing_fails(self):
        self.mock_response.status_code = 400
        self.mock_response.json.side_effect = ValueError("bad json")

        with (
            patch.object(INVOICE, "make_action_log") as mock_log,
            patch.object(INVOICE, "serialize_invoice_xml", return_value=b"<xml/>"),
        ):
            log_action(
                self.mock_invoice_doc,
                self.mock_invoice,
                self.mock_response,
                "encoded",
                "qrcode",
                False,
            )

        self.assertEqual(mock_log.call_args.kwargs["conclusion"], "raw response")
        self.assertEqual(mock_log.call_args.kwargs["status"], "Failed")


class TestHandlePostSuccess(InvoiceTestCase):
    def test_handle_post_success_skips_on_failure(self):
        with (
            patch.object(
                INVOICE.prepayment_invoice,
                "create_prepayment_invoice",
            ) as mock_prepayment,
            patch.object(INVOICE, "frappe"),
        ):
            handle_post_success(MagicMock(), MagicMock(), False)

        mock_prepayment.assert_not_called()

    def test_handle_post_success_creates_prepayment_for_non_normal_invoice(self):
        mock_invoice_doc = MagicMock()
        mock_invoice_doc.get.return_value = "Adjustment"

        mock_invoice = MagicMock()
        mock_invoice.zatca_invoice = {"UUID": "uuid-123"}

        with (
            patch.object(
                INVOICE.prepayment_invoice,
                "create_prepayment_invoice",
            ) as mock_prepayment,
            patch.object(INVOICE, "frappe") as mock_frappe,
        ):
            mock_frappe.db.get_single_value.return_value = 1

            handle_post_success(mock_invoice_doc, mock_invoice, True)

        mock_prepayment.assert_called_once_with(mock_invoice_doc, "uuid-123")
        mock_invoice_doc.submit.assert_not_called()

    def test_handle_post_success_auto_submits_when_flag_is_false(self):
        mock_invoice_doc = MagicMock()
        mock_invoice_doc.get.return_value = "Normal"

        mock_invoice = MagicMock()
        mock_invoice.zatca_invoice = {"UUID": "uuid"}

        with (
            patch.object(
                INVOICE.prepayment_invoice,
                "create_prepayment_invoice",
            ) as mock_prepayment,
            patch.object(INVOICE, "frappe") as mock_frappe,
        ):
            mock_frappe.db.get_single_value.return_value = 0

            handle_post_success(mock_invoice_doc, mock_invoice, True)

        mock_prepayment.assert_not_called()
        mock_invoice_doc.submit.assert_called_once()
        mock_frappe.db.commit.assert_called_once()

    def test_handle_post_success_skips_submit_when_manual_flag_is_true(self):
        mock_invoice_doc = MagicMock()
        mock_invoice_doc.get.return_value = "Normal"

        with (
            patch.object(
                INVOICE.prepayment_invoice,
                "create_prepayment_invoice",
            ) as mock_prepayment,
            patch.object(INVOICE, "frappe") as mock_frappe,
        ):
            mock_frappe.db.get_single_value.return_value = 1

            handle_post_success(mock_invoice_doc, MagicMock(), True)

        mock_prepayment.assert_not_called()
        mock_invoice_doc.submit.assert_not_called()


class TestSendToZatcaOrchestrator(InvoiceTestCase):
    def test_send_to_zatca_orchestrates_all_helpers(self):
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_invoice = MagicMock()
        mock_invoice.xml = MagicMock()

        with (
            patch.object(INVOICE, "frappe") as mock_frappe,
            patch.object(INVOICE, "ZatcaInvoiceData", return_value=mock_invoice) as mock_zatca_cls,
            patch.object(INVOICE, "_validate_before_send", return_value=True) as mock_validate,
            patch.object(INVOICE, "encode_invoice_xml_for_api", return_value="encoded") as mock_encode,
            patch.object(INVOICE, "_submit_to_zatca_api", return_value=mock_response) as mock_submit,
            patch.object(INVOICE, "_is_successful_response", return_value=True) as mock_success,
            patch.object(INVOICE, "_get_response_qrcode", return_value="qrcode") as mock_qr,
            patch.object(INVOICE, "_update_invoice_document") as mock_update,
            patch.object(INVOICE, "_log_action") as mock_log,
            patch.object(INVOICE, "_handle_post_success") as mock_post,
        ):
            sales_invoice = MagicMock()
            mock_frappe.get_doc.return_value = sales_invoice

            result = send_to_zatca("SINV-0001")

        self.assertTrue(result)
        mock_frappe.get_doc.assert_called_once_with("Sales Invoice", "SINV-0001")
        mock_validate.assert_called_once_with(sales_invoice)
        mock_zatca_cls.assert_called_once_with(sales_invoice)
        mock_encode.assert_called_once_with(mock_invoice.xml)
        mock_submit.assert_called_once_with(mock_invoice, "encoded")
        mock_success.assert_called_once_with(mock_response)
        mock_qr.assert_called_once_with(mock_response, mock_invoice, True)
        mock_update.assert_called_once_with(
            sales_invoice,
            mock_invoice,
            mock_response,
            "qrcode",
            True,
        )
        mock_log.assert_called_once_with(
            sales_invoice,
            mock_invoice,
            mock_response,
            "encoded",
            "qrcode",
            True,
        )
        mock_post.assert_called_once_with(sales_invoice, mock_invoice, True)

    def test_send_to_zatca_returns_false_when_validation_fails(self):
        with (
            patch.object(INVOICE, "frappe") as mock_frappe,
            patch.object(INVOICE, "ZatcaInvoiceData") as mock_zatca_cls,
            patch.object(INVOICE, "_validate_before_send", return_value=False) as mock_validate,
            patch.object(INVOICE, "encode_invoice_xml_for_api") as mock_encode,
        ):
            sales_invoice = MagicMock()
            mock_frappe.get_doc.return_value = sales_invoice

            result = send_to_zatca("SINV-0001")

        self.assertFalse(result)
        mock_validate.assert_called_once_with(sales_invoice)
        mock_zatca_cls.assert_not_called()
        mock_encode.assert_not_called()
