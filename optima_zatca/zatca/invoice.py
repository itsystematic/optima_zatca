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
from erpnext.controllers.taxes_and_totals import get_itemised_tax


@frappe.whitelist()
def send_to_zatca(sales_invoice_name):


    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
    invoice = ZatcaInvoiceData(sales_invoice)
    invoice_encoded = base64.b64encode(etree.tostring(invoice.xml.root)).decode()

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
        sales_invoice.db_set("send_to_zatca" , 1 , commit=True)
        frappe.msgprint(_("Your Invoice Was Accepted in Zatca"), title=  _("Accepted"),indicator="green" ,alert=True)
        
        Status = "Success"  if response.status_code == 200 else "Warning"  
        qrcode = get_qr_code_from_zatca(response , invoice.xml.qr_code)
        qrcode_url = create_qr_code_for_invoice(sales_invoice_name , qrcode)
        frappe.db.set_value("Sales Invoice", sales_invoice_name ,{
            "clearance_or_reporting" : ResponseJson.get("clearanceStatus") or ResponseJson.get("reportingStatus") ,
            "ksa_einv_qr" : qrcode_url
        })

    else :
        frappe.msgprint(_("Your Invoice Was Rejected in Zatca"), title=  _("Rejected"), indicator="red" , alert=True)
            

    make_action_log(
        method ="send_to_zatca" ,
        status = Status  ,
        message = response.text ,
        reference_doctype = "Sales Invoice",
        reference_name = sales_invoice_name,
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
        icv = invoice.zatca_invoice.get("InvoiceCounter")
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
        item_tax_rate = 0.0
        
        if row.get("item_tax_template") :
            row.tax_category = frappe.db.get_value("Item Tax Template" , row.item_tax_template , "tax_category")

        if row.item_tax_rate:
            item_tax_rate = frappe.parse_json(row.item_tax_rate)

        if item_tax_rate:
            for account, rate in item_tax_rate.items():
                tax_rate += rate
        elif row.item_code and itemised_tax.get(row.item_code):
            tax_rate = sum([tax.get('tax_rate', 0) for d, tax in itemised_tax.get(row.item_code).items()])

        row.tax_rate = flt(tax_rate, row.precision("tax_rate"))
        row.tax_amount = flt((row.net_amount * tax_rate) / 100, row.precision("net_amount"))
        row.total_amount = flt((row.net_amount + row.tax_amount), row.precision("total_amount"))