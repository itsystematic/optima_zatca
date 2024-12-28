import frappe
import json
import base64
# from optima_zatca.zatca.validate import validate_company_address
from optima_zatca.zatca.api import get_zatca_csid , get_production_csid , renew_production_csid
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

    #if settings.get("check_pcsid") == 0 and all(list_of_fields) :
        #get_production_certificate(settings , company_details ) 


    saving_data_to_company(name , company_details)

    if settings.get("check_pcsid") == 1 or company_details.get("check_pcsid") == 1 :
        frappe.publish_realtime("zatca" , {"message" :"Zatca Setup Completed", "indicator" : "green" ,  "complete" : True  , "percentage" : 100})
    else :
        frappe.publish_realtime("zatca" , {"message" :"Zatca Setup Failed", "indicator" : "red" ,  "complete" : True , "percentage" : 50})


def get_certificate(settings ,company_csr , company_details:dict) :

    request_id , binary_security_token , secret  = get_zatca_csid(settings.name , settings.otp , company_csr )
    certificate = base64.b64decode(binary_security_token).decode("utf-8")
    authorization = make_auth_header_for_request(binary_security_token, secret )

    company_details.update({
        "binary_security_token" : binary_security_token ,
        "request_id" : request_id ,
        "secret" : secret,
        "certificate" : certificate,
        "authorization" : authorization ,
        "check_csid" : 1,
    })

    extract_details_from_certificate(certificate , company_details)
    frappe.publish_realtime("zatca" , {"message" :"CSID Created Successfully", "indicator" : "green" , "percentage" : 20})


def get_production_certificate(settings , company_details:dict ) :
    response = get_production_csid(
        settings,
        settings.get("binary_security_token") ,
        settings.get("secret") ,
        settings.get("request_id")
    )
    
    certificate = base64.b64decode(response.get("binarySecurityToken")).decode("utf-8")
    authorization = make_auth_header_for_request(response.get("binarySecurityToken"), response.get("secret"))
        
    company_details.update({
        "binary_security_token" : response.get("binarySecurityToken")  ,
        "production_request_id" : response.get("requestID") ,
        "secret" : response.get("secret"),
        "certificate" : certificate,
        "token_type" : response.get("tokenType"),
        "authorization" : authorization,
        "check_pcsid" : 1 ,
    })

    extract_details_from_certificate(certificate , company_details)
    frappe.publish_realtime("zatca" , {"message" :"Production CSID Created Successfully", "indicator" : "green" , "percentage" : 95})
    


@frappe.whitelist()
def renew_production_certificate(setting ,otp , authorization , csr):

    response = renew_production_csid(setting ,otp , authorization , csr)
    certificate = base64.b64decode(response.get("binarySecurityToken")).decode("utf-8")
    authorization = make_auth_header_for_request(response.get("binarySecurityToken"), response.get("secret"))

    company_details = {
        "binary_security_token" : response.get("binarySecurityToken")  ,
        "production_request_id" : response.get("requestID") ,
        "secret" : response.get("secret"),
        "certificate" : certificate,
        "token_type" : response.get("tokenType"),
        "authorization" : authorization ,
    }
    extract_details_from_certificate(certificate , company_details)
    saving_data_to_company(setting , company_details)
    frappe.publish_realtime("zatca" , {"message" :"Production CSID Renew Successfully", "indicator" : "green"})



def saving_data_to_company( 
    name:str ,
    company_details
) -> None :
    
    frappe.db.set_value("Optima Zatca Setting" , name , company_details , update_modified=True )
    frappe.db.commit()
    
    frappe.publish_realtime("zatca" , {"message" :"Data Saved Successfully", "indicator" : "green" })



# Calling From Zatca Page

def saving_register_data(**kwargs) :

    saving_company_data(**kwargs)
    saving_branches_data(**kwargs)
    saving_main_settings(**kwargs)



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
        optima_settings = saving_optima_payment_setting(company ,tax_id, legal_name , commercial_register , company_address , **branch)
        add_company_to_zatca(optima_settings)




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
    
    settings = frappe.get_doc({
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
        "api_endpoints" : kwargs.get("api_endpoints")
    }).insert(ignore_if_duplicate=True , ignore_permissions=True)

    return settings.name


def saving_main_settings(**kwargs) :
    frappe.db.set_single_value("Zatca Main Settings" , "phase" , kwargs.get("phase") , update_modified=True)

def get_registered_companies() :

    phase = frappe.db.get_single_value("Zatca Main Settings" , "phase")

    return frappe.db.sql(""" 
        SELECT   
            ozs.company , 
            ozs.organization_name as company_name_in_arabic, 
            ozs.organization_identifier as tax_id,
            cr.commercial_register as commercial_register_number ,
            cr.commercial_register_name ,
            ad.short_address ,
            ad.building_no,
            ad.address_line1,
            ad.address_line2,
            ad.city,
            ad.pincode, 
            ad.district ,
            ozs.otp,
            IF(1=0 , "Not Registered" , %(phase)s ) as phase
        FROM `tabOptima Zatca Setting` ozs
        LEFT JOIN `tabCommercial Register` cr 
            ON cr.name = ozs.commercial_register
        LEFT JOIN `tabAddress` ad
            ON ad.name = cr.address
        
    """,{"phase" : phase},as_dict=True)
