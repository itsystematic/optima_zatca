# Copyright (c) 2023, Yasser Elbana and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import get_url_to_list


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "title",
            "label": _("Title"),
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "fieldname": "vat_amount",
            "label": _("VAT Amount (SAR)"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150,
        },
        {
            "fieldname": "currency",
            "label": _("Currency"),
            "fieldtype": "Currency",
            "width": 150,
            "hidden": 1,
        },
    ]


def get_data(filters):
    data = []

    # Validate if vat settings exist
    company = filters.get("company")
    company_currency = frappe.get_cached_value("Company", company, "default_currency")

    if frappe.db.exists("Zatca VAT Setting", company) is None:
        url = get_url_to_list("Zatca VAT Setting")
        frappe.msgprint(_('Create <a href="{}">Zatca VAT Setting</a> for this company').format(url))
        return data

    ksa_vat_setting = frappe.get_doc("Zatca VAT Setting", company)

    append_data(data, "VAT on Sales", "", company_currency)

    sales_vat = 0
    for vat_setting in ksa_vat_setting.zatca_vat_sales_accounts:
        vat_amount = get_vat_amount(vat_setting, filters, "Sales Invoice")
        append_data(data, vat_setting.title, vat_amount, company_currency)
        sales_vat += vat_amount

    append_data(data, "Grand Total", sales_vat, company_currency)

    append_data(data, "", "", company_currency)

    append_data(data, "VAT on Purchases", "", company_currency)

    purchase_vat = 0
    for vat_setting in ksa_vat_setting.zatca_vat_purchase_accounts:
        vat_amount = get_vat_amount(vat_setting, filters, "Purchase Invoice")
        append_data(data, vat_setting.title, vat_amount, company_currency)
        purchase_vat += vat_amount

    append_data(data, "Grand Total", purchase_vat, company_currency)

    append_data(data, "Net VAT Due", sales_vat - purchase_vat, company_currency)

    return data


# def get_tax_data_for_each_vat_setting(vat_setting, filters, doctype):
# 	"""
# 	(KSA, {filters}, 'Sales Invoice') => 500, 153, 10 \n
# 	calculates and returns \n
# 	total_taxable_amount, total_taxable_adjustment_amount, total_tax"""
# 	from_date = filters.get("from_date")
# 	to_date = filters.get("to_date")

# 	# Initiate variables
# 	total_taxable_amount = 0
# 	total_taxable_adjustment_amount = 0
# 	total_tax = 0
# 	# Fetch All Invoices
# 	invoices = frappe.get_all(
# 		doctype,
# 		filters={"docstatus": 1, "posting_date": ["between", [from_date, to_date]]},
# 		fields=["name", "is_return"],
# 	)

# 	for invoice in invoices:
# 		invoice_items = frappe.get_all(
# 			f"{doctype} Item",
# 			filters={
# 				"docstatus": 1,
# 				"parent": invoice.name,
# 				"item_tax_template": vat_setting.item_tax_template,
# 			},
# 			fields=["item_code", "base_net_amount"],
# 		)

# 		for item in invoice_items:
# 			# Summing up total taxable amount
# 			if invoice.is_return == 0:
# 				total_taxable_amount += item.base_net_amount

# 			if invoice.is_return == 1:
# 				total_taxable_adjustment_amount += item.base_net_amount

# 			# Summing up total tax
# 			total_tax += get_tax_amount(item.item_code, vat_setting.account, doctype, invoice.name)

# 	return total_taxable_amount, total_taxable_adjustment_amount, total_tax


def append_data(data, title, vat_amount, company_currency):
    data.append(
        {
            "title": _(title),
            "vat_amount": vat_amount,
            "currency": company_currency,
        }
    )


# def get_tax_amount(item_code, account_head, doctype, parent):
# 	if doctype == "Sales Invoice":
# 		tax_doctype = "Sales Taxes and Charges"

# 	elif doctype == "Purchase Invoice":
# 		tax_doctype = "Purchase Taxes and Charges"

# 	item_wise_tax_detail = frappe.get_value(
# 		tax_doctype,
# 		{"docstatus": 1, "parent": parent, "account_head": account_head},
# 		"item_wise_tax_detail",
# 	)

# 	tax_amount = 0
# 	if item_wise_tax_detail and len(item_wise_tax_detail) > 0:
# 		item_wise_tax_detail = json.loads(item_wise_tax_detail)
# 		for key, value in item_wise_tax_detail.items():
# 			if key == item_code:
# 				tax_amount = value[1]
# 				break

# 	return tax_amount


def get_vat_amount(vat_setting, filters, doctype):
    """VAT that `doctype` vouchers posted to the setting's account in the period, after returns."""
    totals = frappe.db.sql(
        """
        SELECT COALESCE(SUM(debit), 0) AS debit, COALESCE(SUM(credit), 0) AS credit
        FROM `tabGL Entry`
        WHERE voucher_type = %s AND account = %s AND posting_date BETWEEN %s AND %s
            AND is_cancelled = 0
        """,
        (doctype, vat_setting.account, filters.get("from_date"), filters.get("to_date")),
        as_dict=True,
    )[0]
    return net_vat(doctype, totals.debit, totals.credit)


def net_vat(doctype, debit, credit):
    """Invoices credit output VAT and debit input VAT; their returns post the other way and reduce it."""
    return credit - debit if doctype == "Sales Invoice" else debit - credit
