"""The calls this app makes to ZATCA, and the two methods the onboarding wizard calls."""

import base64
import frappe
from frappe import _
from optima_zatca.zatca.classes.validate import validate_register_data
from optima_zatca.zatca.request import make_post_request , make_patch_request


# ====================================================================================================
# CALLS TO ZATCA
# Each adds its endpoint's headers and body and sends them through zatca/request.py. The certificate
# (CSID) calls throw ZATCA's response text on anything but HTTP 200; make_invoice_request returns the
# response as it is, for the submission workflow to judge.


def get_zatca_csid(setting: str, otp: str, csr: str) -> tuple:
    """Request the compliance CSID for `csr`, authorised by the OTP from the Fatoora portal.

    Returns (request_id, binary_security_token, secret).
    """
    response = make_post_request(
        setting=setting,
        endpoint="compliance",
        header={
            "OTP": otp,
            "Accept-Version": "V2",
            "Content-Type": "application/json",
            "accept": "application/json",
        },
        json_data={
            "csr": csr,
        }
    )

    res = _ok_json(response)
    return res.get("requestID"), res.get("binarySecurityToken"), res.get("secret")


@frappe.whitelist()
def get_production_csid(setting: str, binary_security_token: str, secret: str, request_id: str | int) -> dict:
    """Exchange the compliance CSID, identified by its request_id, for the production CSID."""
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

    return _ok_json(response)


def renew_production_csid(setting ,otp , authorization , csr) -> dict:
    """Request a new production CSID with a fresh OTP and the device's existing CSR."""
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

    return _ok_json(response)


def make_invoice_request(clearance_status , authentication , invoice_hash , invoice_uuid , invoice_encoded , setting , endpoint):
    """Send one signed invoice to `endpoint`: clearance, reporting, or the onboarding's compliance
    checks."""
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


def _ok_json(response) -> dict:
    """The response body, or ZATCA's response text thrown as the error when it is not HTTP 200."""
    if response.status_code != 200:
        frappe.throw(str(response.text))

    return response.json()


# ====================================================================================================
# ONBOARDING WIZARD
# The wizard calls these by dotted path (zatca-onboarding/src/api/live.ts), so they must keep their
# names and stay in this module. setup.py imports this module, so they import it inside the function.


@frappe.whitelist()
def register_company(**kwargs) :
    """Save the wizard's company and registers, then onboard each register in turn.

    Returns only when every register is done; the wizard follows the "zatca" realtime events instead
    of waiting for this response.
    """
    from optima_zatca.zatca.setup import saving_register_data

    validate_register_data(**kwargs)
    saving_register_data(**kwargs)

    frappe.response["message"] = _("Company Data Successfuly Saved")


@frappe.whitelist()
def get_companies_registered() :
    from optima_zatca.zatca.setup import get_registered_companies

    list_of_companies = get_registered_companies()
    return list_of_companies
