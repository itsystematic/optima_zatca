import binascii
import frappe
from frappe import _
import json
import base64
from optima_zatca.zatca.api import get_zatca_csid , get_production_csid , renew_production_csid
from optima_zatca.zatca.utils import ( 
    extract_details_from_certificate ,
    make_auth_header_for_request ,
    get_csr_identity
)

from optima_zatca.zatca.demo import send_sample_sales_invoices
from optima_zatca.zatca.keys import GenerateCSR


# ====================================================================================================
# DEVICE ONBOARDING
# CSR + keys, compliance CSID, sample invoices, production CSID — in that order. Every stage after
# the first is gated by its own check_* flag on the setting, which is what makes a re-run resume
# rather than start over.


@frappe.whitelist()
def add_company_to_zatca(name):
    try:
        settings = frappe.get_doc("Optima Zatca Setting", name)

        # 1. Generate CSR and Keys, only before the compliance CSID exists: its certificate is
        # bound to the key it was requested with, so a retry must keep the stored key.
        company_details = {}
        if not settings.check_csid:
            csr_generator = GenerateCSR(settings, frappe.local.site, **get_csr_identity(settings))
            company_details = csr_generator.get_generated_details()

        # 2. Handle Certificate Generation
        if settings.otp and not settings.check_csid:
            get_certificate(settings, company_details["csr"], company_details)
            saving_data_to_company(name, company_details)
            settings.reload()

        # 3. Send Sample Invoices if required
        if settings.check_csid:
            send_sample_sales_invoices(settings, company_details)

        # 4. Handle Production Certificate
        if not settings.check_pcsid and all_invoice_fields_present(company_details):
            get_production_certificate(settings, company_details)

        # 5. Final Save and Notification
        saving_data_to_company(name, company_details)
        notify_completion_status(settings, company_details)

    except Exception as e:
        handle_zatca_error(settings, e)
        frappe.log_error(f"ZATCA Setup Failed for {name}", str(e))


def all_invoice_fields_present(company_details):
    # The flags are named for the spelt-out ordinal, not the digit.
    invoice_fields = [
        "invoice_one", "invoice_two", "invoice_three",
        "invoice_four", "invoice_five", "invoice_six"
    ]
    return all(company_details.get(field) for field in invoice_fields)


def get_certificate(settings: frappe._dict, company_csr: str, company_details: dict) -> None:
    """Handles initial certificate generation from ZATCA CSID"""
    try:
        response = get_zatca_csid(
            settings.name,
            settings.otp,
            company_csr
        )
        request_id, binary_token, secret = response

        certificate = _decode_certificate(binary_token)
        auth_header = _create_auth_header(binary_token, secret)

        company_details.update({
            "binary_security_token": binary_token,
            "request_id": request_id,
            "secret": secret,
            "certificate": certificate,
            "authorization": auth_header,
            "check_csid": 1
        })

        extract_details_from_certificate(certificate, company_details)

        _publish_status(settings, "CSID Created Successfully", "green", 20)

    except Exception as e:
        _handle_cert_error(settings, e, "CSID creation")
        raise


def get_production_certificate(settings: frappe._dict, company_details: dict) -> None:
    """Handles production certificate generation from ZATCA"""
    try:
        response = get_production_csid(
            settings.name,
            settings.binary_security_token,
            settings.secret,
            settings.request_id
        )

        binary_token = response.get("binarySecurityToken")

        certificate = _decode_certificate(binary_token)

        auth_header = _create_auth_header(binary_token, response.get("secret"))

        company_details.update({
            "binary_security_token": binary_token,
            "production_request_id": response.get("requestID"),
            "secret": response.get("secret"),
            "certificate": certificate,
            "token_type": response.get("tokenType"),
            "authorization": auth_header,
            "check_pcsid": 1
        })

        extract_details_from_certificate(certificate, company_details)

        _publish_status(settings, "Production CSID Created Successfully", "green", 95)

    except Exception as e:
        _handle_cert_error(settings, e, "production CSID creation")
        raise


# ====================================================================================================
# CERTIFICATE RENEWAL
# Re-issues the production CSID for a device that is already onboarded. Needs a fresh OTP, but skips
# CSR generation and the sample invoices.


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


# ====================================================================================================
# REGISTRATION FROM THE ONBOARDING WIZARD
# Entered from the onboarding wizard through zatca/api.py. saving_register_data provisions a company's
# whole device fleet — one Address, Commercial Register and Optima Zatca Setting per branch — and
# onboards each one as it goes. A retry sends the same branch again, so each branch is matched to
# what is stored for its CRN and updated or resumed, never added a second time.
# get_registered_companies reads the fleet back to prefill the wizard.


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
        crn = branch.get("commercial_register_number")
        stored = _load_stored_register(crn)
        action = _decide_register_action(stored, company)

        if action == "other_company":
            frappe.throw(_("Commercial register {0} belongs to another company").format(crn))
        if action == "connected":
            frappe.throw(_("Commercial register {0} is already connected to ZATCA").format(crn))

        if action == "resume":
            optima_settings = stored["setting"]
        else:
            stored = stored or {}
            company_address = saving_address_data(company , stored.get("address") , **branch)
            commercial_register = saving_commercial_register(company , company_address , **branch)
            optima_settings = saving_optima_payment_setting(company ,tax_id, legal_name , commercial_register , company_address , stored.get("setting") , **branch)

        add_company_to_zatca(optima_settings)


def _load_stored_register(crn):
    """What is already saved for this CRN, as plain values, or None for a new register."""
    register = frappe.db.get_value("Commercial Register", crn, ["company", "address"], as_dict=True)
    if not register:
        return None

    setting = frappe.db.get_value(
        "Optima Zatca Setting", {"commercial_register": crn}, ["name", "check_csid", "check_pcsid"], as_dict=True
    ) or {}
    return {
        "company": register.company,
        "address": register.address,
        "setting": setting.get("name"),
        "check_csid": setting.get("check_csid"),
        "check_pcsid": setting.get("check_pcsid"),
    }


def _decide_register_action(stored, company) -> str:
    """What to do with one branch: "save", "resume", or the refusal "other_company" / "connected".

    The register's identity, address included, goes into the CSR, so its records may be edited only
    until the compliance CSID is issued. From then on a retry resumes with them as they are.
    """
    if not stored:
        return "save"
    if stored["company"] != company:
        return "other_company"
    if stored["check_pcsid"]:
        return "connected"
    if stored["check_csid"]:
        return "resume"
    return "save"


def _upsert(doctype, name, values, ignore_mandatory=False):
    """Update the record called `name` with `values`, or create it when there is no such record."""
    doc = frappe.get_doc(doctype, name) if name and frappe.db.exists(doctype, name) else frappe.new_doc(doctype)
    doc.update(values)
    doc.flags.ignore_mandatory = ignore_mandatory
    doc.save(ignore_permissions=True)
    return doc.name


def saving_address_data(company , address=None , **kwargs) :

    return _upsert("Address" , address , {
        "address_title" : company + " " + kwargs.get("commercial_register_name") ,
        "address_type" : "Billing" ,
        "short_address" : kwargs.get("short_address"),
        "building_no" :kwargs.get("building_no"),
        "address_line1" : kwargs.get("address_line1"),
        "address_line2": kwargs.get("address_line2") ,
        "city" : kwargs.get("city"),
        "pincode" : kwargs.get("pincode"),
        "district" : kwargs.get("district") ,
    } , ignore_mandatory=True)


def saving_commercial_register(company , address , **kwargs) :

    return _upsert("Commercial Register" , kwargs.get("commercial_register_number") , {
        "company" : company ,
        "commercial_register_name" : kwargs.get("commercial_register_name") ,
        "commercial_register" : kwargs.get("commercial_register_number"),
        "address" : address
    })


def saving_optima_payment_setting(company ,tax_id, legal_name ,commercial_register ,company_address , setting=None , **kwargs) :

    values = {
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
    }
    if not setting :
        values["otp"] = "123456"
        # The wizard has no environment choice yet; a test site sets this to sandbox or simulation.
        values["api_endpoints"] = frappe.conf.get("zatca_onboarding_environment") or "production"
    if kwargs.get("otp") :
        values["otp"] = kwargs.get("otp")

    return _upsert("Optima Zatca Setting" , setting , values)


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


# ====================================================================================================
# PERSISTENCE AND PROGRESS REPORTING
# Every stage reports to the same "zatca" realtime event the onboarding SPA listens on; the
# percentage is what drives its progress bar.


def saving_data_to_company( 
    name:str ,
    company_details
) -> None :
    
    frappe.db.set_value("Optima Zatca Setting" , name , company_details , update_modified=True )
    frappe.db.commit()
    
    frappe.publish_realtime("zatca" , {"message" :"Data Saved Successfully", "indicator" : "green" })


def notify_completion_status(settings, company_details):
    status = {
        "message": "ZATCA Setup Completed" if company_details.get("check_pcsid") else "ZATCA Setup Partially Completed",
        "commercial_register_name": settings.commercial_register,
        "indicator": "green" if company_details.get("check_pcsid") else "red",
        "complete": True,
        "percentage": 100 if company_details.get("check_pcsid") else 50
    }
    frappe.publish_realtime("zatca", status)


def handle_zatca_error(settings, error):
    error_status = {
        "message": f"ZATCA Setup Failed: {str(error)}",
        "commercial_register_name": settings.commercial_register,
        "indicator": "red",
        "complete": True,
        "percentage": 0
    }
    frappe.publish_realtime("zatca", error_status)


def _publish_status(settings: frappe._dict, message: str, indicator: str, percentage: int) -> None:
    """Publish realtime status updates"""
    frappe.publish_realtime("zatca", {
        "message": message,
        "commercial_register_name": settings.commercial_register,
        "indicator": indicator,
        "percentage": percentage,
        "complete": percentage == 100
    })


def _handle_cert_error(settings: frappe._dict, error: Exception, stage: str) -> None:
    """Handle certificate generation errors"""
    error_msg = frappe._("Failed during {0}: {1}").format(stage, str(error))
    frappe.log_error(title="ZATCA Certificate Error", message=error_msg)
    _publish_status(settings, error_msg, "red", 0)


# ====================================================================================================
# CERTIFICATE PAYLOAD DECODING
# Both CSID responses arrive as a base64 binary security token: the certificate is its decoded body,
# and the same token pairs with the secret to form the Basic auth header for later calls.


def _decode_certificate(b64_string: str) -> str:
    """Decode base64 encoded certificate string"""
    try:
        return base64.b64decode(b64_string).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as e:
        frappe.throw(frappe._("Invalid certificate format: {0}").format(str(e)))


def _create_auth_header(token: str, secret: str) -> str:
    """Generate authorization header for ZATCA API"""
    return make_auth_header_for_request(token, secret)
