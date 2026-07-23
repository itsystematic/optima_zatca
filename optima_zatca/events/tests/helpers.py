"""Shared test factories for the Sales Invoice events suite.

Modeled on ``optima_payment/optima_payment/tests/utils.py``: idempotent,
``get_value``/``exists``-guarded builders that reuse a real site's existing
records where possible and only create what's missing. Written against a KSA/
ZATCA site (techno.local), so they resolve accounts from company defaults and
satisfy the two mandatory Sales Invoice custom fields (``commercial_register``,
``sales_invoice_type``).

The prepayment numeric fields (``total_grands`` / ``deducted_grand_total`` /
``adjustment_percentage``) are normally computed client-side in
``public/js/sales_invoice/prepayment.js``; here they're set directly on the doc.
"""

import frappe
import erpnext
from frappe.utils import nowdate, add_days


# ====================================================================================================
# COMPANY / ACCOUNT LOOKUPS
# ====================================================================================================


def get_company():
    return erpnext.get_default_company()


def get_receivable_account(company=None):
    company = company or get_company()
    return frappe.get_cached_value("Company", company, "default_receivable_account") or frappe.db.get_value(
        "Account", {"company": company, "account_type": "Receivable", "is_group": 0}, "name"
    )


def get_income_account(company=None):
    company = company or get_company()
    return frappe.get_cached_value("Company", company, "default_income_account") or frappe.db.get_value(
        "Account", {"company": company, "root_type": "Income", "is_group": 0}, "name"
    )


def get_cost_center(company=None):
    company = company or get_company()
    return frappe.get_cached_value("Company", company, "cost_center") or frappe.db.get_value(
        "Cost Center", {"company": company, "is_group": 0}, "name"
    )


# ====================================================================================================
# MANDATORY-FIELD FIXTURES (KSA/ZATCA)
# ====================================================================================================


def get_commercial_register(company=None):
    """The Sales Invoice custom field ``commercial_register`` is mandatory on this site."""
    company = company or get_company()
    return frappe.db.get_value("Commercial Register", {"company": company}, "name") or frappe.db.get_value(
        "Commercial Register", {}, "name"
    )


def get_or_create_sales_invoice_type(name):
    """The five types ship as fixtures; create defensively for a scratch site."""
    if not frappe.db.exists("Sales Invoice Type", name):
        frappe.get_doc({"doctype": "Sales Invoice Type", "sales_invoice_type": name}).insert(
            ignore_permissions=True
        )
    return name


# ====================================================================================================
# PARTY / ITEM FIXTURES
# ====================================================================================================


def get_customer():
    """Reuse an existing Individual customer (dodges KSA mandatory registration
    fields that apply to Company-type customers)."""
    customer = frappe.db.get_value("Customer", {"customer_type": "Individual", "disabled": 0}, "name")
    if not customer:
        customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": "Optima Zatca Test Customer",
                "customer_group": customer_group,
                "customer_type": "Individual",
            }
        ).insert(ignore_permissions=True).name
    return customer


def get_item():
    """Reuse an existing non-stock item so the line's accounting is already valid."""
    return frappe.db.get_value("Item", {"is_stock_item": 0, "disabled": 0}, "name")


# ====================================================================================================
# PREPAYMENT INVOICE FIXTURE
# ====================================================================================================


def make_prepayment_invoice(*, is_linked=0, **overrides):
    """Insert a minimal Prepayment Invoice row (used for linkage / return tests).

    ``is_linked`` drives ``_validate_prepayment_linkage``: an already-linked
    prepayment must be rejected as a return target.
    """
    # Prepayment Invoice autoname is ``field:id``; supply a unique one.
    fields = {
        "doctype": "Prepayment Invoice",
        "id": f"TEST-PRE-{frappe.generate_hash(length=8)}",
        "is_linked": is_linked,
    }
    fields.update(overrides)
    doc = frappe.get_doc(fields)
    doc.insert(ignore_permissions=True)
    return doc


# ====================================================================================================
# SALES ORDER / SALES INVOICE FACTORIES
# ====================================================================================================


def make_sales_order(*, company=None, customer=None, do_not_submit=False, **overrides):
    """Minimal Sales Order used as an Initial Prepayment reference."""
    company = company or get_company()
    customer = customer or get_customer()
    cost_center = get_cost_center(company)
    fields = {
        "doctype": "Sales Order",
        "company": company,
        "customer": customer,
        "cost_center": cost_center,
        "delivery_date": nowdate(),
        "items": [
            {
                "item_code": get_item(),
                "qty": 1,
                "rate": 100,
                "income_account": get_income_account(company),
                "cost_center": cost_center,
            }
        ],
    }
    fields.update(overrides)
    so = frappe.get_doc(fields)
    so.insert(ignore_permissions=True)
    if not do_not_submit:
        so.submit()
    return so


def make_sales_invoice(
    *,
    sales_invoice_type="Normal",
    company=None,
    customer=None,
    do_not_insert=False,
    **overrides,
):
    """Build a draft Sales Invoice that reaches the ``validate`` hook.

    Inserts (running validation) unless ``do_not_insert=True``; never submits,
    so the ZATCA ``on_submit`` path is not triggered. Adjustment types get the
    mandatory ``previous_prepayment`` and default prepayment totals unless the
    caller overrides them.
    """
    company = company or get_company()
    customer = customer or get_customer()
    cost_center = get_cost_center(company)

    fields = {
        "doctype": "Sales Invoice",
        "company": company,
        "customer": customer,
        "posting_date": nowdate(),
        "due_date": add_days(nowdate(), 30),
        "currency": frappe.get_cached_value("Company", company, "default_currency"),
        "commercial_register": get_commercial_register(company),
        "sales_invoice_type": get_or_create_sales_invoice_type(sales_invoice_type),
        "debit_to": get_receivable_account(company),
        "cost_center": cost_center,
        "items": [
            {
                "item_code": get_item(),
                "qty": 1,
                "rate": 100,
                "income_account": get_income_account(company),
                "cost_center": cost_center,
            }
        ],
    }

    if sales_invoice_type in ("Prepayment", "Adjustment", "Final Adjustment"):
        # previous_prepayment is mandatory_depends_on for these types.
        fields.setdefault("previous_prepayment", make_prepayment_invoice().name)
        fields.setdefault("total_grands", 100)
        fields.setdefault("deducted_grand_total", 50)
        fields.setdefault("adjustment_percentage", 50)

    fields.update(overrides)
    si = frappe.get_doc(fields)
    if not do_not_insert:
        si.insert(ignore_permissions=True)
    return si
