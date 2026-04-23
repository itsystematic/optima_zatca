from dataclasses import dataclass

import frappe
from frappe import _

from optima_zatca.zatca.logs import make_action_log
from optima_zatca.zatca.api import make_invoice_request
from optima_zatca.zatca.classes.invoice import ZatcaInvoiceData
import optima_zatca.zatca.prepayment_invoice as prepayment_invoice
from optima_zatca.zatca.xml_transport import get_qr_code_from_cleared_invoice
from optima_zatca.zatca.utils import create_qr_code_for_invoice, log_and_throw_error


@dataclass(frozen=True)
class SubmissionOutcome:
    """Business decision output derived from a ZATCA response."""

    is_success: bool
    invoice_status: str | None
    response_qrcode: str
    log_status: str
    log_conclusion: str


@dataclass(frozen=True)
class PostSuccessPolicy:
    """Business decision output for success-only follow-up actions."""

    create_prepayment_invoice: bool
    auto_submit_invoice: bool


def submit_sales_invoice_to_zatca(sales_invoice) -> bool:
    """Run the ZATCA submission workflow for a loaded Sales Invoice document."""
    if not _validate_before_send(sales_invoice):
        return False

    zatca_invoice_data = ZatcaInvoiceData(sales_invoice)
    submission_request = zatca_invoice_data.get_submission_request_data()
    response = _submit_to_zatca_api(submission_request)
    submission_outcome = _decide_submission_outcome(
        response,
        zatca_invoice_data.get_generated_qr_code(),
    )
    _update_invoice_document(sales_invoice, submission_outcome)
    _log_action(
        sales_invoice,
        zatca_invoice_data.get_log_context(),
        response,
        submission_request["encoded_invoice"],
        submission_outcome,
    )
    follow_up_policy = _decide_post_success_policy(
        submission_outcome.is_success,
        sales_invoice.get("sales_invoice_type"),
        _is_manual_submit_enabled(),
    )
    _execute_post_success_actions(
        sales_invoice,
        zatca_invoice_data.get_uuid(),
        follow_up_policy,
    )
    return submission_outcome.is_success


def _validate_before_send(sales_invoice) -> bool:
    """Stop early if Frappe validation or submit permissions fail."""
    try:
        sales_invoice.run_method("validate")
        sales_invoice.run_method("before_submit")
        sales_invoice.check_permission("submit")
        return True
    except Exception as e:
        log_and_throw_error(
            operation="Send to ZATCA",
            document_name=sales_invoice.name,
            exception=e,
        )
        return False


def _submit_to_zatca_api(submission: dict):
    """Send the prepared invoice payload to ZATCA."""
    return make_invoice_request(
        submission.get("clearance_status"),
        submission.get("authorization"),
        submission.get("invoice_hash"),
        submission.get("uuid"),
        submission.get("encoded_invoice"),
        submission.get("company_settings"),
        submission.get("endpoint"),
    )


def _decide_submission_outcome(response, generated_qr_code: str) -> SubmissionOutcome:
    """Decide the business outcome of a ZATCA submission response."""
    is_success = _is_success_status_code(response.status_code)
    return SubmissionOutcome(
        is_success=is_success,
        invoice_status=_decide_invoice_status(response, is_success),
        response_qrcode=_decide_response_qrcode(response, generated_qr_code, is_success),
        log_status=_decide_log_status(response.status_code, is_success),
        log_conclusion=_decide_log_conclusion(response),
    )


def _is_success_status_code(status_code: int) -> bool:
    """Treat accepted and warning statuses as successful."""
    return status_code in [200, 202]


def _decide_invoice_status(response, is_success: bool) -> str | None:
    """Decide the invoice clearance or reporting status from a successful response."""
    if not is_success:
        return None

    response_json = response.json()
    return response_json.get("clearanceStatus") or response_json.get("reportingStatus")


def _decide_response_qrcode(response, generated_qr_code: str, is_success: bool) -> str:
    """Decide which QR code should be persisted for this submission."""
    if not is_success:
        return ""

    return get_qr_code_from_cleared_invoice(response, generated_qr_code)


def _decide_log_status(status_code: int, is_success: bool) -> str:
    """Decide the log status label for this response."""
    if status_code == 200:
        return "Success"

    if is_success:
        return "Warning"

    return "Failed"


def _decide_log_conclusion(response) -> str:
    """Decide the user-facing summary stored in the action log."""
    try:
        return format_zatca_response(response.json())
    except Exception:
        return response.text


def _update_invoice_document(sales_invoice, submission_outcome: SubmissionOutcome) -> None:
    """Persist invoice fields that depend on the ZATCA response."""
    if not submission_outcome.is_success:
        frappe.msgprint(_("Your Invoice Was Rejected in Zatca"), title=_("Rejected"), indicator="red", alert=True)
        return

    sales_invoice.sent_to_zatca = 1
    sales_invoice.clearance_or_reporting = submission_outcome.invoice_status
    sales_invoice.ksa_einv_qr = create_qr_code_for_invoice(sales_invoice.name, submission_outcome.response_qrcode)
    sales_invoice.save(ignore_permissions=True, ignore_version=True)

    frappe.msgprint(_("Your Invoice Was Accepted in Zatca"), title=_("Accepted"), indicator="green", alert=True)


def _log_action(
    sales_invoice,
    log_context: dict,
    response,
    invoice_encoded: str,
    submission_outcome: SubmissionOutcome,
) -> None:
    """Write the ZATCA audit log entry for this send attempt."""
    make_action_log(
        method="send_to_zatca",
        status=submission_outcome.log_status,
        message=response.text,
        reference_doctype="Sales Invoice",
        reference_name=sales_invoice.name,
        company=sales_invoice.get("company"),
        commercial_register=sales_invoice.get("commercial_register"),
        uuid=log_context.get("uuid"),
        invoice=invoice_encoded,
        hash=log_context.get("invoice_hash"),
        qr_code=submission_outcome.response_qrcode,
        qr_code_generated=log_context.get("generated_qr_code"),
        api_endpoint=log_context.get("api_endpoint"),
        environment=log_context.get("environment"),
        pih=log_context.get("pih"),
        icv=log_context.get("invoice_counter"),
        xml_content=log_context.get("xml_content"),
        conclusion=submission_outcome.log_conclusion,
    )


def _decide_post_success_policy(
    is_success: bool,
    sales_invoice_type: str | None,
    manual_submit_enabled: bool,
) -> PostSuccessPolicy:
    """Decide which follow-up actions should run after a successful submission."""
    if not is_success:
        return PostSuccessPolicy(
            create_prepayment_invoice=False,
            auto_submit_invoice=False,
        )

    return PostSuccessPolicy(
        create_prepayment_invoice=sales_invoice_type != "Normal",
        auto_submit_invoice=not manual_submit_enabled,
    )


def _is_manual_submit_enabled() -> bool:
    """Read whether invoice submission should remain manual after ZATCA success."""
    return bool(frappe.db.get_single_value("Zatca Main Settings", "manual_submit"))


def _execute_post_success_actions(
    sales_invoice,
    invoice_uuid: str,
    follow_up_policy: PostSuccessPolicy,
) -> None:
    """Execute follow-up side effects after the workflow decides they should run."""
    if follow_up_policy.create_prepayment_invoice:
        prepayment_invoice.create_prepayment_invoice(
            sales_invoice,
            invoice_uuid,
        )

    if follow_up_policy.auto_submit_invoice:
        sales_invoice.submit()
        frappe.db.commit()


def format_zatca_response(response: dict) -> str:
    """Collapse validation results into a short user-facing summary."""
    validation_results = response.get("validationResults", {})
    error_messages = validation_results.get("errorMessages", [])
    warning_messages = validation_results.get("warningMessages", [])

    if error_messages:
        result = "🔴 Failed Invoice\n"
        for error in error_messages:
            result += f"{error['message']}\n"
        return result.rstrip()

    if warning_messages:
        result = "🟡 Success Invoice but there is a Warning\n"
        for warning in warning_messages:
            result += f"{warning['message']}\n"
        return result.rstrip()

    return "🟢 Success Invoice"
