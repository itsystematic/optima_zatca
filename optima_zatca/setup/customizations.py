"""
Single source of truth for optima_zatca's self-customizations.

Everything the app adds to standard DocTypes — custom fields, property setters,
and roles — is defined here ONCE and applied idempotently:

- ``ensure_customizations()`` is the apply path. It runs on install
  (``after_install``) and is re-invoked by patches so already-installed sites
  converge to the canonical definitions.
- ``remove_customizations()`` is the symmetric teardown, run on uninstall
  (``before_uninstall``). It removes only the schema the app owns (custom fields,
  property setters, roles) — never user data or the app's own DocTypes.

Custom fields use ``update=True`` (idempotent upsert), so re-running always
re-asserts the definitions below.
"""

from os import listdir

import frappe
import json
from click import secho
from frappe import get_app_path, make_property_setter
from frappe.core.doctype.data_import.data_import import import_doc
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


ZATCA_ROLES = ["Zatca Role", "Zatca Manager"]

ADDRESS_DOCTYPE_FIELDS = [
    "address_title", "address_type", "section_break_123", "short_address", "address_line1", "city", "pincode",
    "column_break_tshas", "building_no", "address_line2", "district", "address_details", "address_name_in_arabic",
    "county", "state", "country", "column_break0", "email_id", "phone", "fax", "tax_category", "is_primary_address",
    "is_shipping_address", "disabled", "linked_with", "is_your_company_address", "links"
]


# ---------------------------------------------------------------------------
# Custom field definitions
# ---------------------------------------------------------------------------

def _selling_child_table_fields():
    """VAT-tracking fields shared by every selling item child table."""
    return [
        {"fieldname": "tax_category", "fieldtype": "Link", "label": "Tax Category",
         "insert_after": "item_tax_template", "options": "Tax Category", "read_only": 1, "hidden": 1},
        {"fieldname": "price_amount", "label": "Price Amount", "fieldtype": "Float",
         "insert_after": "tax_category", "read_only": 1, "hidden": 1, "no_copy": 1},
        {"fieldname": "line_extension_amount", "label": "Line Extension Amount", "fieldtype": "Float",
         "insert_after": "price_amount", "read_only": 1, "hidden": 1, "no_copy": 1},
        {"fieldname": "item_discount", "label": "Item Discount", "fieldtype": "Float",
         "insert_after": "line_extension_amount", "read_only": 1, "hidden": 1, "no_copy": 1},
        {"fieldname": "tax_rate", "fieldtype": "Float", "label": "Tax Rate",
         "insert_after": "item_discount", "read_only": 1, "hidden": 1},
        {"fieldname": "tax_amount", "fieldtype": "Float", "label": "Tax Amount",
         "insert_after": "tax_rate", "read_only": 1, "hidden": 1},
        {"fieldname": "total_amount", "fieldtype": "Currency", "label": "Total Amount",
         "insert_after": "tax_amount", "read_only": 1, "hidden": 1},
        {"fieldname": "tax_exemption", "fieldtype": "Link", "label": "Tax Exemption",
         "insert_after": "total_amount", "options": "Tax Exemption"},
    ]


def _purchase_child_table_fields():
    """VAT-tracking fields for Purchase Invoice Item (visible in the item table)."""
    return [
        {"fieldname": "tax_category", "fieldtype": "Link", "label": "Tax Category",
         "insert_after": "item_tax_template", "options": "Tax Category", "read_only": 1, "hidden": 1},
        {"fieldname": "price_amount", "label": "Price Amount", "fieldtype": "Float",
         "insert_after": "tax_category", "read_only": 1, "hidden": 1, "no_copy": 1},
        {"fieldname": "line_extension_amount", "label": "Line Extension Amount", "fieldtype": "Float",
         "insert_after": "price_amount", "read_only": 1, "hidden": 1, "no_copy": 1},
        {"fieldname": "item_discount", "label": "Item Discount", "fieldtype": "Float",
         "insert_after": "line_extension_amount", "read_only": 1, "hidden": 1, "no_copy": 1},
        {"fieldname": "tax_rate", "fieldtype": "Float", "label": "Tax Rate",
         "insert_after": "item_discount", "read_only": 1, "in_list_view": 1},
        {"fieldname": "tax_amount", "fieldtype": "Currency", "label": "Tax Amount",
         "insert_after": "tax_rate", "read_only": 1, "in_list_view": 1},
        {"fieldname": "total_amount", "fieldtype": "Currency", "label": "Total Amount",
         "insert_after": "tax_amount", "read_only": 1},
        {"fieldname": "tax_exemption", "fieldtype": "Link", "label": "Tax Exemption",
         "insert_after": "total_amount", "options": "Tax Exemption"},
    ]


def _base_sales_invoice_fields():
    """Core ZATCA fields on Sales Invoice (identity, clearance, QR)."""
    return [
        {"fieldname": "commercial_register", "fieldtype": "Link", "label": "Commercial Register",
         "insert_after": "company", "options": "Commercial Register",
         "description": "this field should contain the 10-digit", "reqd": 1},
        {"fieldname": "clearance_or_reporting", "fieldtype": "Data", "label": "Clearance Or Reporting",
         "insert_after": "column_break_14", "read_only": 1, "no_copy": 1},
        {"fieldname": "sales_invoice_type", "fieldtype": "Link", "label": "Sales Invoice Type",
         "insert_after": "clearance_or_reporting", "options": "Sales Invoice Type",
         "default": "Normal", "reqd": 1, "depends_on": "customer"},
        {"fieldname": "prepayment_sales_order", "fieldtype": "Link", "label": "Sales Order",
         "options": "Sales Order", "insert_after": "due_date", "read_only": 1,
         "description": "Prepayment Sales Invoice is for this Sales Order"},
        {"fieldname": "reason_for_issuance", "fieldtype": "Small Text", "label": "Reason For issuance",
         "insert_after": "is_debit_note", "depends_on": "eval: doc.is_return || doc.is_debit_note",
         "mandatory_depends_on": "eval: doc.is_return || doc.is_debit_note"},
        {"fieldname": "ksa_einv_qr", "fieldtype": "Attach Image", "label": "KSA E-Invoicing QR",
         "insert_after": "reason_for_issuance", "read_only": 1, "hidden": 1, "no_copy": 1},
        {"fieldname": "section_break89", "fieldtype": "Section Break", "insert_after": "ksa_einv_qr"},
        {"fieldname": "sent_to_zatca", "fieldtype": "Check", "label": "Sent To Zatca",
         "insert_after": "is_discounted", "read_only": 1, "no_copy": 1},
    ]


def _prepayment_sales_invoice_fields():
    """Prepayment-cycle fields on Sales Invoice (tab, tables, totals, percentages).

    ``sales_invoice_type`` / ``prepayment_sales_order`` are intentionally NOT
    repeated here — they live in :func:`_base_sales_invoice_fields`.
    """
    return [
        {"fieldname": "prepayments_tab", "fieldtype": "Tab Break", "label": "Prepayments",
         "insert_after": "connections_tab",
         "depends_on": "eval:['Prepayment', 'Adjustment', 'Final Adjustment'].includes(doc.sales_invoice_type)"},
        {"fieldname": "previous_prepayment", "fieldtype": "Link", "label": "Previous Prepayment",
         "options": "Prepayment Invoice", "insert_after": "prepayments_tab", "no_copy": 1,
         "read_only_depends_on": "eval: doc.return_against",
         "mandatory_depends_on": "eval:['Prepayment', 'Adjustment', 'Final Adjustment'].includes(doc.sales_invoice_type)"},
        {"fieldname": "prepayments_details", "fieldtype": "Section Break", "label": "Prepayment Details",
         "insert_after": "previous_prepayment"},
        {"fieldname": "prepayments_invcoies", "fieldtype": "Table", "label": "Prepayments Invoices",
         "options": "Prepayment Details", "insert_after": "prepayments_details",
         "depends_on": "eval:doc.previous_prepayment", "read_only": 1},
        {"fieldname": "prepayment_totals", "fieldtype": "Section Break", "label": "Prepayment Totals",
         "insert_after": "prepayments_invcoies", "depends_on": "eval:doc.previous_prepayment"},
        {"fieldname": "total_tax_amount", "fieldtype": "Currency", "label": "Total Tax Amount",
         "insert_after": "prepayment_totals", "read_only": 1, "default": 0},
        {"fieldname": "column_break_eiwq", "fieldtype": "Column Break", "insert_after": "total_tax_amount"},
        {"fieldname": "total_taxable_amount", "fieldtype": "Currency", "label": "Total Taxable Amount",
         "insert_after": "column_break_eiwq", "read_only": 1, "default": 0},
        {"fieldname": "column_break_eiwe", "fieldtype": "Column Break", "insert_after": "total_taxable_amount"},
        {"fieldname": "total_grands", "fieldtype": "Currency", "label": "Total Grands",
         "insert_after": "column_break_eiwe", "read_only": 1, "default": 0},
        {"fieldname": "deducted_prepayment_totals", "fieldtype": "Section Break", "label": "Deducted Prepayment Totals",
         "insert_after": "total_grands", "depends_on": "eval:doc.adjustment_percentage"},
        {"fieldname": "deducted_tax_amount", "fieldtype": "Currency", "label": "Deducted Tax Amount",
         "insert_after": "deducted_prepayment_totals", "read_only": 1, "default": 0},
        {"fieldname": "column_break_efde", "fieldtype": "Column Break", "insert_after": "deducted_tax_amount"},
        {"fieldname": "deducted_taxable_amount", "fieldtype": "Currency", "label": "Deducted Taxable Amount",
         "insert_after": "column_break_efde", "read_only": 1, "default": 0},
        {"fieldname": "column_break_eifde", "fieldtype": "Column Break", "insert_after": "deducted_taxable_amount"},
        {"fieldname": "deducted_grand_total", "fieldtype": "Currency", "label": "Deducted Grand Total",
         "insert_after": "column_break_eifde", "read_only": 1, "default": 0},
        {"fieldname": "adjustment_totals", "fieldtype": "Section Break", "label": "Adjustment Totals",
         "insert_after": "deducted_grand_total", "depends_on": "eval:doc.adjustment_percentage"},
        {"fieldname": "adjustment_tax_amount", "fieldtype": "Currency", "label": "Adjustment Tax Amount",
         "insert_after": "adjustment_totals", "read_only": 1, "default": 0},
        {"fieldname": "column_break_eiwqwe", "fieldtype": "Column Break", "insert_after": "adjustment_tax_amount"},
        {"fieldname": "adjustment_taxable_amount", "fieldtype": "Currency", "label": "Adjustment Taxable Amount",
         "insert_after": "column_break_eiwqwe", "read_only": 1, "default": 0},
        {"fieldname": "column_break_eiweqwe", "fieldtype": "Column Break", "insert_after": "adjustment_taxable_amount"},
        {"fieldname": "adjustment_grands", "fieldtype": "Currency", "label": "Adjustment Grands",
         "insert_after": "column_break_eiweqwe", "read_only": 1, "default": 0},
        {"fieldname": "prepayment_percentages", "fieldtype": "Section Break", "label": "Prepayment Percentages",
         "insert_after": "adjustment_grands",
         "depends_on": "eval:['Adjustment', 'Final Adjustment'].includes(doc.sales_invoice_type) && doc.previous_prepayment",
         "read_only_depends_on": "eval:doc.sales_invoice_type == 'Final Adjustment'"},
        {"fieldname": "remaining_percentage", "fieldtype": "Percent", "label": "Remaining Percentage",
         "insert_after": "prepayment_percentages", "precision": 5, "default": 100, "read_only": 1},
        {"fieldname": "column_break_eikd", "fieldtype": "Column Break", "insert_after": "remaining_percentage"},
        {"fieldname": "max_adjustment_limit", "fieldtype": "Percent", "label": "Max Limit Percentage",
         "insert_after": "column_break_eikd", "read_only": 1, "default": 0, "precision": 5},
        {"fieldname": "column_break_eikder", "fieldtype": "Column Break", "insert_after": "max_adjustment_limit"},
        {"fieldname": "adjustment_percentage", "fieldtype": "Percent", "label": "Adjustment Percentage",
         "insert_after": "column_break_eikder", "precision": 5,
         "depends_on": "eval:doc.previous_prepayment",
         "mandatory_depends_on": "eval:doc.sales_invoice_type == 'Adjustment'",
         "read_only_depends_on": "eval:doc.sales_invoice_type == 'Final Adjustment'  || doc.is_return"},
    ]


def get_custom_fields():
    """Every custom field owned by optima_zatca, keyed by DocType."""
    selling_child = _selling_child_table_fields()
    return {
        "Company": [
            {"fieldname": "company_name_in_arabic", "fieldtype": "Data", "label": "Company Name In Arabic",
             "insert_after": "company_name",
             "description": "This name must match the company name in the government commercial register."},
            {"fieldname": "section_break87956", "fieldtype": "Section Break", "insert_after": "company_name_in_arabic"},
        ],
        "Address": [
            {"fieldname": "section_break_123", "fieldtype": "Section Break", "label": "Saudi National Address Components",
             "insert_after": "address_type"},
            {"fieldname": "short_address", "fieldtype": "Data", "label": "Short Address",
             "insert_after": "section_break_123"},
            {"fieldname": "building_no", "fieldtype": "Data", "label": "Building No",
             "insert_after": "column_break_tshas"},
            {"fieldname": "column_break_tshas", "fieldtype": "Column Break", "insert_after": "pincode"},
            {"fieldname": "district", "fieldtype": "Data", "label": "District", "insert_after": "address_line2"},
            {"fieldname": "address_name_in_arabic", "fieldtype": "Data", "label": "Address Name In Arabic",
             "insert_after": "address_details"},
        ],
        "Branch": [
            {"fieldname": "commercial_register", "fieldtype": "Link", "label": "Commercial Register",
             "insert_after": "branch", "options": "Commercial Register",
             "description": "this field should contain the 10-digit"},
        ],
        "Sales Invoice": _base_sales_invoice_fields() + _prepayment_sales_invoice_fields(),
        "Sales Invoice Item": selling_child,
        "Quotation Item": selling_child,
        "Sales Order Item": selling_child,
        "Delivery Note Item": selling_child,
        "POS Invoice Item": selling_child,
        "Purchase Invoice Item": _purchase_child_table_fields(),
        "Customer": [
            {"fieldname": "registration_type", "fieldtype": "Link", "label": "Registration Type",
             "insert_after": "tax_id", "options": "Registration Type",
             "mandatory_depends_on": "eval: doc.customer_type == 'Company' ", "default": "CRN"},
            {"fieldname": "registration_value", "fieldtype": "Data", "label": "Registration Value",
             "insert_after": "registration_type", "mandatory_depends_on": "eval: doc.customer_type == 'Company' "},
        ],
        "Item Tax Template": [
            {"fieldname": "tax_category", "fieldtype": "Link", "label": "Tax Category",
             "insert_after": "company", "options": "Tax Category"},
        ],
    }


def get_property_setters():
    """Property setters that relabel/hide standard fields for KSA."""
    setters = [
        # Address relabeling + field order
        {"doctype": "Address", "doctype_or_field": "DocField", "fieldname": "address_line1",
         "property": "label", "value": "Street", "property_type": "Data"},
        {"doctype": "Address", "doctype_or_field": "DocField", "fieldname": "address_line2",
         "property": "label", "value": "Secondary No", "property_type": "Data"},
        {"doctype": "Address", "doctype_or_field": "DocType", "fieldname": None,
         "property": "field_order", "value": json.dumps(ADDRESS_DOCTYPE_FIELDS), "property_type": "Data"},
    ]

    # Discount + rounded-total defaults across selling transactions
    for doctype in ["Sales Invoice", "Sales Order", "Quotation", "Delivery Note"]:
        setters += [
            {"doctype": doctype, "doctype_or_field": "DocField", "fieldname": "apply_discount_on",
             "property": "read_only", "value": "1", "property_type": "Check"},
            {"doctype": doctype, "doctype_or_field": "DocField", "fieldname": "apply_discount_on",
             "property": "default", "value": "Net Total", "property_type": "Data"},
            {"doctype": doctype, "doctype_or_field": "DocField", "fieldname": "disable_rounded_total",
             "property": "default", "value": "1", "property_type": "Check"},
            {"doctype": doctype, "doctype_or_field": "DocField", "fieldname": "disable_rounded_total",
             "property": "hidden", "value": "1", "property_type": "Check"},
        ]

    # Hide standard tax fields (ZATCA computes tax per line)
    for doctype in ["Sales Invoice", "Sales Order", "Quotation", "Delivery Note"]:
        setters += [
            {"doctype": doctype, "doctype_or_field": "DocField", "fieldname": "taxes_and_charges",
             "property": "hidden", "value": "1", "property_type": "Check"},
            {"doctype": doctype, "doctype_or_field": "DocField", "fieldname": "tax_category",
             "property": "hidden", "value": "1", "property_type": "Check"},
        ]

    return setters


# ---------------------------------------------------------------------------
# Apply (install + patches)
# ---------------------------------------------------------------------------

def ensure_customizations():
    """Idempotently create/update every custom field, property setter, and role."""
    create_custom_fields(get_custom_fields(), update=True)
    _apply_property_setters()
    _ensure_roles()


def _apply_property_setters():
    for setter in get_property_setters():
        make_property_setter(setter, ignore_validate=True, validate=False)


def _ensure_roles():
    for role in ZATCA_ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)


def add_standard_data():
    """Import the seed docs shipped under optima_zatca/files/."""
    files_dir = get_app_path("optima_zatca", "files")
    all_files = listdir(files_dir)
    secho("Install Doctypes From Files => {}".format(" , ".join(all_files)), fg="blue")
    for file in all_files:
        import_doc(get_app_path("optima_zatca", "files", file))


# ---------------------------------------------------------------------------
# Teardown (uninstall)
# ---------------------------------------------------------------------------

def remove_customizations():
    """Remove the schema the app owns. Non-destructive: leaves user data and the
    app's own DocTypes (Frappe removes those) untouched."""
    _remove_custom_fields()
    _remove_property_setters()
    _remove_roles()


def _remove_custom_fields():
    for doctype, fields in get_custom_fields().items():
        for field in fields:
            name = f"{doctype}-{field['fieldname']}"
            if frappe.db.exists("Custom Field", name):
                frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)


def _remove_property_setters():
    for setter in get_property_setters():
        filters = {
            "doc_type": setter["doctype"],
            "property": setter["property"],
            "doctype_or_field": setter["doctype_or_field"],
        }
        if setter.get("fieldname"):
            filters["field_name"] = setter["fieldname"]
        for name in frappe.get_all("Property Setter", filters=filters, pluck="name"):
            frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)


def _remove_roles():
    for role in ZATCA_ROLES:
        if not frappe.db.exists("Role", role):
            continue
        try:
            frappe.delete_doc("Role", role, ignore_permissions=True)
        except frappe.LinkExistsError:
            # Role is still assigned to users; leave it in place rather than fail uninstall.
            secho(f"Role '{role}' is still in use — left in place", fg="yellow")
