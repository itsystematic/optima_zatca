from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

import optima_zatca.zatca.invoice as invoice_module
import optima_zatca.zatca.submission_workflow as workflow_module
from optima_zatca.zatca.invoice import send_to_zatca
from optima_zatca.zatca.submission_workflow import (
    PostSuccessPolicy,
    SubmissionOutcome,
    _decide_log_conclusion,
    _decide_post_success_policy,
    _decide_response_qrcode,
    _decide_submission_outcome,
    _log_action,
    _execute_post_success_actions,
    _is_manual_submit_enabled,
    _submit_to_zatca_api,
    _update_invoice_document,
    _validate_before_send,
    format_zatca_response,
    submit_sales_invoice_to_zatca,
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

        with patch.object(workflow_module, "log_and_throw_error") as mock_log:
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

        with patch.object(workflow_module, "make_invoice_request") as mock_request:
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


class TestSubmissionOutcomeDecisions(InvoiceTestCase):
    def test_decide_submission_outcome_marks_accepted_response_as_success(self):
        response = MagicMock(status_code=200)
        response.json.return_value = {"clearanceStatus": "CLEARED"}

        with patch.object(
            workflow_module,
            "get_qr_code_from_cleared_invoice",
            return_value="response_qr",
        ) as mock_get_qr:
            result = _decide_submission_outcome(response, "generated_qr")

        self.assertTrue(result.is_success)
        self.assertEqual(result.invoice_status, "CLEARED")
        self.assertEqual(result.response_qrcode, "response_qr")
        self.assertEqual(result.log_status, "Success")
        mock_get_qr.assert_called_once_with(response, "generated_qr")

    def test_decide_submission_outcome_marks_warning_response_as_warning(self):
        response = MagicMock(status_code=202)
        response.json.return_value = {
            "reportingStatus": "REPORTED",
            "validationResults": {
                "warningMessages": [{"message": "warning"}],
            },
        }

        with patch.object(
            workflow_module,
            "get_qr_code_from_cleared_invoice",
            return_value="response_qr",
        ):
            result = _decide_submission_outcome(response, "generated_qr")

        self.assertTrue(result.is_success)
        self.assertEqual(result.invoice_status, "REPORTED")
        self.assertEqual(result.log_status, "Warning")
        self.assertIn("warning", result.log_conclusion)

    def test_decide_submission_outcome_marks_failed_response_as_failed(self):
        response = MagicMock(status_code=400)
        response.text = "raw response"
        response.json.side_effect = ValueError("bad json")

        result = _decide_submission_outcome(response, "generated_qr")

        self.assertFalse(result.is_success)
        self.assertIsNone(result.invoice_status)
        self.assertEqual(result.response_qrcode, "")
        self.assertEqual(result.log_status, "Failed")
        self.assertEqual(result.log_conclusion, "raw response")

    def test_decide_response_qrcode_returns_empty_string_when_response_failed(self):
        result = _decide_response_qrcode(MagicMock(status_code=400), "generated_qr", False)

        self.assertEqual(result, "")

    def test_decide_log_conclusion_falls_back_to_raw_text_when_json_parsing_fails(self):
        response = MagicMock()
        response.text = "raw response"
        response.json.side_effect = ValueError("bad json")

        result = _decide_log_conclusion(response)

        self.assertEqual(result, "raw response")


class TestUpdateInvoiceDocument(InvoiceTestCase):
    def test_update_invoice_document_on_success(self):
        sales_invoice = MagicMock()
        sales_invoice.name = "SINV-0001"
        submission_outcome = SubmissionOutcome(
            is_success=True,
            invoice_status="CLEARED",
            response_qrcode="qrcode_value",
            log_status="Success",
            log_conclusion="Accepted",
        )

        with (
            patch.object(
                workflow_module,
                "create_qr_code_for_invoice",
                return_value="/path/to/qr.png",
            ) as mock_qr,
            patch.object(workflow_module.frappe, "msgprint") as mock_msgprint,
        ):
            _update_invoice_document(sales_invoice, submission_outcome)

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
        submission_outcome = SubmissionOutcome(
            is_success=False,
            invoice_status=None,
            response_qrcode="",
            log_status="Failed",
            log_conclusion="Rejected",
        )

        with patch.object(workflow_module.frappe, "msgprint") as mock_msgprint:
            _update_invoice_document(sales_invoice, submission_outcome)

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
        submission_outcome = SubmissionOutcome(
            is_success=True,
            invoice_status="CLEARED",
            response_qrcode="qrcode",
            log_status="Success",
            log_conclusion="formatted",
        )

        with patch.object(workflow_module, "make_action_log") as mock_log:
            _log_action(
                self.sales_invoice,
                self.log_context,
                self.response,
                "encoded",
                submission_outcome,
            )

        self.assertEqual(mock_log.call_args.kwargs["conclusion"], "formatted")
        self.assertEqual(mock_log.call_args.kwargs["status"], "Success")

    def test_log_action_uses_outcome_data_instead_of_recomputing_policy(self):
        self.response.status_code = 400
        submission_outcome = SubmissionOutcome(
            is_success=False,
            invoice_status=None,
            response_qrcode="qrcode",
            log_status="Failed",
            log_conclusion="raw response",
        )

        with patch.object(workflow_module, "make_action_log") as mock_log:
            _log_action(
                self.sales_invoice,
                self.log_context,
                self.response,
                "encoded",
                submission_outcome,
            )

        self.assertEqual(mock_log.call_args.kwargs["conclusion"], "raw response")
        self.assertEqual(mock_log.call_args.kwargs["status"], "Failed")


class TestPostSuccessPolicy(InvoiceTestCase):
    def test_decide_post_success_policy_disables_actions_on_failure(self):
        result = _decide_post_success_policy(False, "Adjustment", False)

        self.assertEqual(
            result,
            PostSuccessPolicy(
                create_prepayment_invoice=False,
                auto_submit_invoice=False,
            ),
        )

    def test_decide_post_success_policy_creates_prepayment_for_non_normal_invoice(self):
        result = _decide_post_success_policy(True, "Adjustment", False)

        self.assertEqual(
            result,
            PostSuccessPolicy(
                create_prepayment_invoice=True,
                auto_submit_invoice=True,
            ),
        )

    def test_decide_post_success_policy_skips_auto_submit_when_manual_submit_enabled(self):
        result = _decide_post_success_policy(True, "Normal", True)

        self.assertEqual(
            result,
            PostSuccessPolicy(
                create_prepayment_invoice=False,
                auto_submit_invoice=False,
            ),
        )

    def test_is_manual_submit_enabled_reads_setting_from_frappe(self):
        with patch.object(workflow_module.frappe.db, "get_single_value", return_value=1):
            result = _is_manual_submit_enabled()

        self.assertTrue(result)


class TestExecutePostSuccessActions(InvoiceTestCase):
    def test_execute_post_success_actions_runs_requested_side_effects(self):
        sales_invoice = MagicMock()
        follow_up_policy = PostSuccessPolicy(
            create_prepayment_invoice=True,
            auto_submit_invoice=True,
        )

        with (
            patch.object(
                workflow_module.prepayment_invoice,
                "create_prepayment_invoice",
            ) as mock_prepayment,
            patch.object(workflow_module.frappe.db, "commit") as mock_commit,
        ):
            _execute_post_success_actions(sales_invoice, "uuid-123", follow_up_policy)

        mock_prepayment.assert_called_once_with(sales_invoice, "uuid-123")
        sales_invoice.submit.assert_called_once_with()
        mock_commit.assert_called_once_with()

    def test_execute_post_success_actions_skips_unselected_side_effects(self):
        sales_invoice = MagicMock()
        follow_up_policy = PostSuccessPolicy(
            create_prepayment_invoice=False,
            auto_submit_invoice=False,
        )

        with (
            patch.object(
                workflow_module.prepayment_invoice,
                "create_prepayment_invoice",
            ) as mock_prepayment,
            patch.object(workflow_module.frappe.db, "commit") as mock_commit,
        ):
            _execute_post_success_actions(sales_invoice, "uuid-123", follow_up_policy)

        mock_prepayment.assert_not_called()
        sales_invoice.submit.assert_not_called()
        mock_commit.assert_not_called()


class TestSubmissionWorkflow(InvoiceTestCase):
    def test_submit_sales_invoice_to_zatca_orchestrates_all_helpers(self):
        response = MagicMock()
        response.status_code = 200
        submission_outcome = SubmissionOutcome(
            is_success=True,
            invoice_status="CLEARED",
            response_qrcode="qrcode",
            log_status="Success",
            log_conclusion="Accepted",
        )
        follow_up_policy = PostSuccessPolicy(
            create_prepayment_invoice=True,
            auto_submit_invoice=False,
        )

        zatca_invoice_data = MagicMock()
        zatca_invoice_data.get_submission_request_data.return_value = {
            "encoded_invoice": "encoded",
        }
        zatca_invoice_data.get_log_context.return_value = {"uuid": "uuid"}
        zatca_invoice_data.get_generated_qr_code.return_value = "generated_qr"
        zatca_invoice_data.get_uuid.return_value = "uuid"
        sales_invoice = MagicMock()

        with (
            patch.object(workflow_module, "ZatcaInvoiceData", return_value=zatca_invoice_data) as mock_zatca_cls,
            patch.object(workflow_module, "_validate_before_send", return_value=True) as mock_validate,
            patch.object(workflow_module, "_submit_to_zatca_api", return_value=response) as mock_submit,
            patch.object(workflow_module, "_decide_submission_outcome", return_value=submission_outcome) as mock_outcome,
            patch.object(workflow_module, "_update_invoice_document") as mock_update,
            patch.object(workflow_module, "_log_action") as mock_log,
            patch.object(workflow_module, "_is_manual_submit_enabled", return_value=True) as mock_manual_submit,
            patch.object(workflow_module, "_decide_post_success_policy", return_value=follow_up_policy) as mock_policy,
            patch.object(workflow_module, "_execute_post_success_actions") as mock_post,
        ):
            result = submit_sales_invoice_to_zatca(sales_invoice)

        self.assertTrue(result)
        mock_validate.assert_called_once_with(sales_invoice)
        mock_zatca_cls.assert_called_once_with(sales_invoice)
        zatca_invoice_data.get_submission_request_data.assert_called_once_with()
        mock_submit.assert_called_once_with({"encoded_invoice": "encoded"})
        zatca_invoice_data.get_generated_qr_code.assert_called_once_with()
        mock_outcome.assert_called_once_with(response, "generated_qr")
        mock_update.assert_called_once_with(sales_invoice, submission_outcome)
        zatca_invoice_data.get_log_context.assert_called_once_with()
        mock_log.assert_called_once_with(
            sales_invoice,
            {"uuid": "uuid"},
            response,
            "encoded",
            submission_outcome,
        )
        mock_manual_submit.assert_called_once_with()
        mock_policy.assert_called_once_with(True, sales_invoice.get("sales_invoice_type"), True)
        zatca_invoice_data.get_uuid.assert_called_once_with()
        mock_post.assert_called_once_with(sales_invoice, "uuid", follow_up_policy)

    def test_submit_sales_invoice_to_zatca_returns_false_when_validation_fails(self):
        sales_invoice = MagicMock()

        with (
            patch.object(workflow_module, "_validate_before_send", return_value=False) as mock_validate,
            patch.object(workflow_module, "ZatcaInvoiceData") as mock_zatca_cls,
        ):
            result = submit_sales_invoice_to_zatca(sales_invoice)

        self.assertFalse(result)
        mock_validate.assert_called_once_with(sales_invoice)
        mock_zatca_cls.assert_not_called()


class TestSendToZatcaEntrypoint(InvoiceTestCase):
    def test_send_to_zatca_loads_document_and_delegates_to_workflow(self):
        sales_invoice = MagicMock()

        with (
            patch.object(invoice_module.frappe, "get_doc", return_value=sales_invoice) as mock_get_doc,
            patch.object(
                invoice_module,
                "submit_sales_invoice_to_zatca",
                return_value=True,
            ) as mock_submit_workflow,
        ):
            result = send_to_zatca("SINV-0001")

        self.assertTrue(result)
        mock_get_doc.assert_called_once_with("Sales Invoice", "SINV-0001")
        mock_submit_workflow.assert_called_once_with(sales_invoice)
