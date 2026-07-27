"""Shared test factories for the Sales Invoice events suite.

Modeled on ``optima_payment/optima_payment/tests/utils.py``: idempotent,
``get_value``/``exists``-guarded builders. **Site-agnostic** — they provision
their own dedicated party/item/commercial-register records rather than reusing
whatever the site happens to contain. Reusing arbitrary existing records is
what broke this suite on a fresh site (the first "non-stock" Item it found was
a *fixed asset*, so ``validate_fixed_asset`` demanded an Asset). Everything the
tests touch is now named ``Optima Zatca Test …`` and created on first use, so a
scratch CI site and a real KSA site behave identically.

Accounts and cost centers still come from company defaults (every ERPNext
company has them); the two mandatory Sales Invoice custom fields
(``commercial_register``, ``sales_invoice_type``) are provisioned here.

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


TEST_COMMERCIAL_REGISTER = "Optima Zatca Test CR"


def get_or_create_commercial_register(company=None):
    """Provision the mandatory (``reqd``) Sales Invoice ``commercial_register``.

    Tests never submit, so the certificate/device side of a real Commercial
    Register is never exercised — a bare record with its three mandatory fields
    (``commercial_register``, ``commercial_register_name``, ``address``) is
    enough to clear ``validate``.

    A real KSA site already has a (cert-bound, ``is_default``) Commercial
    Register, and the controller forbids adding a second default for the same
    company — so reuse the site's existing register when there is one and only
    fabricate a minimal record on a scratch site that has none.
    """
    company = company or get_company()
    existing = frappe.db.get_value(
        "Commercial Register", {"company": company}, "name"
    ) or frappe.db.get_value("Commercial Register", {}, "name")
    if existing:
        return existing

    address = _get_or_create_test_address(company)
    cr = frappe.get_doc(
        {
            "doctype": "Commercial Register",
            "company": company,
            "commercial_register": "1010101010",  # 10-digit CRN, per the field's description
            "commercial_register_name": TEST_COMMERCIAL_REGISTER,
            "address": address,
        }
    )
    cr.insert(ignore_permissions=True)
    return cr.name


def _get_or_create_test_address(company):
    """Minimal Address for the test Commercial Register (address is a reqd link)."""
    name = frappe.db.get_value("Address", {"address_title": "Optima Zatca Test Address"}, "name")
    if name:
        return name

    country = frappe.db.get_value("Company", company, "country") or frappe.db.get_value(
        "Country", {}, "name"
    )
    address = frappe.get_doc(
        {
            "doctype": "Address",
            "address_title": "Optima Zatca Test Address",
            "address_type": "Billing",
            "address_line1": "Test Street",
            "city": "Riyadh",
            "country": country,
        }
    )
    address.insert(ignore_permissions=True)
    return address.name


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


TEST_CUSTOMER = "Optima Zatca Test Customer"
TEST_ITEM = "Optima Zatca Test Item"


def get_or_create_customer():
    """Dedicated Individual customer.

    ``customer_type="Individual"`` dodges the KSA registration/``tax_id`` fields
    that this site's customizations make mandatory for Company-type customers.
    """
    if not frappe.db.exists("Customer", TEST_CUSTOMER):
        customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
        frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": TEST_CUSTOMER,
                "customer_group": customer_group,
                "customer_type": "Individual",
                # Site-specific mandatory custom field; the key is a no-op where it doesn't exist.
                "customer_name_in_arabic": TEST_CUSTOMER,
            }
        ).insert(ignore_permissions=True)
    return TEST_CUSTOMER


def get_or_create_item(company=None):
    """Dedicated non-stock service item.

    Explicitly ``is_stock_item=0`` and ``is_fixed_asset=0``: a fixed-asset item
    makes ERPNext's ``validate_fixed_asset`` demand an Asset on every line, which
    is the exact failure that borrowing an arbitrary existing item produced.
    This site's KSA customization makes the Item ``taxes`` table mandatory
    (a property setter installed by ``setup_item_table_property_setter``), so an
    Item Tax Template row is always attached — which in turn is why the SO/SI
    factories pre-seed their own ``taxes`` row with a ``cost_center`` (see
    ``_tax_row``).
    """
    company = company or get_company()
    if not frappe.db.exists("Item", TEST_ITEM):
        item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": TEST_ITEM,
                "item_name": TEST_ITEM,
                "item_group": item_group,
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "is_fixed_asset": 0,
                "taxes": [{"item_tax_template": get_or_create_item_tax_template(company)}],
            }
        ).insert(ignore_permissions=True)
    return TEST_ITEM


TEST_ITEM_TAX_TEMPLATE = "Optima Zatca Test VAT 15%"


def get_or_create_item_tax_template(company=None):
    """An Item Tax Template for ``company``.

    A real KSA site already has the ``KSA VAT …`` templates that
    ``setup_item_tax_templates`` installs in ``after_install`` — reuse one.
    Only a scratch site (where that installer found no VAT accounts, so created
    no template) reaches the fabricate branch, which builds a minimal 15%
    template backed by a get-or-created Tax account.
    """
    company = company or get_company()
    existing = frappe.db.get_value(
        "Item Tax Template", {"company": company}, "name"
    ) or frappe.db.get_value("Item Tax Template", {}, "name")
    if existing:
        return existing

    template = frappe.get_doc(
        {
            "doctype": "Item Tax Template",
            "title": TEST_ITEM_TAX_TEMPLATE,
            "company": company,
            "taxes": [{"tax_type": _get_or_create_tax_account(company), "tax_rate": 15.0}],
        }
    )
    template.insert(ignore_permissions=True)
    return template.name


def _get_or_create_tax_account(company):
    """A leaf Tax account under the company's Liability tree (VAT output)."""
    existing = frappe.db.get_value(
        "Account", {"company": company, "account_type": "Tax", "is_group": 0}, "name"
    )
    if existing:
        return existing

    parent = frappe.db.get_value(
        "Account", {"company": company, "root_type": "Liability", "is_group": 1}, "name"
    )
    account = frappe.get_doc(
        {
            "doctype": "Account",
            "account_name": "Optima Zatca Test Output VAT",
            "parent_account": parent,
            "company": company,
            "is_group": 0,
            "account_type": "Tax",
        }
    )
    account.insert(ignore_permissions=True)
    return account.name


def _tax_row(company, cost_center):
    """A Sales Taxes and Charges row (with ``cost_center``) mirroring the item's
    tax template, pre-seeded on orders/invoices.

    Attaching an Item Tax Template makes ERPNext's "add taxes from item tax
    template" auto-append a Sales Taxes row; on this site tax rows require a
    ``cost_center``, so seed the row explicitly rather than let the auto-append
    inject one without it.
    """
    template = get_or_create_item_tax_template(company)
    account_head, tax_rate = frappe.db.get_value(
        "Item Tax Template Detail", {"parent": template}, ["tax_type", "tax_rate"]
    )
    return {
        "charge_type": "On Net Total",
        "account_head": account_head,
        "rate": tax_rate,
        "cost_center": cost_center,
        "description": account_head,
    }


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
    customer = customer or get_or_create_customer()
    cost_center = get_cost_center(company)
    fields = {
        "doctype": "Sales Order",
        "company": company,
        "customer": customer,
        "cost_center": cost_center,
        "delivery_date": nowdate(),
        "items": [
            {
                "item_code": get_or_create_item(),
                "qty": 1,
                "rate": 100,
                "income_account": get_income_account(company),
                "cost_center": cost_center,
            }
        ],
    }
    if tax_row := _tax_row(company, cost_center):
        fields["taxes"] = [tax_row]
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
    customer = customer or get_or_create_customer()
    cost_center = get_cost_center(company)

    fields = {
        "doctype": "Sales Invoice",
        "company": company,
        "customer": customer,
        "posting_date": nowdate(),
        "due_date": add_days(nowdate(), 30),
        "currency": frappe.get_cached_value("Company", company, "default_currency"),
        "commercial_register": get_or_create_commercial_register(company),
        "sales_invoice_type": get_or_create_sales_invoice_type(sales_invoice_type),
        "debit_to": get_receivable_account(company),
        "cost_center": cost_center,
        "items": [
            {
                "item_code": get_or_create_item(),
                "qty": 1,
                "rate": 100,
                "income_account": get_income_account(company),
                "cost_center": cost_center,
            }
        ],
    }

    if tax_row := _tax_row(company, cost_center):
        fields["taxes"] = [tax_row]

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
