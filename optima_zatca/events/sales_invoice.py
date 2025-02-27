import io
import os
import frappe
from frappe import _
from base64 import b64encode
from erpnext import get_region
from pyqrcode import create as qr_create
from frappe.utils import getdate , get_time , add_to_date


def sales_invoice_on_cancel(doc , event) :

    enable_cancel_invoice = frappe.db.get_single_value("Zatca Main Settings" , "enable_cancel_invoice")
    
    if doc.get("sent_to_zatca") and doc.get("clearance_or_reporting") in ["CLEARED" , "REPORTED"] and not enable_cancel_invoice :
        frappe.throw(_("No Permission To Cancel Invoice Sent To Zatca") , title=_("Zatca Permission"))


def sales_invoice_on_trash(doc , event) :

    enable_delete_invoice = frappe.db.get_single_value("Zatca Main Settings" , "enable_delete_invoice")

    if doc.get("sent_to_zatca") and doc.get("clearance_or_reporting") in ["CLEARED" , "REPORTED"] and not enable_delete_invoice :
        frappe.throw(_("No Permission To Delete Invoice Sent To Zatca") , title=_("Zatca Permission"))



def sales_invoice_on_submit(doc , event) :


    if doc.clearance_or_reporting not in  ["REPORTED" ,"CLEARED"]:
        frappe.throw(_("Invoice Not Reported Yet") , title=_("Zatca Error"))


    enable_phase_one = frappe.db.get_single_value("Zatca Main Settings" , "phase") == "Phase One"

    if not enable_phase_one  or doc.get("sent_to_zatca") == 1 : return 

    region = get_region(doc.company)
    if region not in ['Saudi Arabia']:
        return

    # Don't create QR Code if it already exists
    qr_code = doc.get("ksa_einv_qr")
    if qr_code and frappe.db.exists({"doctype": "File", "file_url": qr_code}):
        return

    tlv_array = []
    # Sellers Name

    seller_name = frappe.db.get_value('Company',doc.company,'company_name_in_arabic')

    if not seller_name:
        frappe.throw(_('Arabic name missing for {} in the company document').format(doc.company))

    tag = bytes([1]).hex()
    length = bytes([len(seller_name.encode('utf-8'))]).hex()
    value = seller_name.encode('utf-8').hex()
    tlv_array.append(''.join([tag, length, value]))

    # VAT Number
    tax_id = frappe.db.get_value('Company', doc.company, 'tax_id')
    if not tax_id:
        frappe.throw(_('Tax ID missing for {} in the company document').format(doc.company))

    tag = bytes([2]).hex()
    length = bytes([len(tax_id)]).hex()
    value = tax_id.encode('utf-8').hex()
    tlv_array.append(''.join([tag, length, value]))

    # Time Stamp
    posting_date = getdate(doc.posting_date)
    time = get_time(doc.posting_time)
    seconds = time.hour * 60 * 60 + time.minute * 60 + time.second
    time_stamp = add_to_date(posting_date, seconds=seconds)
    time_stamp = time_stamp.strftime('%Y-%m-%dT%H:%M:%SZ')

    tag = bytes([3]).hex()
    length = bytes([len(time_stamp)]).hex()
    value = time_stamp.encode('utf-8').hex()
    tlv_array.append(''.join([tag, length, value]))

    # Invoice Amount
    invoice_amount = str(doc.grand_total)
    tag = bytes([4]).hex()
    length = bytes([len(invoice_amount)]).hex()
    value = invoice_amount.encode('utf-8').hex()
    tlv_array.append(''.join([tag, length, value]))

    # VAT Amount
    total_vat_amount = 0
    taxes_rate = []
    accounts_type_tax = frappe.get_list("Item Tax Template" , {"company" : doc.company , "disabled" : 0} ,['`tabItem Tax Template Detail`.tax_type'] , join="Left join")
    tax_accounts = list(map(lambda x : x.get("tax_type") , accounts_type_tax))
    vat_amount_row  = list(filter(lambda x : x.get("account_head") in tax_accounts , doc.taxes))
    
    for tax in vat_amount_row :
        
        if tax.get("rate")  in taxes_rate :
            frappe.throw(_("VAT {} is Duplicated in Document {}").format(tax.get("rate"),doc.name))
        total_vat_amount += tax.get("tax_amount")
        taxes_rate.append(tax.get("rate"))
        
    vat_amount = str(total_vat_amount)
    tag = bytes([5]).hex()
    length = bytes([len((vat_amount))]).hex()
    value = vat_amount.encode('utf-8').hex()
    tlv_array.append(''.join([tag, length, value]))

    # Joining bytes into one
    tlv_buff = ''.join(tlv_array)

    # base64 conversion for QR Code
    base64_string = b64encode(bytes.fromhex(tlv_buff)).decode()

    qr_image = io.BytesIO()
    url = qr_create(base64_string, error='L')
    url.png(qr_image, scale=2, quiet_zone=1)

    name = frappe.generate_hash(doc.name, 5)

    # making file
    filename = f"QRCode-{name}.png".replace(os.path.sep, "__")
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "is_private": 0,
        "content": qr_image.getvalue(),
        "attached_to_doctype": doc.get("doctype"),
        "attached_to_name": doc.get("name"),
        "attached_to_field": "ksa_einv_qr"
    })

    _file.save()

    # assigning to document
    doc.db_set('ksa_einv_qr', _file.file_url)
    doc.notify_update()