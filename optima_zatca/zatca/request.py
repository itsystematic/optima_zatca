"""Send HTTP requests to ZATCA.

The URL comes from the Optima Zatca Setting's environment and an endpoint name; the headers and
body come from the caller in zatca/api.py. Nothing here reads a response: whatever ZATCA returns
goes back to the caller to judge.
"""

import requests
import frappe
from frappe import _


# ====================================================================================================
# ENDPOINTS
# One URL per endpoint for each environment a setting's api_endpoints field can name.
# "complainace_checks" is misspelt, but the same key is stored on Optima Zatca Logs and filtered on by
# the Zatca Logs report, so renaming it means migrating those rows as well.


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


def get_base_url(setting=None , endpoint:str=None) -> str :
    """The URL of `endpoint` in the environment the Optima Zatca Setting points at.

    `setting` may be the setting's name or the loaded document: the submission workflow and
    demo.py pass the document, and Frappe 16 refuses a document as a get_value filter.
    """
    if not setting :
        frappe.throw(_("Please Select Company"))

    if isinstance(setting, str):
        environment = frappe.db.get_value("Optima Zatca Setting" , setting , "api_endpoints")
    else:
        environment = setting.get("api_endpoints")

    return BASEURL.get(environment).get(endpoint)


# ====================================================================================================
# REQUESTS
# Only make_post_request turns a network failure into a readable message; the GET and PATCH helpers
# let the requests exception through.


def _block_in_tests():
    """No test may reach ZATCA in any environment: the invoice it sends is fabricated, but the
    certificate it is signed with is the site's real one."""
    if frappe.in_test:
        frappe.throw(_("ZATCA requests are blocked while tests run."))


def make_post_request(setting, endpoint, header, json_data):
    _block_in_tests()
    url = get_base_url(setting, endpoint)
    try:
        response = requests.post(url, headers=header, json=json_data)
        return response

    except Exception as e:
        frappe.throw(_("Zatca Is Not Responding Please Try Again Later"))


def make_get_request(setting , endpoint , header ,json_data) :
    _block_in_tests()
    url = get_base_url(setting , endpoint)

    return requests.get(url , headers=header , json=json_data)


def make_patch_request(setting , endpoint , headers , json_data) :
    _block_in_tests()
    url = get_base_url(setting , endpoint)

    return requests.patch(url , header=headers , json=json_data)
