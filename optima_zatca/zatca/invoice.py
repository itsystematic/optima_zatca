import json
import traceback
import frappe 
import base64
from frappe import _
from lxml import etree
from frappe.utils import flt
from optima_zatca.zatca.logs import make_action_log
from optima_zatca.zatca.api import make_invoice_request
from optima_zatca.zatca.utils import create_qr_code_for_invoice, log_and_throw_error
from optima_zatca.zatca.classes.invoice import ZatcaInvoiceData
# from erpnext.controllers.taxes_and_totals import get_itemised_tax


@frappe.whitelist()
def send_to_zatca(sales_invoice_name):

    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
    invoice = ZatcaInvoiceData(sales_invoice)
    invoice_encoded = base64.b64encode(etree.tostring(invoice.xml.root , encoding="utf-8")).decode("utf-8")

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
        xml_content = etree.tostring(invoice.xml.root , encoding="utf-8")
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




def update_itemised_tax_data(doc):
    try:
        if not doc.taxes: return

        if doc.doctype == "Purchase Invoice": return

        itemised_tax = get_itemised_tax(doc.taxes)

        for row in doc.items:
            try:
                tax_rate = 0.0
                # item_tax_rate = 0.0
                tax_amount = 0.00
                included_in_print_rate = 0
                
                if row.get("item_tax_template") :
                    row.tax_category = frappe.db.get_value("Item Tax Template" , row.item_tax_template , "tax_category", cache=True) # Use caching for frequent lookups

                # if row.item_tax_rate:
                #     item_tax_rate = frappe.parse_json(row.item_tax_rate)

                if row.item_code and itemised_tax.get(row.item_code):

                    for d, tax in itemised_tax.get(row.item_code).items() :
                        tax_rate += tax.get('tax_rate', 0)
                        tax_amount += tax.get("tax_amount")
                        included_in_print_rate += tax.get("included_in_print_rate")

                row.tax_rate = flt(tax_rate, row.precision("tax_rate"))

                
                if included_in_print_rate :
                    row.line_extension_amount = flt(row.amount / ( ( row.tax_rate / 100 ) + 1 ) , 2)
                    taxable_amount = flt(row.amount / ( ( row.tax_rate / 100 ) + 1 ) , 2 )
                    row.price_amount = flt(taxable_amount / row.get("qty") , 2)
                    row.tax_amount = flt(row.amount - taxable_amount , 2)
                    original_net_total = doc.net_total + ( doc.get("discount_amount" , 0.00) or 0.00 )
                    row.total_amount = row.amount

                else :
                    # XML Fields ( in Normal Case )
                    row.price_amount = row.rate 
                    row.line_extension_amount = flt(row.amount , 2 ) 
                    taxable_amount = flt(row.net_amount , 2)
                    row.tax_amount = flt(row.line_extension_amount * ( row.tax_rate / 100 ) , 2) 
                    original_net_total = doc.net_total 
                    row.total_amount = flt(( row.line_extension_amount + row.tax_amount), 2)
                    
                row.item_discount = flt((doc.discount_amount) * taxable_amount / original_net_total, 2 ) if doc.get("discount_amount") else 0.00
            except Exception as e:
                    frappe.log_error(
                        title=f"Failed to process item {row.idx}",
                        message=f"Item: {row.item_code}\nError: {str(e)}\n{traceback.format_exc()}"
                    )
                    # Set safe defaults to avoid breaking the document
                    row.tax_rate = 0.0
                    row.tax_amount = 0.0

                    raise frappe.ValidationError("Tax calculation failed. Check Error Log.")
    except Exception as e:
        log_and_throw_error(
            operation = "update_itemised_tax_data",
            document_name = doc.name,
            exception = e
        )
        # frappe.log_error(
        #     title=f"Failed in update_itemised_tax_data for {doc.name}",
        #     message=f"Document: {doc.doctype} {doc.name}\nError: {str(e)}\n{traceback.format_exc()}"
        # )
        # # Re-raise if you want the document save to fail visibly
        # frappe.throw("Tax calculation failed. Check Error Log.")



def get_itemised_tax(taxes):

	itemised_tax = {}
	for tax in taxes:
		if getattr(tax, "category", None) and tax.category == "Valuation":
			continue

		item_tax_map = json.loads(tax.item_wise_tax_detail) if tax.item_wise_tax_detail else {}

		if item_tax_map:
			for item_code, tax_data in item_tax_map.items():
				itemised_tax.setdefault(item_code, frappe._dict())

				tax_rate = 0.0
				tax_amount = 0.0

				if isinstance(tax_data, list):
					tax_rate = flt(tax_data[0])
					tax_amount = flt(tax_data[1])
				else:
					tax_rate = flt(tax_data)

				itemised_tax[item_code][tax.description] = frappe._dict(dict(
                    tax_rate=tax_rate, 
                    tax_amount=tax_amount , 
                    included_in_print_rate=tax.included_in_print_rate , 
                    tax_account = tax.account_head
                ))

	return itemised_tax

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

        # Create and insert the document
        new_prepayment = frappe.get_doc({
            "doctype": "Prepayment Invoice",
            "uuid": uuid,
            "percent": percent,
            "issue_time": issue_time,
            "prepayment_type_code": "386",
            "id": sales_invoice.get("name"),
            "customer": sales_invoice.get("customer"),
            "sales_invoice": sales_invoice.get("name"),
            "is_return": sales_invoice.get("is_return"),
            "adjustment_percentage": adjustment_percentage,
            "issue_date": sales_invoice.get("posting_date"),
            "grand_total": sales_invoice.get("grand_total"),
            "tax_category": sales_invoice.get("tax_category"),
            "has_previous_prepayment": has_previous_prepayment,
            "is_debit_note": sales_invoice.get("is_debit_note"),
            "prepayment_type": prepayment_type,
            "previous_prepayment_invoice": previous_prepayment_invoice,
            "tax_amount": sales_invoice.get("total_taxes_and_charges"),
            "remaining_percentage": sales_invoice.get("remaining_percentage"),
            "taxable_amount": sales_invoice.get("total") or sales_invoice.get("net_total"),
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
    
    # Zero-pad the hours if needed
    parts = time_str.split(":")
    if len(parts) >= 1:
        parts[0] = parts[0].zfill(2)
        time_str = ":".join(parts)
        
    return time_str


def get_tax_rate_from_items(sales_invoice: dict) -> float:
    """Extract tax rate from the first item in the sales invoice."""
    items = sales_invoice.get("items", [])
    return items[0].get("tax_rate") if items else 0


# def log_and_throw_error(invoice_name: str, exception: Exception) -> None:
#     """Log the error and throw a user-friendly message."""
#     error_message = str(exception)
#     error_trace = traceback.format_exc()
    
#     frappe.log_error(
#         title=f"Failed to create Prepayment Invoice for {invoice_name}",
#         message=f"Error: {error_message}\n{error_trace}"
#     )
#     frappe.throw(_("Failed to create Prepayment Invoice. Check Error Log."))
