import json
import frappe 
import base64
from frappe import _
from lxml import etree
from frappe.utils import flt
from optima_zatca.zatca.logs import make_action_log
from optima_zatca.zatca.api import make_invoice_request
from optima_zatca.zatca.utils import create_qr_code_for_invoice
from optima_zatca.zatca.classes.invoice import ZatcaInvoiceData
# from erpnext.controllers.taxes_and_totals import get_itemised_tax


@frappe.whitelist()
def send_to_zatca(sales_invoice_name):

    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
    invoice = ZatcaInvoiceData(sales_invoice)
    invoice_encoded = base64.b64encode(etree.tostring(invoice.xml.root , encoding="utf-8")).decode("utf-8")

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
    if response.status_code in [200 , 202]: 
        ResponseJson = response.json()
        sales_invoice.db_set({
            "sent_to_zatca" : 1  ,
            "clearance_or_reporting" : ResponseJson.get("clearanceStatus") or ResponseJson.get("reportingStatus")
        }, commit=True)

        frappe.msgprint(_("Your Invoice Was Accepted in Zatca"), title=  _("Accepted"),indicator="green" ,alert=True)
        
        Status = "Success"  if response.status_code == 200 else "Warning"  
        qrcode = get_qr_code_from_zatca(response , invoice.xml.qr_code)
        qrcode_url = create_qr_code_for_invoice(sales_invoice.name , qrcode)
        frappe.db.set_value("Sales Invoice", sales_invoice.name ,{"ksa_einv_qr" : qrcode_url})
        manual_submit = frappe.db.get_single_value("Zatca Main Settings", "manual_submit")
        if not manual_submit : # Auto Submit
            sales_invoice.reload()
            sales_invoice.submit()

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

    return True if response.status_code in [200 , 202] else False


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
    if not doc.taxes: return

    itemised_tax = get_itemised_tax(doc.taxes)

    for row in doc.items:
        tax_rate = 0.0
        # item_tax_rate = 0.0
        tax_amount = 0.00
        included_in_print_rate = 0
        
        if row.get("item_tax_template") :
            row.tax_category = frappe.db.get_value("Item Tax Template" , row.item_tax_template , "tax_category")

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