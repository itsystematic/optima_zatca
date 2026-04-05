import frappe 
from frappe import _

import base64
from lxml import etree

from optima_zatca.zatca.logs import make_action_log
from optima_zatca.zatca.api import make_invoice_request
from optima_zatca.zatca.classes.invoice import ZatcaInvoiceData
from optima_zatca.zatca.utils import create_qr_code_for_invoice, log_and_throw_error


def format_zatca_response(response):
    """
    Format ZATCA validation response into human-readable message.
    
    Args:
        response (dict): ZATCA response dictionary
        
    Returns:
        str: Formatted human-readable message
    """
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


def _encode_invoice_xml(invoice: ZatcaInvoiceData) -> str:
    """Serializes invoice XML to base64-encoded UTF-8 string."""
    return base64.b64encode(
        etree.tostring(invoice.xml.root, encoding="utf-8")
    ).decode("utf-8")


@frappe.whitelist()
def send_to_zatca(sales_invoice_name):

    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
    invoice = ZatcaInvoiceData(sales_invoice)
    invoice_encoded = _encode_invoice_xml(invoice)

    # Run all validations and pre-submit hooks BEFORE sending to ZATCA for auto-submit later
    try:
        sales_invoice.run_method("validate")
        sales_invoice.run_method("before_submit")
        sales_invoice.check_permission("submit")
        
    except Exception as e:
        log_and_throw_error(
            operation="Send to ZATCA",
            document_name = sales_invoice.name,
            exception=e
        )
        return False


    response = make_invoice_request(
        invoice.zatca_invoice.get("Clearance-Status") , 
        invoice.company_settings.get("authorization") , 
        invoice.xml.hash , 
        invoice.zatca_invoice.get("UUID") , 
        invoice_encoded , 
        invoice.company_settings , 
        invoice.zatca_invoice.get("EndPoint")
    )
    Status , qrcode = "Failed" , ""
    sucess_status = response.status_code in [200 , 202]

    if sucess_status: 
        ResponseJson = response.json()
        sales_invoice.sent_to_zatca = 1
        sales_invoice.clearance_or_reporting = ResponseJson.get("clearanceStatus") or ResponseJson.get("reportingStatus")

        frappe.msgprint(_("Your Invoice Was Accepted in Zatca"), title=  _("Accepted"),indicator="green" ,alert=True)
        
        Status = "Success"  if response.status_code == 200 else "Warning"  
        qrcode = get_qr_code_from_zatca(response , invoice.xml.qr_code)
        qrcode_url = create_qr_code_for_invoice(sales_invoice.name , qrcode)
        sales_invoice.ksa_einv_qr = qrcode_url

        # Save the document with ZATCA updates
        sales_invoice.save(ignore_permissions=True, ignore_version=True)


    else :
        frappe.msgprint(_("Your Invoice Was Rejected in Zatca"), title=  _("Rejected"), indicator="red" , alert=True)
            
    # Format the conclusion from response
    try:
        conclusion_text = format_zatca_response(response.json())
    except Exception:
        conclusion_text = response.text

    make_action_log(
        method ="send_to_zatca" ,
        status = Status  ,
        message = response.text ,
        reference_doctype = "Sales Invoice",
        reference_name = sales_invoice.name,
        company = sales_invoice.get("company") ,
        commercial_register = sales_invoice.get("commercial_register") ,
        uuid = invoice.zatca_invoice.get("UUID"),
        invoice = invoice_encoded,
        hash = invoice.xml.hash ,
        qr_code = qrcode ,
        qr_code_generated = invoice.xml.qr_code ,
        api_endpoint = invoice.zatca_invoice.get("EndPoint") ,
        environment = invoice.zatca_invoice.get("Environment"),
        pih = invoice.zatca_invoice.get("PIH"),
        icv = invoice.zatca_invoice.get("InvoiceCounter"),
        xml_content = etree.tostring(invoice.xml.root , encoding="utf-8"),
        conclusion = conclusion_text
    )

    # Create Prepayment Invoice doctype when success
    if sales_invoice.get("sales_invoice_type") != "Normal" and sucess_status:
        create_prepayment_invoice(sales_invoice, invoice.zatca_invoice.get("UUID", ""))

    manual_submit = frappe.db.get_single_value("Zatca Main Settings", "manual_submit")
    if not manual_submit and sucess_status: # Auto Submit
        sales_invoice.submit()
        frappe.db.commit()
        
    return True if sucess_status else False


def get_qr_code_from_zatca(zatca_response, generated_qrcode) :
    from optima_zatca.zatca.classes.xml import get_qrcode_from_xml

    qrcode = generated_qrcode

    if zatca_response.status_code in [200 , 202] :
        response = zatca_response.json()
        if response.get("clearedInvoice") :
            invoice_xml = base64.b64decode(response.get("clearedInvoice")).decode("utf-8")
            xml_qrcode = get_qrcode_from_xml(invoice_xml)
            if xml_qrcode :
                qrcode = xml_qrcode

    return qrcode


def create_prepayment_invoice(sales_invoice, uuid: str) -> None:
    """
    Create a Prepayment Invoice document from a Sales Invoice.
    
    Args:
        sales_invoice: frappe Document containing sales invoice data
        uuid: Unique identifier for the prepayment invoice
        
    Raises:
        frappe.ValidationError: If prepayment invoice creation fails
    """
    try:
        issue_time = format_issue_time(sales_invoice.posting_time)
        has_previous_prepayment = True if sales_invoice.previous_prepayment else False
        previous_prepayment_invoice = sales_invoice.previous_prepayment
        percent = (sales_invoice.items or [{}])[0].get("tax_rate", 0)
        prepayment_type = sales_invoice.sales_invoice_type
        adjustment_percentage = sales_invoice.adjustment_percentage * -1 if sales_invoice.is_return else sales_invoice.adjustment_percentage

        # Get sales_order value based on priority
        sales_order = None
        # Priority 1: Check prepayment_sales_order field
        if sales_invoice.get("prepayment_sales_order"):
            sales_order = sales_invoice.get("prepayment_sales_order")
        # Priority 2: Check first item's sales_order field
        elif sales_invoice.items and sales_invoice.items[0].get("sales_order"):
            sales_order = sales_invoice.items[0].get("sales_order")

        # mark the previous invoice as "Is Linked"
        if sales_invoice.previous_prepayment:
            frappe.db.set_value("Prepayment Invoice", sales_invoice.previous_prepayment, "is_linked", 1)

        # mark the invoice which was acctually returned against The returned invoice as "Been Returned"
        if sales_invoice.return_against:
            frappe.db.set_value("Prepayment Invoice", sales_invoice.return_against, "been_return", 1)
            frappe.db.set_value("Prepayment Invoice", sales_invoice.return_against, "is_linked", 1)
            
            # revert back the final to adjustment and set the adjustment percentage to zero to continue the pepayment chain later
            if sales_invoice.sales_invoice_type == "Final Adjustment":
                prepayment_type = "Adjustment"
                frappe.db.set_value("Prepayment Invoice", sales_invoice.return_against, "prepayment_type", "Adjustment")

        # To keep the linked chain ensure the reutuned invoice always has a previous, even initial prepayment
        if sales_invoice.is_return:
            has_previous_prepayment = True
            previous_prepayment_invoice = sales_invoice.return_against

        # Store company currency amounts (base_ fields if available, fallback to regular fields)
        # This ensures we always store amounts in company currency
        grand_total = sales_invoice.get("base_grand_total") or sales_invoice.get("grand_total")
        tax_amount = sales_invoice.get("base_total_taxes_and_charges") or sales_invoice.get("total_taxes_and_charges")
        taxable_amount = sales_invoice.get("base_net_total") or sales_invoice.get("net_total")

        # Create and insert the document
        new_prepayment = frappe.get_doc({
            "doctype": "Prepayment Invoice",
            "uuid": uuid,
            "percent": percent,
            "issue_time": issue_time,
            "prepayment_type_code": "386",
            "id": sales_invoice.get("name"),
            "customer": sales_invoice.get("customer"),
            "currency": sales_invoice.get("currency"),
            "sales_invoice": sales_invoice.get("name"),
            "sales_order": sales_order,
            "is_return": sales_invoice.get("is_return"),
            "adjustment_percentage": adjustment_percentage,
            "issue_date": sales_invoice.get("posting_date"),
            "grand_total": grand_total,
            "tax_category": sales_invoice.get("tax_category"),
            "has_previous_prepayment": has_previous_prepayment,
            "is_debit_note": sales_invoice.get("is_debit_note"),
            "prepayment_type": prepayment_type,
            "previous_prepayment_invoice": previous_prepayment_invoice,
            "tax_amount": tax_amount,
            "remaining_percentage": sales_invoice.get("remaining_percentage"),
            "taxable_amount": taxable_amount,
        })
        new_prepayment.insert(ignore_permissions=True)
    except Exception as e:
        log_and_throw_error(
            operation = "create prepayment invoice",
            document_name = sales_invoice.name,
            exception = e
        )


def format_issue_time(posting_time: str) -> str:
    """Format a posting time value to HH:MM:SS string.
    
    Args:
        posting_time: A time value (timedelta, string, etc.)
        
    Returns:
        Formatted time string in HH:MM:SS format
    """
    if not posting_time:
        return ""
        
    time_str = str(posting_time)
    
    # If there's a decimal point (microseconds), truncate it
    if "." in time_str:
        time_str = time_str.split(".")[0]
    
    # Zero-pad all time components if needed
    parts = time_str.split(":")
    if len(parts) >= 1:
        parts = [part.zfill(2) for part in parts]
        time_str = ":".join(parts)
        
    return time_str


def get_tax_rate_from_items(sales_invoice: dict) -> float:
    """Extract tax rate from the first item in the sales invoice."""
    items = sales_invoice.get("items", [])
    return items[0].get("tax_rate") if items else 0
