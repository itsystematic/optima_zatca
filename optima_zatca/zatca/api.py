import json 
import base64
import frappe
from frappe import _
from optima_zatca.zatca.request import make_post_request , make_get_request
# from optima.zatcainvoice.classes.invoice import ZatcaInvoiceData
# from optima.zatcainvoice.logs import create_zatca_logs

@frappe.whitelist()
def get_zatca_csid(setting:str, otp:str , csr:str) -> dict:

    response = make_post_request(
        setting= setting ,
        endpoint= "compliance" ,
        header={
            "OTP": otp,
            "Accept-Version": "V2",
            "Content-Type": "application/json",
            "accept" : "application/json",
        },
        json_data={
            "csr": csr,
        }
    )

    if not  response.status_code == 200 :
        frappe.throw(str(response.text))

    
    res = response.json()
    
    return res.get("requestID") , res.get("binarySecurityToken") , res.get("secret")
        

@frappe.whitelist()
def get_production_csid(company , binary_security_token , secret , csid) -> dict:
    auth = base64.b64encode("{0}:{1}".format(binary_security_token,secret).encode()).decode("utf-8")
    
    response = make_post_request(
        company= company ,
        endpoint= "onboarding" ,
        header = {
            "accept": "application/json",
            "Accept-Language": "en",
            "Accept-Version": "V2",
            "Authorization": "Basic " + auth,
            "Content-Type": "application/json",
        },
        json_data={
            "compliance_request_id" : csid
        }
    )

    if not  response.status_code == 200 :
        frappe.throw(str(response.text))
    
    return response.json()



def make_invoice_request(clearance_status , authentication , invoice_hash , invoice_uuid , invoice_encoded , setting , endpoint):

    response = make_post_request(
        setting=setting,
        endpoint=endpoint,
        header= {
            "accept": "application/json",
            "Accept-Language": "en",
            "Clearance-Status": clearance_status,
            "Accept-Version": "V2",
            "Authorization": "Basic " + authentication,
            "Content-Type": "application/json",
        },
        json_data={
            "invoiceHash": invoice_hash,
            "uuid": invoice_uuid ,
            "invoice": invoice_encoded,
        }
    )

    return response


# def generate_zatca_invoice_request(company , sales_invoice) -> None:
    
#     invoice = ZatcaInvoiceData(company , sales_invoice)
    
#     headers, body, data, endpoint = invoice.xml.fetch_request_data()

#     response = make_post_request(
#         company=company.get("name"),
#         endpoint=endpoint,
#         header=headers,
#         json_data=body
#     )
    
#     ResponseJson = response.json()
    
#     frappe.db.set_value("Sales Invoice" , sales_invoice.get("name") , "clearance_or_reporting" , 
#             ResponseJson.get("clearanceStatus") or ResponseJson.get("reportingStatus")
#     )

#     if response.status_code in [200 , 202]:  
#         frappe.db.set_value("Sales Invoice" , sales_invoice.get("name") , "custom_sent_to_zatca" , 1)
#         frappe.msgprint(
#             msg = _("Your Invoice Was Accepted in Zatca"), 
#             title=  _("Accepted"),
#             indicator="green" ,
#             alert=True
#         )
#         create_zatca_logs(
#             _method = "generate_zatca_invoice_request" ,
#             status = "Success"  if response.status_code == 200 else "Warning"  ,
#             message = response.text ,
#             reference_doctype = "Sales Invoice",
#             reference_name = sales_invoice.get("name"),
#             company = company.get("name"),
#             uuid = data.get("uuid"),
#             invoice = response.json().get("clearedInvoice") if response.json().get("clearedInvoice")  else data.get("invoice"),
#             hash = data.get("hash"),
#             qr_code = data.get("qrcode"),
#             pih = data.get("pih"),
#             icv = data.get("icv")
#         )

        
#         stored_values = json.loads(company.get("custom_stored_values"))
        
#         if company.check_pcsid:
#             stored_values[company.get("api_endpoints")]["production"]["icv"] = ( int(data.get("icv")) + 1 )
#             stored_values[company.get("api_endpoints")]["production"]["pih"] = data.get("hash")
#         else:
#             stored_values[company.get("api_endpoints")]["compliance"]["icv"] = ( int(data.get("icv")) + 1 )
#             stored_values[company.get("api_endpoints")]["compliance"]["pih"] = data.get("hash")
            
#         company.custom_stored_values = json.dumps(stored_values)
#         company.save(ignore_permissions = True)
        
#     else :
#         create_zatca_logs(
#             _method = "generate_zatca_invoice_request" ,
#             status = "Failed" ,
#             message = response.text ,
#             reference_doctype = "Sales Invoice",
#             reference_name = sales_invoice.get("name"),
#             company = company.get("name"),
#             uuid = data.get("uuid"),
#             invoice = data.get("invoice"),
#             hash = data.get("hash"),
#             qr_code = data.get("qr_code"),
#             pih = data.get("pih"),
#             icv = data.get("icv")
#         )
#         # sales_invoice.add_comment("Comment", _("{0}".format(response.text)))
        
#         frappe.throw(_("{0}".format(response.text)))

        
        
        
# @frappe.whitelist()
#def create_missing_qrcode(invoice_name , invoice_uuid , invoice ) -> None:
    import qrcode , io , base64 ,re
    from lxml import etree
    from frappe.utils import get_bench_relative_path
    
    # name_of_file = "{0}_uuid_{1}.xml".format(invoice_name , invoice_uuid)
    # tree = etree.parse(get_bench_relative_path(frappe.local.site) + "/public/files/invoices/{0}".format(name_of_file) )
    invoice = base64.b64decode(invoice).decode("utf-8")
    invoice = re.sub(r'<\?xml.*\?>', '', invoice)
    root = etree.fromstring(invoice)
    # print(tree)
    # root = tree.tag
    
    namespaces = {
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
    }
    qrcodevalue = ""   
    for doc_ref in root.findall('cac:AdditionalDocumentReference', namespaces):
        cbc_id = doc_ref.find('cbc:ID', namespaces).text
        if cbc_id == "QR":
            embedded_doc = doc_ref.find('cac:Attachment/cbc:EmbeddedDocumentBinaryObject', namespaces)
            if embedded_doc is not None:
                qrcodevalue = embedded_doc.text.strip()

    if not qrcodevalue :
        frappe.msgprint("No Qr code found in the invoice")
        
    img = qrcode.make(qrcodevalue)
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format="PNG")
    img_content = img_byte_array.getvalue()

    filename = f"{invoice_name}.png"

    existing_file = frappe.db.get_all(
        "File",
        filters={
            # "file_name": filename,
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": invoice_name,
        },
        fields=["name"],
    )

    # if there is a file attched to the image then delete it.
    if existing_file:
        for ex_file in existing_file:
            # File with the same name exists, delete it
            existing_file_doc = frappe.get_doc("File", ex_file.name)
            existing_file_doc.delete()

    # create a file with the image content
    _file = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": filename,
            "is_private": 0,
            "content": img_content,
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": invoice_name ,
            "attached_to_field": "ksa_einv2_qr",
        }
    )

    _file.save(ignore_permissions=True)
    
    sales_invoice = frappe.get_doc("Sales Invoice" , invoice_name)
    sales_invoice.db_set({"ksa_einv2_qr" : _file.file_url , "custom_sent_to_zatca" : 1})
    sales_invoice.notify_update()
    
    frappe.msgprint("Qr code created successfully" , alert=True , indicator= 'green')





@frappe.whitelist(allow_guest=True)
def add_company_info(*args , **kwargs) :
    
    # validate_missing_fields(*args , **kwargs)
    pass