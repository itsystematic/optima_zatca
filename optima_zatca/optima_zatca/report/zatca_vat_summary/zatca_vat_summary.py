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
            "fieldname": "amount",
            "label": _("Amount (SAR)"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150,
        },
        # {
        #     "fieldname": "adjustment_amount",
        #     "label": _("Adjustment (SAR)"),
        #     "fieldtype": "Currency",
        #     "options": "currency",
        #     "width": 150,
        # },
        # {
        #     "fieldname": "vat_amount",
        #     "label": _("VAT Amount (SAR)"),
        #     "fieldtype": "Currency",
        #     "options": "currency",
        #     "width": 150,
        # },
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

    # Sales Heading
    append_data(data, "VAT on Sales", "", "", "", company_currency)

    grand_total_taxable_amount = 0
    grand_total_taxable_adjustment_amount = 0
    grand_total_tax = 0

    net_vat_due_amount = 0

    for vat_setting in ksa_vat_setting.zatca_vat_sales_accounts:
        (
            total_taxable_amount,
            total_taxable_adjustment_amount,
            total_tax,
        ) = get_tax_data_for_each_vat_setting(vat_setting, filters, "Sales Invoice")

        # Adding results to data
        append_data(
            data,
            vat_setting.title,
            total_taxable_amount,
            total_taxable_adjustment_amount,
            total_tax,
            company_currency,
        )

        grand_total_taxable_amount += total_taxable_amount
        grand_total_taxable_adjustment_amount += total_taxable_adjustment_amount
        grand_total_tax += total_tax

    net_vat_due_amount += grand_total_tax

    # Sales Grand Total
    append_data(
        data,
        "Grand Total",
        grand_total_taxable_amount,
        grand_total_taxable_adjustment_amount,
        grand_total_tax,
        company_currency,
    )

    # Blank Line
    append_data(data, "", "", "", "", company_currency)

    # Purchase Heading
    append_data(data, "VAT on Purchases", "", "", "", company_currency)

    grand_total_taxable_amount = 0
    grand_total_taxable_adjustment_amount = 0
    grand_total_tax = 0

    for vat_setting in ksa_vat_setting.zatca_vat_purchase_accounts:
        (
            total_taxable_amount,
            total_taxable_adjustment_amount,
            total_tax,
        ) = get_tax_data_for_each_vat_setting(vat_setting, filters, "Purchase Invoice")

        # Adding results to data
        append_data(
            data,
            vat_setting.title,
            total_taxable_amount,
            total_taxable_adjustment_amount,
            total_tax,
            company_currency,
        )

        grand_total_taxable_amount += total_taxable_amount
        grand_total_taxable_adjustment_amount += total_taxable_adjustment_amount
        grand_total_tax += total_tax

    net_vat_due_amount -= grand_total_tax

    # Purchase Grand Total
    append_data(
        data,
        "Grand Total",
        grand_total_taxable_amount,
        grand_total_taxable_adjustment_amount,
        grand_total_tax,
        company_currency,
    )

    # Net VAT Due
    append_data(
        data,
        "Net VAT Due",
        None,
        None,
        net_vat_due_amount,
        company_currency,
    )

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


def append_data(data, title, amount, adjustment_amount, vat_amount, company_currency):
    """Returns data with appended value."""
    data.append(
        {
            "title": _(title),
            "amount": amount,
            "adjustment_amount": adjustment_amount,
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


def get_tax_data_for_each_vat_setting(vat_setting, filters, doctype):
    """
    (KSA, {filters}, 'Sales Invoice') => 500, 153, 10 \n
    calculates and returns \n
    total_taxable_amount, total_taxable_adjustment_amount, total_tax"""
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Initiate variables
    total_taxable_amount = 0
    total_taxable_adjustment_amount = 0
    total_tax = 0
    # Fetch All Invoices
    invoices = frappe.db.sql("""
                        SELECT 
                            SUM(credit) AS credit, 
                            SUM(debit) AS debit,
                            SUM(credit) - SUM(debit) AS total_1,
                            SUM(debit) - SUM(credit) AS total_2
                        FROM `tabGL Entry`
                        WHERE voucher_type = %s AND account = %s AND posting_date BETWEEN %s AND %s
                                AND is_cancelled = 0;
                        """, (doctype, vat_setting.account, from_date, to_date), as_dict=1)

    if doctype == "Sales Invoice":
        total_taxable_amount = invoices[0].get("credit") if invoices[0].get("credit") else 0
        total_taxable_adjustment_amount = invoices[0].get("debit") if invoices[0].get("debit") else 0
        total_tax = invoices[0].get("total_1") if invoices[0].get("total_1") else 0
    else:
        total_taxable_amount = invoices[0].get("debit") if invoices[0].get("debit") else 0
        total_taxable_adjustment_amount = invoices[0].get("credit") if invoices[0].get("credit") else 0
        total_tax = invoices[0].get("total_2") if invoices[0].get("total_2") else 0

    return total_taxable_amount, total_taxable_adjustment_amount, total_tax
