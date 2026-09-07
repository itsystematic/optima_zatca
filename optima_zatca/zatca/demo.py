import uuid
import time
import json
import frappe 
from frappe import _ , _dict
from frappe import get_app_path
from optima_zatca.zatca.classes.xml import ZatcaXml
from optima_zatca.zatca.logs import make_action_log
from optima_zatca.zatca.api import make_invoice_request
from optima_zatca.zatca.xml_transport import encode_invoice_xml_for_api, serialize_invoice_xml

DEMO_INVOICE  = {
    "0" : "invoice_one" ,
    "1" : "invoice_two",
    "2" : "invoice_three",
    "3" : "invoice_four",
    "4" : "invoice_five",
    "5" : "invoice_six"
}

def send_sample_sales_invoices(settings ,company_details , on_document=None) :
    """Submit the six compliance documents ZATCA checks before issuing production.

    ``on_document`` is optional and, when given, is called as
    ``on_document(index, total, accepted)`` once per document — ``index`` being
    1-based. The onboarding board uses it to say which document is in flight
    rather than leaving a bar sitting at one value for the length of six calls.
    Existing callers that pass nothing are unaffected.
    """

    PIH = "gSNPKCpoXIlSvtP2p5JwDXLOaEWfkevQ2pbtnkosqjE="
        
    with open(get_app_path("optima_zatca") + "/zatca/Samples/Invoices/sales_invoices.json" , "r" ) as file : 
        sales_invoices = json.load(file)
        
    company_info = get_company_info(settings)
    invoice_info = get_public_info(settings)

    percentage = 20
    for idx , sales_invoice  in enumerate(sales_invoices.get("Invoices")) :
        try :
            if settings.get(DEMO_INVOICE.get("{0}".format(idx))) == 1:
                company_details[DEMO_INVOICE.get(f"{idx}")] = True
                _report(on_document, idx, len(sales_invoices.get("Invoices")), True)
                continue


            sales_invoice['PIH'] = PIH
            sales_invoice.update(company_info)
            sales_invoice.update(invoice_info)
            
            zatca_xml = ZatcaXml(sales_invoice)

            invoice_encoded = encode_invoice_xml_for_api(zatca_xml)

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
                percentage += 10
                frappe.publish_realtime("zatca" , { 
                    "message" : _("Invoice {0}  Type {1} Was Accepted in Zatca").format(sales_invoice.get("InvoiceStatus") ,sales_invoice.get("InvoiceSubStatus")),
                    "indicator" : "green" , "percentage" : percentage,
                    "commercial_register_name": settings.get('commercial_register')
                })
                # frappe.msgprint(alert=True , indicator="green" , msg= _("Invoice {0}  Type {1} Was Accepted in Zatca").format(sales_invoice.get("InvoiceStatus") ,sales_invoice.get("InvoiceSubStatus")))
                PIH = zatca_xml.hash

                company_details[DEMO_INVOICE.get(f"{idx}")] = True
                _report(on_document, idx, len(sales_invoices.get("Invoices")), True)

            else :
                frappe.publish_realtime("zatca" , {
                    "message" : _("Invoice {0}  Type {1} Was Rejected in Zatca").format(sales_invoice.get("InvoiceStatus") ,sales_invoice.get("InvoiceSubStatus")),
                    "indicator" : "red" ,
                    "percentage" : percentage,
                    "commercial_register_name": settings.get('commercial_register')
                })
                # frappe.msgprint(alert=True , indicator="red" , msg=_("Invoice {0}  Type {1} Was Rejected in Zatca").format(sales_invoice.get("InvoiceStatus") ,sales_invoice.get("InvoiceSubStatus")))
                
                Status = "Failed"
                _report(on_document, idx, len(sales_invoices.get("Invoices")), False)
                
            make_action_log(
                method ="send_to_zatca" ,
                status = Status  ,
                message = response.text ,
                reference_doctype = "Sales Invoice",
                company = settings.company ,
                commercial_register =  company_info.get("company").get("ID") ,
                uuid = sales_invoice.get("UUID"),
                invoice = invoice_encoded,
                hash = zatca_xml.hash ,
                api_endpoint = "complainace_checks" ,
                environment = settings.get("api_endpoints"),
                pih = zatca_xml.hash,
                icv = sales_invoice.get("InvoiceCounter"),
                xml_content = serialize_invoice_xml(zatca_xml) ,
            )

            time.sleep(5)

        except Exception as e:
            frappe.publish_realtime("zatca" , {
                "message" : _("Invoice {0}  Type {1} Was Rejected in Zatca").format(sales_invoice.get("InvoiceStatus") ,sales_invoice.get("InvoiceSubStatus")), "indicator" : "red"
            })
    
    # time.sleep(5)




def _report(on_document, idx, total, accepted):
    """Tell the caller a document settled, without letting that break the run.

    A progress callback is a convenience for whoever is watching; a failure in
    one must not abandon a certificate chain that is otherwise progressing.
    """
    if not on_document:
        return
    try:
        on_document(idx + 1, total, accepted)
    except Exception:
        frappe.log_error(title="ZATCA compliance progress callback", message=frappe.get_traceback())


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
