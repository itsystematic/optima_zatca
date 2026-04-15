import frappe 
from frappe import _

import base64
from lxml import etree

import optima_zatca.zatca.prepayment_invoice as prepayment_invoice
from optima_zatca.zatca.logs import make_action_log
from optima_zatca.zatca.api import make_invoice_request
from optima_zatca.zatca.classes.invoice import ZatcaInvoiceData
from optima_zatca.zatca.utils import create_qr_code_for_invoice, log_and_throw_error


# Public API


@frappe.whitelist()
def send_to_zatca(sales_invoice_name) -> bool:
    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
    if not _validate_before_send(sales_invoice):
        return False

    invoice = ZatcaInvoiceData(sales_invoice)
    invoice_encoded = _encode_invoice_xml(invoice)
    response = _submit_to_zatca_api(invoice, invoice_encoded)
    success = _is_successful_response(response)
    qrcode = _get_response_qrcode(response, invoice, success)
    _update_invoice_document(sales_invoice, invoice, response, qrcode, success)
    _log_action(sales_invoice, invoice, response, invoice_encoded, qrcode, success)
    _handle_post_success(sales_invoice, invoice, success)
    return success


# Private orchestration helpers


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


def _encode_invoice_xml(invoice: ZatcaInvoiceData) -> str:
    """Encode the invoice XML payload for the API request."""
    return base64.b64encode(
        etree.tostring(invoice.xml.root, encoding="utf-8")
    ).decode("utf-8")


def _submit_to_zatca_api(invoice: ZatcaInvoiceData, invoice_encoded: str):
    """Send the prepared invoice payload to ZATCA."""
    zi = invoice.zatca_invoice
    return make_invoice_request(
        zi.get("Clearance-Status"),
        invoice.company_settings.get("authorization"),
        invoice.xml.hash,
        zi.get("UUID"),
        invoice_encoded,
        invoice.company_settings,
        zi.get("EndPoint"),
    )


def _is_successful_response(response) -> bool:
    """Treat accepted and warning responses as successful."""
    return response.status_code in [200, 202]


def _get_response_qrcode(response, invoice, success: bool) -> str:
    """Resolve the final QR code once for this request."""
    if not success:
        return ""

    return get_qr_code_from_zatca(response, invoice.xml.qr_code)


def _update_invoice_document(sales_invoice, invoice, response, qrcode: str, success: bool) -> None:
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


def _log_action(sales_invoice, invoice, response, invoice_encoded: str, qrcode: str, success: bool) -> None:
    """Write the ZATCA audit log entry for this send attempt."""
    zi = invoice.zatca_invoice
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
        uuid=zi.get("UUID"),
        invoice=invoice_encoded,
        hash=invoice.xml.hash,
        qr_code=qrcode,
        qr_code_generated=invoice.xml.qr_code,
        api_endpoint=zi.get("EndPoint"),
        environment=zi.get("Environment"),
        pih=zi.get("PIH"),
        icv=zi.get("InvoiceCounter"),
        xml_content=etree.tostring(invoice.xml.root, encoding="utf-8"),
        conclusion=conclusion,
    )


def _handle_post_success(sales_invoice, invoice, success: bool) -> None:
    """Run success-only follow-up actions after logging."""
    if not success:
        return

    if sales_invoice.get("sales_invoice_type") != "Normal":
        prepayment_invoice.create_prepayment_invoice(
            sales_invoice,
            invoice.zatca_invoice.get("UUID", ""),
        )

    manual_submit = frappe.db.get_single_value("Zatca Main Settings", "manual_submit")
    if not manual_submit:
        sales_invoice.submit()
        frappe.db.commit()


# Supporting utilities


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


def get_qr_code_from_zatca(zatca_response, generated_qrcode) -> str:
    from optima_zatca.zatca.classes.xml import get_qrcode_from_xml

    qrcode = generated_qrcode

    if zatca_response.status_code in [200 , 202] :
        response = zatca_response.json()
        cleared_invoice = response.get("clearedInvoice") if isinstance(response, dict) else None
        if cleared_invoice :
            invoice_xml = base64.b64decode(cleared_invoice).decode("utf-8")
            xml_qrcode = get_qrcode_from_xml(invoice_xml)
            if xml_qrcode :
                qrcode = xml_qrcode

    return qrcode
