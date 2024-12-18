import uuid
import time
import json
import base64
import frappe 
from frappe import _ , _dict
from lxml import etree
from frappe import get_app_path
from optima_zatca.zatca.classes.xml import ZatcaXml
from optima_zatca.zatca.logs import make_action_log
from optima_zatca.zatca.api import make_invoice_request

DEMO_INVOICE  = {
    "0" : "invoice_one" ,
    "1" : "invoice_two",
    "2" : "invoice_three",
    "3" : "invoice_four",
    "4" : "invoice_five",
    "5" : "invoice_six"
}

def send_sample_sales_invoices(settings ,company_details) :

    PIH = "gSNPKCpoXIlSvtP2p5JwDXLOaEWfkevQ2pbtnkosqjE="
        
    with open(get_app_path("optima_zatca") + "/zatca/Samples/Invoices/sales_invoices.json" , "r" ) as file : 
        sales_invoices = json.load(file)
        
    company_info = get_company_info(settings)
    invoice_info = get_public_info(settings)

    # try :
    for idx , sales_invoice  in enumerate(sales_invoices.get("Invoices")) :

        if settings.get(DEMO_INVOICE.get("{0}".format(idx))) == 1:
            company_details[DEMO_INVOICE.get(f"{idx}")] = True
            continue

        sales_invoice['PIH'] = PIH
        sales_invoice.update(company_info)
        sales_invoice.update(invoice_info)
        
        zatca_xml = ZatcaXml(sales_invoice)

        invoice_encoded = base64.b64encode(etree.tostring(zatca_xml.root)).decode()

        response = make_invoice_request(
            sales_invoice.get("Clearance-Status") , 
            settings.get("authorization") , 
            zatca_xml.hash , 
            sales_invoice.get("UUID") , 
            invoice_encoded , 
            settings, 
            "complainace_checks"
        )
        
        if response.status_code in [200 , 202]:
            
            Status = "Success"  if response.status_code == 200 else "Warning" 
            frappe.publish_realtime("zatca" , { 
                "message" : _("Invoice {0}  Type {1} Was Accepted in Zatca").format(sales_invoice.get("InvoiceStatus") ,sales_invoice.get("InvoiceSubStatus")), "indicator" : "green"
            })
            # frappe.msgprint(alert=True , indicator="green" , msg= _("Invoice {0}  Type {1} Was Accepted in Zatca").format(sales_invoice.get("InvoiceStatus") ,sales_invoice.get("InvoiceSubStatus")))
            PIH = zatca_xml.hash

            company_details[DEMO_INVOICE.get(f"{idx}")] = True
            
        else :
            frappe.publish_realtime("zatca" , {
                "message" : _("Invoice {0}  Type {1} Was Rejected in Zatca").format(sales_invoice.get("InvoiceStatus") ,sales_invoice.get("InvoiceSubStatus")), "indicator" : "red"
            })
            # frappe.msgprint(alert=True , indicator="red" , msg=_("Invoice {0}  Type {1} Was Rejected in Zatca").format(sales_invoice.get("InvoiceStatus") ,sales_invoice.get("InvoiceSubStatus")))
            
            Status = "Failed" 
            
        make_action_log(
            method ="send_to_zatca" ,
            status = Status  ,
            message = response.text ,
            reference_doctype = "Sales Invoice",
            company = settings.company ,
            commercial_register = sales_invoice.get("commercial_register") ,
            uuid = sales_invoice.get("UUID"),
            invoice = invoice_encoded,
            hash = zatca_xml.hash ,
            api_endpoint = "complainace_checks" ,
            environment = settings.get("api_endpoints"),
            pih = zatca_xml.hash,
            icv = sales_invoice.get("InvoiceCounter")
        )

    # except Exception as e:
    #     frappe.msgprint(str(e))
    
    # time.sleep(5)




def get_company_info(company_settings) :

    address = frappe.db.get_value("Commercial Register" , company_settings.get("commercial_register") , "address")
    company_address = frappe.get_doc("Address" , address )
        
    return {
        "company" : _dict({
            "ID" : company_settings.get("commercial_register") , 
            "schemeID" : company_settings.get("registration_type") ,
            "CompanyID" : company_settings.get("organization_identifier"),
            "RegistrationName" : company_settings.get("organization_name").strip(),
            "IdentificationCode" : "SA" , # Saudia Arabia 
            "CitySubdivisionName" : company_address.get("district") ,
            "BuildingNumber" : company_address.get("building_no"),
            "StreetName" : company_address.get("address_line1"),
            "PostalZone" : company_address.get("pincode"),
            "CityName" : company_address.get("city"),
            "CountrySubentity" : company_address.get("state") ,
            "TaxSchemeID" : "VAT" ,
            "DefaultCurrency" : "SAR",
        })
    }


def get_public_info(settings) :

    return {
        "X509SerialNumber" : str(settings.get("serial_number509")) ,
        "X509IssuerName" : settings.get("issuer_name") ,
        "DigestValue" : settings.get("certificate_hash") ,
        "Certificate" : settings.get("certificate") ,
        'SignatureInformation' : settings.get("signature"),
        "private_key" : settings.get("private_key") ,
        "public_key" : settings.get("public_key").strip() ,
        "UUID" : str(uuid.uuid4()) ,
    }