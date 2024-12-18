import frappe
import json
import base64
# from optima_zatca.zatca.validate import validate_company_address
from optima_zatca.zatca.api import get_zatca_csid , get_production_csid
from optima_zatca.zatca.utils import (
    create_company_csr , 
    extract_details_from_certificate ,
    make_auth_header_for_request 
)

from optima_zatca.zatca.demo import send_sample_sales_invoices



@frappe.whitelist()
def add_company_to_zatca(name):

    company_details = {}

    settings = frappe.get_doc("Optima Zatca Setting" , name)

    company_csr = create_company_csr(settings , company_details)

    if settings.get("otp") and settings.get("check_csid") == 0 :

        get_certificate(settings ,company_csr , company_details)
        saving_data_to_company(name , company_details)
        settings = frappe.get_doc("Optima Zatca Setting" , name)


    if settings.get("check_csid") == 1 :
        send_sample_sales_invoices(settings ,company_details)

    list_of_fields = [
        company_details.get("invoice_one" , False),company_details.get("invoice_two" , False), 
        company_details.get("invoice_three", False) , company_details.get("invoice_four" , False) , 
        company_details.get("invoice_five" , False) ,company_details.get("invoice_six" , False)
    ]

    if settings.get("check_pcsid") == 0 and all(list_of_fields) :
        get_production_certificate(settings , company_details ) 


    saving_data_to_company(name , company_details)


def get_certificate(settings ,company_csr , company_details:dict) :

    request_id , binary_security_token , secret  = get_zatca_csid(settings.name , settings.otp , company_csr )
    certificate = base64.b64decode(binary_security_token).decode("utf-8")

    company_details.update({
        "binary_security_token" : binary_security_token ,
        "request_id" : request_id ,
        "secret" : secret,
        "certificate" : certificate,
        "check_csid" : 1,
    })

    if certificate :
        make_auth_header_for_request(binary_security_token, secret , company_details)
        extract_details_from_certificate(certificate , company_details)


def get_production_certificate(settings , company_details:dict ) :
    response = get_production_csid(
        settings,
        company_details.get("binary_security_token") ,
        company_details.get("secret") ,
        company_details.get("request_id")
    )
    
    certificate = base64.b64decode(response.get("binarySecurityToken")).decode("utf-8")
        
    company_details.update({
        "binary_security_token" : response.get("binarySecurityToken")  ,
        "request_id" : response.get("requestID") ,
        "secret" : response.get("secret"),
        "certificate" : certificate,
        "token_type" : response.get("tokenType"),
        "check_pcsid" : 1 ,
    })

    if certificate :
        make_auth_header_for_request(response.get("binarySecurityToken"), response.get("secret") , company_details)
        extract_details_from_certificate(certificate , company_details)
    



def saving_data_to_company( 
    name:str ,
    company_details
) -> None :
    
    frappe.db.set_value("Optima Zatca Setting" , name , company_details , update_modified=True )
    frappe.db.commit()
    
    frappe.msgprint("Data Saved Successfully" , alert=True)





def saving_register_data(**kwargs) :

    saving_company_data(**kwargs)
    saving_branches_data(**kwargs)



def saving_company_data(**kwargs) :

    frappe.db.set_value("Company" , kwargs.get("company") , {
        "company_name_in_arabic" : kwargs.get("company_name_in_arabic") ,
        "tax_id" : kwargs.get("tax_id")
    } , update_modified=True )
    


def saving_branches_data(**kwargs) :
    company = kwargs.get("company")
    tax_id = kwargs.get("tax_id")
    legal_name = kwargs.get("company_name_in_arabic")
    
    list_of_branches = json.loads(kwargs.get("commercial_register")) if isinstance(kwargs.get("commercial_register") , str) else kwargs.get("commercial_register")

    for branch in list_of_branches:
        company_address = saving_address_data(company , **branch)
        commercial_register = saving_commercial_register(company , company_address , **branch)
        saving_optima_payment_setting(company ,tax_id, legal_name , commercial_register , company_address , **branch)


def saving_address_data(company , **kwargs) :

    address = frappe.get_doc({
        "doctype" : "Address" ,
        "address_title" : company + " " + kwargs.get("commercial_register_name") ,
        "address_type" : "Billing" ,
        "short_address" : kwargs.get("short_address"),
        "building_no" :kwargs.get("building_no"),
        "address_line1" : kwargs.get("address_line1"),
        "address_line2": kwargs.get("address_line2") ,
        "city" : kwargs.get("city"),
        "pincode" : kwargs.get("pincode"),
        "district" : kwargs.get("district") ,

    }).insert(ignore_permissions=True , ignore_mandatory=True)

    return address.name


def saving_commercial_register(company , address , **kwargs) :

    commercial_register = frappe.get_doc({
        "doctype" : "Commercial Register" ,
        "company" : company ,
        "commercial_register_name" : kwargs.get("commercial_register_name") ,
        "commercial_register" : kwargs.get("commercial_register_number"),
        "address" : address
    }).insert(ignore_if_duplicate=True , ignore_permissions=True)

    return commercial_register.name


def saving_optima_payment_setting(company ,tax_id, legal_name ,commercial_register ,company_address , **kwargs) :
    
    frappe.get_doc({
        "doctype" : "Optima Zatca Setting" ,
        "company" : company ,
        "commercial_register" : commercial_register ,
        "organization_identifier" : tax_id,
        "organization_unit_name" : kwargs.get("commercial_register_name") ,
        "location" : kwargs.get("short_address") ,
        "organization_name" : legal_name ,
        "registration_type" : "CRN",
        "country_name" : "SA",
        "industry" : "Commercial" ,
        "address" : company_address ,
        "invoice_type" : "1100" ,
        "otp" : kwargs.get("otp") or "12356",
        "api_endpoints" : "production"
    }).insert(ignore_if_duplicate=True , ignore_permissions=True)
