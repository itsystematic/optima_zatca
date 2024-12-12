import frappe
import json
import base64
# from optima_zatca.zatca.validate import validate_company_address
from optima_zatca.zatca.api import get_zatca_csid
from optima_zatca.zatca.utils import (
    create_company_csr , 
    extract_details_from_certificate ,
    make_auth_header_for_request 
)



def make_optima_zatca_setting() :

    # Create Commercial Register
    # commercial_register = 
    pass





@frappe.whitelist()
def add_company_to_zatca(name):

    company_details = {}
    settings = frappe.get_doc("Optima Zatca Setting" , name)
    company_csr = create_company_csr(settings , company_details)

    if settings.get("otp") and company_csr :
        get_certificate(settings ,company_csr , company_details)

    saving_data_to_company(name , company_details)


def get_certificate(settings ,company_csr , company_details:dict) :

    request_id , binary_security_token , secret  = get_zatca_csid(settings.name , settings.otp , company_csr )

    certificate = base64.b64decode(binary_security_token).decode("utf-8")
    
    company_details.update({
        "binary_security_token" : binary_security_token ,
        "request_id" : request_id ,
        "secret" : secret,
        "certificate" : certificate,
    })

    if certificate :
        make_auth_header_for_request(binary_security_token, secret , company_details)
        extract_details_from_certificate(certificate , company_details)


def saving_data_to_company( 
    name:str ,
    company_details
) -> None :
    
    frappe.db.set_value("Optima Zatca Setting" , name , company_details , update_modified=True )
    frappe.db.commit()
    
    frappe.msgprint("Daata Saved Successfully" , alert=True)

