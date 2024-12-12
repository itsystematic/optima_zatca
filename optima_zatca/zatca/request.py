
import requests
import frappe
from frappe import _


BASEURL = {
    "sandbox" : {
        "compliance": "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/compliance",
        "complainace_checks": "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/compliance/invoices",
        "onboarding": "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/production/csids",
        "clearance": "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/invoices/clearance/single",
        "reporting": "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/invoices/reporting/single",
    },
    "simulation" : {
        "compliance": "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/compliance",
        "complainace_checks": "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/compliance/invoices",
        "onboarding": "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/production/csids",
        "clearance": "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/invoices/clearance/single",
        "reporting": "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/invoices/reporting/single",
    } ,
    "production" : {
        "compliance": "https://gw-fatoora.zatca.gov.sa/e-invoicing/core/compliance",
        "complainace_checks": "https://gw-fatoora.zatca.gov.sa/e-invoicing/core/compliance/invoices",
        "onboarding": "https://gw-fatoora.zatca.gov.sa/e-invoicing/core/production/csids",
        "clearance": "https://gw-fatoora.zatca.gov.sa/e-invoicing/core/invoices/clearance/single",
        "reporting": "https://gw-fatoora.zatca.gov.sa/e-invoicing/core/invoices/reporting/single",
    }
}



def get_base_url(setting:str=None , endpoint:str=None) -> str :
    
    if not setting :
        frappe.throw(_("Please Select Company"))
        
    environment = frappe.db.get_value("Optima Zatca Setting" , setting , "api_endpoints")
    
    return BASEURL.get(environment).get(endpoint)


def make_post_request(setting,endpoint , header , json_data):
    
    url = get_base_url(setting , endpoint)
    
    try : 
        response = requests.post(url , headers=header , json=json_data)
        return response
        
    except :
        frappe.throw(_("Zatca Is Not Responding Please Try Again Later"))


def make_get_request(setting , endpoint , header ,json_data) :
    
    url = get_base_url(setting , endpoint)
    
    return requests.get(url , headers=header , json=json_data)
    
    