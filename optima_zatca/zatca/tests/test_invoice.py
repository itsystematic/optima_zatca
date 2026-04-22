from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

import optima_zatca.zatca.invoice as invoice_module
from optima_zatca.zatca.invoice import (
    _create_prepayment_invoice_if_needed,
    _get_response_qrcode,
    _handle_post_success,
    _is_successful_response,
    _log_action,
    _submit_to_zatca_api,
    _submit_invoice_if_auto_submit_enabled,
    _update_invoice_document,
    _validate_before_send,
    format_zatca_response,
    send_to_zatca,
)


class InvoiceTestCase(FrappeTestCase):
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
        result = format_zatca_response({"validationResults": {}})

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
        sales_invoice = MagicMock()
        sales_invoice.run_method.side_effect = Exception("Validation failed")

        with patch.object(invoice_module, "log_and_throw_error") as mock_log:
            result = _validate_before_send(sales_invoice)

        self.assertFalse(result)
        mock_log.assert_called_once()

    def test_validate_before_send_returns_true_on_success(self):
        sales_invoice = MagicMock()

        result = _validate_before_send(sales_invoice)

        self.assertTrue(result)
        sales_invoice.run_method.assert_any_call("validate")
        sales_invoice.run_method.assert_any_call("before_submit")
        sales_invoice.check_permission.assert_called_once_with("submit")


class TestSubmitToZatcaApi(InvoiceTestCase):
    def test_submit_to_zatca_api_calls_make_invoice_request_with_expected_payload(self):
        submission = {
            "clearance_status": "1",
            "authorization": "Bearer token",
            "invoice_hash": "abc123",
            "uuid": "test-uuid",
            "encoded_invoice": "encoded_xml",
            "company_settings": {"authorization": "Bearer token"},
            "endpoint": "https://example.com",
        }

        with patch.object(invoice_module, "make_invoice_request") as mock_request:
            mock_request.return_value = MagicMock(status_code=200)

            result = _submit_to_zatca_api(submission)

        self.assertEqual(result.status_code, 200)
        mock_request.assert_called_once_with(
            "1",
            "Bearer token",
            "abc123",
            "test-uuid",
            "encoded_xml",
            submission["company_settings"],
            "https://example.com",
        )


class TestSuccessfulResponseHelpers(InvoiceTestCase):
    def test_is_successful_response_accepts_200_and_202(self):
        self.assertTrue(_is_successful_response(MagicMock(status_code=200)))
        self.assertTrue(_is_successful_response(MagicMock(status_code=202)))

    def test_is_successful_response_rejects_other_status_codes(self):
        self.assertFalse(_is_successful_response(MagicMock(status_code=400)))

    def test_get_response_qrcode_returns_empty_string_when_response_failed(self):
        result = _get_response_qrcode(MagicMock(status_code=400), "generated_qr", False)

        self.assertEqual(result, "")

    def test_get_response_qrcode_reads_qr_from_cleared_invoice_when_successful(self):
        response = MagicMock(status_code=200)

        with patch.object(
            invoice_module,
            "get_qr_code_from_cleared_invoice",
            return_value="response_qr",
        ) as mock_get_qr:
            result = _get_response_qrcode(response, "generated_qr", True)

        self.assertEqual(result, "response_qr")
        mock_get_qr.assert_called_once_with(response, "generated_qr")


class TestUpdateInvoiceDocument(InvoiceTestCase):
    def test_update_invoice_document_on_success(self):
        sales_invoice = MagicMock()
        sales_invoice.name = "SINV-0001"
        response = MagicMock()
        response.json.return_value = {"clearanceStatus": "CLEARED"}

        with (
            patch.object(
                invoice_module,
                "create_qr_code_for_invoice",
                return_value="/path/to/qr.png",
            ) as mock_qr,
            patch.object(invoice_module.frappe, "msgprint") as mock_msgprint,
        ):
            _update_invoice_document(
                sales_invoice,
                response,
                "qrcode_value",
                True,
            )

        self.assertEqual(sales_invoice.sent_to_zatca, 1)
        self.assertEqual(sales_invoice.clearance_or_reporting, "CLEARED")
        mock_qr.assert_called_once_with("SINV-0001", "qrcode_value")
        sales_invoice.save.assert_called_once_with(
            ignore_permissions=True,
            ignore_version=True,
        )
        mock_msgprint.assert_called_once()

    def test_update_invoice_document_on_failure_does_not_save(self):
        sales_invoice = MagicMock()

        with patch.object(invoice_module.frappe, "msgprint") as mock_msgprint:
            _update_invoice_document(
                sales_invoice,
                MagicMock(),
                "",
                False,
            )

        sales_invoice.save.assert_not_called()
        mock_msgprint.assert_called_once()


class TestLogAction(InvoiceTestCase):
    def setUp(self):
        super().setUp()
        self.response = MagicMock()
        self.response.status_code = 200
        self.response.text = "raw response"

        self.sales_invoice = MagicMock()
        self.sales_invoice.name = "SINV-0001"
        self.sales_invoice.get.return_value = ""

        self.log_context = {
            "uuid": "uuid",
            "api_endpoint": "ep",
            "environment": "sim",
            "pih": "pih",
            "invoice_counter": 1,
            "invoice_hash": "hash",
            "generated_qr_code": "qr",
            "xml_content": b"<xml/>",
        }

    def test_log_action_uses_formatted_response_when_json_is_available(self):
        self.response.json.return_value = {}

        with (
            patch.object(invoice_module, "make_action_log") as mock_log,
            patch.object(invoice_module, "format_zatca_response", return_value="formatted"),
        ):
            _log_action(
                self.sales_invoice,
                self.log_context,
                self.response,
                "encoded",
                "qrcode",
                True,
            )

        self.assertEqual(mock_log.call_args.kwargs["conclusion"], "formatted")
        self.assertEqual(mock_log.call_args.kwargs["status"], "Success")

    def test_log_action_falls_back_to_raw_text_when_json_parsing_fails(self):
        self.response.status_code = 400
        self.response.json.side_effect = ValueError("bad json")

        with (
            patch.object(invoice_module, "make_action_log") as mock_log,
        ):
            _log_action(
                self.sales_invoice,
                self.log_context,
                self.response,
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
                invoice_module,
                "_create_prepayment_invoice_if_needed",
            ) as mock_prepayment,
            patch.object(
                invoice_module,
                "_submit_invoice_if_auto_submit_enabled",
            ) as mock_submit,
        ):
            _handle_post_success(MagicMock(), "uuid", False)

        mock_prepayment.assert_not_called()
        mock_submit.assert_not_called()

    def test_handle_post_success_runs_both_follow_up_policies_on_success(self):
        sales_invoice = MagicMock()

        with (
            patch.object(
                invoice_module,
                "_create_prepayment_invoice_if_needed",
            ) as mock_prepayment,
            patch.object(
                invoice_module,
                "_submit_invoice_if_auto_submit_enabled",
            ) as mock_submit,
        ):
            _handle_post_success(sales_invoice, "uuid", True)

        mock_prepayment.assert_called_once_with(sales_invoice, "uuid")
        mock_submit.assert_called_once_with(sales_invoice)


class TestCreatePrepaymentInvoiceIfNeeded(InvoiceTestCase):
    def test_creates_prepayment_for_non_normal_invoice(self):
        sales_invoice = MagicMock()
        sales_invoice.get.return_value = "Adjustment"

        with patch.object(
            invoice_module.prepayment_invoice,
            "create_prepayment_invoice",
        ) as mock_prepayment:
            _create_prepayment_invoice_if_needed(sales_invoice, "uuid-123")

        mock_prepayment.assert_called_once_with(sales_invoice, "uuid-123")

    def test_skips_prepayment_for_normal_invoice(self):
        sales_invoice = MagicMock()
        sales_invoice.get.return_value = "Normal"

        with patch.object(
            invoice_module.prepayment_invoice,
            "create_prepayment_invoice",
        ) as mock_prepayment:
            _create_prepayment_invoice_if_needed(sales_invoice, "uuid-123")

        mock_prepayment.assert_not_called()


class TestSubmitInvoiceIfAutoSubmitEnabled(InvoiceTestCase):
    def test_auto_submits_when_flag_is_false(self):
        sales_invoice = MagicMock()

        with (
            patch.object(invoice_module.frappe.db, "get_single_value", return_value=0),
            patch.object(invoice_module.frappe.db, "commit") as mock_commit,
        ):
            _submit_invoice_if_auto_submit_enabled(sales_invoice)

        sales_invoice.submit.assert_called_once_with()
        mock_commit.assert_called_once_with()

    def test_skips_submit_when_manual_flag_is_true(self):
        sales_invoice = MagicMock()

        with patch.object(invoice_module.frappe.db, "get_single_value", return_value=1):
            _submit_invoice_if_auto_submit_enabled(sales_invoice)

        sales_invoice.submit.assert_not_called()


class TestSendToZatcaOrchestrator(InvoiceTestCase):
    def test_send_to_zatca_orchestrates_all_helpers(self):
        response = MagicMock()
        response.status_code = 200

        zatca_invoice_data = MagicMock()
        zatca_invoice_data.get_submission_request_data.return_value = {
            "encoded_invoice": "encoded",
        }
        zatca_invoice_data.get_log_context.return_value = {"uuid": "uuid"}
        zatca_invoice_data.get_generated_qr_code.return_value = "generated_qr"
        zatca_invoice_data.get_uuid.return_value = "uuid"
        sales_invoice = MagicMock()

        with (
            patch.object(invoice_module.frappe, "get_doc", return_value=sales_invoice) as mock_get_doc,
            patch.object(invoice_module, "ZatcaInvoiceData", return_value=zatca_invoice_data) as mock_zatca_cls,
            patch.object(invoice_module, "_validate_before_send", return_value=True) as mock_validate,
            patch.object(invoice_module, "_submit_to_zatca_api", return_value=response) as mock_submit,
            patch.object(invoice_module, "_is_successful_response", return_value=True) as mock_success,
            patch.object(invoice_module, "_get_response_qrcode", return_value="qrcode") as mock_qr,
            patch.object(invoice_module, "_update_invoice_document") as mock_update,
            patch.object(invoice_module, "_log_action") as mock_log,
            patch.object(invoice_module, "_handle_post_success") as mock_post,
        ):
            result = send_to_zatca("SINV-0001")

        self.assertTrue(result)
        mock_get_doc.assert_called_once_with("Sales Invoice", "SINV-0001")
        mock_validate.assert_called_once_with(sales_invoice)
        mock_zatca_cls.assert_called_once_with(sales_invoice)
        zatca_invoice_data.get_submission_request_data.assert_called_once_with()
        mock_submit.assert_called_once_with({"encoded_invoice": "encoded"})
        mock_success.assert_called_once_with(response)
        zatca_invoice_data.get_generated_qr_code.assert_called_once_with()
        mock_qr.assert_called_once_with(response, "generated_qr", True)
        mock_update.assert_called_once_with(
            sales_invoice,
            response,
            "qrcode",
            True,
        )
        zatca_invoice_data.get_log_context.assert_called_once_with()
        mock_log.assert_called_once_with(
            sales_invoice,
            {"uuid": "uuid"},
            response,
            "encoded",
            "qrcode",
            True,
        )
        zatca_invoice_data.get_uuid.assert_called_once_with()
        mock_post.assert_called_once_with(sales_invoice, "uuid", True)

    def test_send_to_zatca_returns_false_when_validation_fails(self):
        sales_invoice = MagicMock()

        with (
            patch.object(invoice_module.frappe, "get_doc", return_value=sales_invoice),
            patch.object(invoice_module, "_validate_before_send", return_value=False) as mock_validate,
            patch.object(invoice_module, "ZatcaInvoiceData") as mock_zatca_cls,
        ):
            result = send_to_zatca("SINV-0001")

        self.assertFalse(result)
        mock_validate.assert_called_once_with(sales_invoice)
        mock_zatca_cls.assert_not_called()
