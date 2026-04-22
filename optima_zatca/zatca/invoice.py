import frappe
from frappe import _

from optima_zatca.zatca.logs import make_action_log
from optima_zatca.zatca.api import make_invoice_request
from optima_zatca.zatca.classes.invoice import ZatcaInvoiceData
import optima_zatca.zatca.prepayment_invoice as prepayment_invoice
from optima_zatca.zatca.xml_transport import get_qr_code_from_cleared_invoice
from optima_zatca.zatca.utils import create_qr_code_for_invoice, log_and_throw_error


# Public API


@frappe.whitelist()
def send_to_zatca(sales_invoice_name) -> bool:
    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
    if not _validate_before_send(sales_invoice):
        return False

    zatca_invoice_data = ZatcaInvoiceData(sales_invoice)
    submission_request = zatca_invoice_data.get_submission_request_data()
    response = _submit_to_zatca_api(submission_request)
    success = _is_successful_response(response)
    qrcode = _get_response_qrcode(response, zatca_invoice_data.get_generated_qr_code(), success)
    _update_invoice_document(sales_invoice, response, qrcode, success)
    _log_action(
        sales_invoice,
        zatca_invoice_data.get_log_context(),
        response,
        submission_request["encoded_invoice"],
        qrcode,
        success,
    )
    _handle_post_success(sales_invoice, zatca_invoice_data.get_uuid(), success)
    return success


################################################################################
# Private orchestration helpers
################################################################################


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


def _is_successful_response(response) -> bool:
    """Treat accepted and warning responses as successful."""
    return response.status_code in [200, 202]


def _get_response_qrcode(response, generated_qr_code: str, success: bool) -> str:
    """Resolve the final QR code once for this request."""
    if not success:
        return ""

    return get_qr_code_from_cleared_invoice(response, generated_qr_code)


def _update_invoice_document(sales_invoice, response, qrcode: str, success: bool) -> None:
    """Persist invoice fields that depend on the ZATCA response."""
    if not success:
        frappe.msgprint(_("Your Invoice Was Rejected in Zatca"), title=_("Rejected"), indicator="red", alert=True)
        return

    response_json = response.json()
    sales_invoice.sent_to_zatca = 1
    sales_invoice.clearance_or_reporting = (
        response_json.get("clearanceStatus") or response_json.get("reportingStatus")
    )
    sales_invoice.ksa_einv_qr = create_qr_code_for_invoice(sales_invoice.name, qrcode)
    sales_invoice.save(ignore_permissions=True, ignore_version=True)

    frappe.msgprint(_("Your Invoice Was Accepted in Zatca"), title=_("Accepted"), indicator="green", alert=True)


def _log_action(sales_invoice, log_context: dict, response, invoice_encoded: str, qrcode: str, success: bool) -> None:
    """Write the ZATCA audit log entry for this send attempt."""
    status = "Success" if response.status_code == 200 else ("Warning" if success else "Failed")

    try:
        conclusion = format_zatca_response(response.json())
    except Exception:
        conclusion = response.text

    make_action_log(
        method="send_to_zatca",
        status=status,
        message=response.text,
        reference_doctype="Sales Invoice",
        reference_name=sales_invoice.name,
        company=sales_invoice.get("company"),
        commercial_register=sales_invoice.get("commercial_register"),
        uuid=log_context.get("uuid"),
        invoice=invoice_encoded,
        hash=log_context.get("invoice_hash"),
        qr_code=qrcode,
        qr_code_generated=log_context.get("generated_qr_code"),
        api_endpoint=log_context.get("api_endpoint"),
        environment=log_context.get("environment"),
        pih=log_context.get("pih"),
        icv=log_context.get("invoice_counter"),
        xml_content=log_context.get("xml_content"),
        conclusion=conclusion,
    )


def _handle_post_success(sales_invoice, invoice_uuid: str, success: bool) -> None:
    """Run success-only follow-up actions after logging."""
    if not success:
        return

    if sales_invoice.get("sales_invoice_type") != "Normal":
        prepayment_invoice.create_prepayment_invoice(
            sales_invoice,
            invoice_uuid,
        )

    manual_submit = frappe.db.get_single_value("Zatca Main Settings", "manual_submit")
    if not manual_submit:
        sales_invoice.submit()
        frappe.db.commit()


#################################################################################
# Supporting utilities
#################################################################################


def format_zatca_response(response: dict) -> str:
    """Collapse validation results into a short user-facing summary."""
    validation_results = response.get('validationResults', {})
    error_messages = validation_results.get('errorMessages', [])
    warning_messages = validation_results.get('warningMessages', [])

    # Check for error messages first
    if error_messages:
        result = "🔴 Failed Invoice\n"
        for error in error_messages:
            result += f"{error['message']}\n"
        return result.rstrip()  # Remove trailing newline

    # Check for warning messages
    elif warning_messages:
        result = "🟡 Success Invoice but there is a Warning\n"
        for warning in warning_messages:
            result += f"{warning['message']}\n"
        return result.rstrip()  # Remove trailing newline

    # No errors or warnings
    else:
        return "🟢 Success Invoice"
