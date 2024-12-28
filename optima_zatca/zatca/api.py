import json 
import base64
import frappe
from frappe import _
from optima_zatca.zatca.classes.validate import validate_register_data
from optima_zatca.zatca.request import make_post_request , make_get_request , make_patch_request


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
def get_production_csid(setting , binary_security_token , secret , request_id) -> dict:
    auth = base64.b64encode("{0}:{1}".format(binary_security_token,secret).encode()).decode("utf-8")
    
    response = make_post_request(
        setting= setting ,
        endpoint= "onboarding" ,
        header = {
            "accept": "application/json",
            "Accept-Language": "en",
            "Accept-Version": "V2",
            "Authorization": "Basic " + auth,
            "Content-Type": "application/json",
        },
        json_data={
            "compliance_request_id" : request_id
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


def renew_production_csid(setting ,otp , authorization , csr):
    
    response = make_patch_request(
        setting= setting ,
        endpoint= "onboarding" ,
        header = {
            "OTP": otp,
            "Accept-Language": "en",
            "Accept-Version": "V2",
            "Authorization": "Basic " + authorization,
            "Content-Type": "application/json",
        },
        json_data={
            "csr" : csr
        }
    )

    if response.status_code != 200 :
        frappe.throw(str(response.text))
    
    return response.json()




@frappe.whitelist()
def register_company(**kwargs) :
    from optima_zatca.zatca.setup import saving_register_data
    
    validate_register_data(**kwargs)
    saving_register_data(**kwargs)

    frappe.response["message"] = _("Company Data Successfuly Saved")


@frappe.whitelist()
def get_companies_registered() :
    from optima_zatca.zatca.setup import get_registered_companies

    list_of_companies = get_registered_companies()
    return list_of_companies