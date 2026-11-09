"""Register a company's commercial registers with ZATCA and get each one its certificates.

    register_company (zatca/api.py)       the onboarding wizard's one call
      └─ saving_register_data             the company, the phase, then for each register:
           ├─ Address · Commercial Register · Optima Zatca Setting    created or updated
           └─ add_company_to_zatca        CSR + keys → compliance CSID → sample invoices
                                          → production CSID

    renew_production_certificate          a new production CSID, from the setting's form

Progress goes out on the "zatca" realtime event, which the wizard's progress board follows.
"""

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
# REGISTRATION FROM THE ONBOARDING WIZARD
# One Address, Commercial Register and Optima Zatca Setting per register, keyed on its CRN. A retry
# sends the same register again, so it is matched to what is already stored and updated or resumed,
# never added a second time.


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
    """Save or resume each register in turn, then onboard it."""
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
            optima_settings = saving_zatca_setting(company ,tax_id, legal_name , commercial_register , company_address , stored.get("setting") , **branch)

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


def saving_zatca_setting(company ,tax_id, legal_name ,commercial_register ,company_address , setting=None , **kwargs) :
    """Create or update the register's Optima Zatca Setting; returns its name."""
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
        "invoice_type" : "1100" ,  # issues both standard (B2B) and simplified (B2C) invoices
    }
    if not setting :
        # otp is mandatory on the doctype, so a register saved without one gets a placeholder.
        values["otp"] = "123456"
        # The wizard has no environment choice yet; a test site sets this to sandbox or simulation.
        values["api_endpoints"] = frappe.conf.get("zatca_onboarding_environment") or "production"
    if kwargs.get("otp") :
        values["otp"] = kwargs.get("otp")

    return _upsert("Optima Zatca Setting" , setting , values)


def _upsert(doctype, name, values, ignore_mandatory=False):
    """Update the record called `name` with `values`, or create it when there is no such record."""
    doc = frappe.get_doc(doctype, name) if name and frappe.db.exists(doctype, name) else frappe.new_doc(doctype)
    doc.update(values)
    doc.flags.ignore_mandatory = ignore_mandatory
    doc.save(ignore_permissions=True)
    return doc.name


def saving_main_settings(**kwargs) :
    frappe.db.set_single_value("Zatca Main Settings" , "phase" , kwargs.get("phase") , update_modified=True)


def get_registered_companies() :
    """Every register that has an Optima Zatca Setting, in the shape the wizard lists and prefills.

    `phase` is the one global phase from Zatca Main Settings, repeated on every row.
    """
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
# DEVICE ONBOARDING AND RENEWAL
# CSR + keys, compliance CSID, sample invoices, production CSID — in that order. Every stage after the
# first is gated by its own check_* flag on the setting, which is what makes a re-run resume rather
# than start over. Each CSID arrives as a base64 binary security token: decoded, it is the certificate;
# paired with the secret, it is the Basic auth header for later calls.


@frappe.whitelist()
def add_company_to_zatca(name):
    """Onboard one Optima Zatca Setting, resuming from the last stage it reached.

    Called for each register by saving_branches_data, and by the setting form's Setup Zatca button.
    A failure is published on the "zatca" event and logged rather than raised, so the next register
    in the same request still runs.
    """
    try:
        settings = frappe.get_doc("Optima Zatca Setting", name)

        # Keys only before the compliance CSID exists: its certificate is bound to the key it was
        # requested with, so a retry must keep the stored key.
        setting_updates = {}
        if not settings.check_csid:
            csr_generator = GenerateCSR(settings, frappe.local.site, **get_csr_identity(settings))
            setting_updates = csr_generator.get_generated_details()

        if settings.otp and not settings.check_csid:
            get_compliance_certificate(settings, setting_updates["csr"], setting_updates)
            saving_data_to_setting(name, setting_updates)
            settings.reload()  # picks up check_csid, so the sample invoices run in this same pass

        if settings.check_csid:
            send_sample_sales_invoices(settings, setting_updates)

        if not settings.check_pcsid and all_sample_invoices_passed(setting_updates):
            get_production_certificate(settings, setting_updates)

        saving_data_to_setting(name, setting_updates)
        notify_completion_status(settings, setting_updates)

    except Exception as e:
        notify_failure_status(settings, e)
        frappe.log_error(f"ZATCA Setup Failed for {name}", str(e))


def all_sample_invoices_passed(setting_updates):
    # The flags are named for the spelt-out ordinal, not the digit.
    invoice_fields = [
        "invoice_one", "invoice_two", "invoice_three",
        "invoice_four", "invoice_five", "invoice_six"
    ]
    return all(setting_updates.get(field) for field in invoice_fields)


def get_compliance_certificate(settings: frappe._dict, company_csr: str, setting_updates: dict) -> None:
    """Request the compliance CSID with the setting's OTP, and add it to `setting_updates`."""
    try:
        response = get_zatca_csid(
            settings.name,
            settings.otp,
            company_csr
        )
        request_id, binary_token, secret = response

        certificate = _decode_certificate(binary_token)
        auth_header = make_auth_header_for_request(binary_token, secret)

        setting_updates.update({
            "binary_security_token": binary_token,
            "request_id": request_id,
            "secret": secret,
            "certificate": certificate,
            "authorization": auth_header,
            "check_csid": 1
        })

        extract_details_from_certificate(certificate, setting_updates)

        _publish_status(settings, "CSID Created Successfully", "green", 20)

    except Exception as e:
        _handle_cert_error(settings, e, "CSID creation")
        raise


def get_production_certificate(settings: frappe._dict, setting_updates: dict) -> None:
    """Exchange the compliance CSID for the production one, and add it to `setting_updates`."""
    try:
        response = get_production_csid(
            settings.name,
            settings.binary_security_token,
            settings.secret,
            settings.request_id
        )

        binary_token = response.get("binarySecurityToken")

        certificate = _decode_certificate(binary_token)

        auth_header = make_auth_header_for_request(binary_token, response.get("secret"))

        setting_updates.update({
            "binary_security_token": binary_token,
            "production_request_id": response.get("requestID"),
            "secret": response.get("secret"),
            "certificate": certificate,
            "token_type": response.get("tokenType"),
            "authorization": auth_header,
            "check_pcsid": 1
        })

        extract_details_from_certificate(certificate, setting_updates)

        _publish_status(settings, "Production CSID Created Successfully", "green", 95)

    except Exception as e:
        _handle_cert_error(settings, e, "production CSID creation")
        raise


def _decode_certificate(b64_string: str) -> str:
    try:
        return base64.b64decode(b64_string).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as e:
        frappe.throw(_("Invalid certificate format: {0}").format(str(e)))


@frappe.whitelist()
def renew_production_certificate(setting ,otp , authorization , csr):
    """Replace an onboarded setting's production CSID, from the setting form's Renew button.

    Needs a fresh OTP, but skips CSR generation and the sample invoices: the form sends the
    setting's stored authorization and CSR.
    """
    response = renew_production_csid(setting ,otp , authorization , csr)
    certificate = base64.b64decode(response.get("binarySecurityToken")).decode("utf-8")
    authorization = make_auth_header_for_request(response.get("binarySecurityToken"), response.get("secret"))

    setting_updates = {
        "binary_security_token" : response.get("binarySecurityToken")  ,
        "production_request_id" : response.get("requestID") ,
        "secret" : response.get("secret"),
        "certificate" : certificate,
        "token_type" : response.get("tokenType"),
        "authorization" : authorization ,
    }
    extract_details_from_certificate(certificate , setting_updates)
    saving_data_to_setting(setting , setting_updates)
    frappe.publish_realtime("zatca" , {"message" :"Production CSID Renew Successfully", "indicator" : "green"})


# ====================================================================================================
# SAVING AND PROGRESS EVENTS
# Every event is {message, indicator, percentage, complete, commercial_register_name} on "zatca". The
# wizard's board files each one under its commercial_register_name and ignores an event without it,
# such as the one saving_data_to_setting sends.


def saving_data_to_setting(name: str, values) -> None:
    """Write `values` onto the Optima Zatca Setting and commit straight away, so a certificate ZATCA
    has issued stays saved even if something later in the request fails."""
    frappe.db.set_value("Optima Zatca Setting" , name , values , update_modified=True )
    frappe.db.commit()

    frappe.publish_realtime("zatca" , {"message" :"Data Saved Successfully", "indicator" : "green" })


def _publish_status(settings: frappe._dict, message: str, indicator: str, percentage: int) -> None:
    frappe.publish_realtime("zatca", {
        "message": message,
        "commercial_register_name": settings.commercial_register,
        "indicator": indicator,
        "percentage": percentage,
        "complete": percentage == 100
    })


def notify_completion_status(settings, setting_updates):
    """The run's last event: 100% when the production CSID was issued, otherwise 50%."""
    status = {
        "message": "ZATCA Setup Completed" if setting_updates.get("check_pcsid") else "ZATCA Setup Partially Completed",
        "commercial_register_name": settings.commercial_register,
        "indicator": "green" if setting_updates.get("check_pcsid") else "red",
        "complete": True,
        "percentage": 100 if setting_updates.get("check_pcsid") else 50
    }
    frappe.publish_realtime("zatca", status)


def notify_failure_status(settings, error):
    error_status = {
        "message": f"ZATCA Setup Failed: {str(error)}",
        "commercial_register_name": settings.commercial_register,
        "indicator": "red",
        "complete": True,
        "percentage": 0
    }
    frappe.publish_realtime("zatca", error_status)


def _handle_cert_error(settings: frappe._dict, error: Exception, stage: str) -> None:
    """Log a refused certificate request and publish it at 0%; the caller re-raises."""
    error_msg = _("Failed during {0}: {1}").format(stage, str(error))
    frappe.log_error(title="ZATCA Certificate Error", message=error_msg)
    _publish_status(settings, error_msg, "red", 0)
