"""Seed the site the app's integration tests run on.

ERPNext 16 no longer completes the setup wizard before tests, so a fresh test site has no
company, and without a Saudi one the region-gated ZATCA code never runs. This gives such a
site the company a real KSA customer has, plus what `after_install` could not create while
there was no company: VAT accounts, item tax templates and the advance payment item.

A site that already has a company is left untouched.
"""

import frappe
from erpnext.setup.utils import enable_all_roles_and_domains
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
from frappe.utils import now_datetime

from optima_zatca.install import run_provisioning_patches
from optima_zatca.setup.setup_vat_system.set_tax_configuration import create_complete_vat_system

TEST_COMPANY = "Optima Zatca Test Company"


def before_tests():
    if frappe.db.a_row_exists("Company"):
        return

    frappe.clear_cache()
    setup_complete(setup_wizard_args(now_datetime().year))
    if not frappe.db.a_row_exists("Company"):
        raise RuntimeError(f"The setup wizard finished without creating {TEST_COMPANY}; see the Error Log.")

    create_complete_vat_system()
    # run_provisioning_patches rolls back when a patch fails, which would take the
    # uncommitted VAT accounts and templates with it.
    frappe.db.commit()
    run_provisioning_patches()
    enable_all_roles_and_domains()
    frappe.db.commit()


def setup_wizard_args(year):
    return {
        "company_name": TEST_COMPANY,
        "company_abbr": "OZT",
        "country": "Saudi Arabia",
        "currency": "SAR",
        "timezone": "Asia/Riyadh",
        "language": "english",
        "chart_of_accounts": "Standard",
        "fy_start_date": f"{year}-01-01",
        "fy_end_date": f"{year}-12-31",
    }
