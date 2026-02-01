import frappe
import json
import traceback
from frappe.utils import flt
from optima_zatca.zatca.utils import log_and_throw_error

def update_itemised_tax_data(doc):
    """
    Regional override for itemised tax data calculation.
    Routes to appropriate handler based on document type.
    """
    if not doc.taxes:
        return

    if doc.doctype == "Purchase Invoice":
        _calculate_purchase_invoice_item_taxes(doc)
    else:
        _calculate_sales_document_item_taxes(doc)


def _calculate_sales_document_item_taxes(doc):
    """
    Calculate per-item tax data for Sales documents (Sales Invoice, Quotation, etc.).
    Populates custom fields: tax_category, price_amount, line_extension_amount,
    item_discount, tax_rate, tax_amount, total_amount.
    """
    try:
        itemised_tax = get_itemised_tax(doc.taxes)
        # Returns: {item_code: {tax_description: {tax_rate, tax_amount, included_in_print_rate}}}

        for row in doc.items:
            try:
                tax_rate = 0.0
                tax_amount = 0.00
                included_in_print_rate = 0
                
                # Get tax_category from Item Tax Template
                if row.get("item_tax_template"):
                    row.tax_category = frappe.db.get_value(
                        "Item Tax Template", row.item_tax_template, "tax_category", cache=True
                    )

                if row.item_code and itemised_tax.get(row.item_code):
                    # Sum up all taxes for this item
                    for d, tax in itemised_tax.get(row.item_code).items():
                        tax_rate += tax.get('tax_rate', 0)
                        tax_amount += tax.get("tax_amount", 0)
                        included_in_print_rate += tax.get("included_in_print_rate", 0)

                row.tax_rate = flt(tax_rate, row.precision("tax_rate"))

                if included_in_print_rate:
                    row.line_extension_amount = flt(row.amount / ((row.tax_rate / 100) + 1), 2)
                    taxable_amount = flt(row.amount / ((row.tax_rate / 100) + 1), 2)
                    qty = flt(row.get("qty") or 0)
                    if qty != 0:
                        row.price_amount = flt(taxable_amount / qty, 2)
                    else:
                        row.price_amount = 0.0
                    row.tax_amount = flt(row.amount - taxable_amount, 2)
                    original_net_total = doc.net_total + (doc.get("discount_amount", 0.00) or 0.00)
                    row.total_amount = row.amount
                else:
                    row.price_amount = row.rate
                    row.line_extension_amount = flt(row.amount, 2)
                    taxable_amount = flt(row.net_amount, 2)
                    row.tax_amount = flt(row.line_extension_amount * (row.tax_rate / 100), 2)
                    original_net_total = doc.net_total
                    row.total_amount = flt((row.line_extension_amount + row.tax_amount), 2)

                row.item_discount = flt(
                    (doc.discount_amount) * taxable_amount / original_net_total, 2
                ) if doc.get("discount_amount") else 0.00
            except Exception as e:
                frappe.log_error(
                    title=f"Failed to process item {row.idx}",
                    message=f"Item: {row.item_code}\nError: {str(e)}\n{traceback.format_exc()}"
                )
                row.tax_rate = 0.0
                row.tax_amount = 0.0
                raise frappe.ValidationError("Tax calculation failed. Check Error Log.")
    except Exception as e:
        log_and_throw_error(
            operation="update_itemised_tax_data (sales)",
            document_name=doc.name,
            exception=e
        )


def _calculate_purchase_invoice_item_taxes(doc):
    """
    Calculate per-item tax data for Purchase Invoice.
    Populates custom fields: tax_category, price_amount, line_extension_amount,
    item_discount, tax_rate, tax_amount, total_amount.
    """
    try:
        itemised_tax = get_itemised_tax(doc.taxes)

        for row in doc.items:
            try:
                tax_rate = 0.0
                tax_amount = 0.00
                included_in_print_rate = 0

                if row.get("item_tax_template"):
                    row.tax_category = frappe.db.get_value(
                        "Item Tax Template", row.item_tax_template, "tax_category", cache=True
                    )

                if row.item_code and itemised_tax.get(row.item_code):
                    for d, tax in itemised_tax.get(row.item_code).items():
                        tax_rate += tax.get('tax_rate', 0)
                        tax_amount += tax.get("tax_amount")
                        included_in_print_rate += tax.get("included_in_print_rate")

                row.tax_rate = flt(tax_rate, row.precision("tax_rate"))

                if included_in_print_rate:
                    row.line_extension_amount = flt(row.amount / ((row.tax_rate / 100) + 1), 2)
                    taxable_amount = flt(row.amount / ((row.tax_rate / 100) + 1), 2)
                    qty = flt(row.get("qty") or 0)
                    if qty != 0:
                        row.price_amount = flt(taxable_amount / qty, 2)
                    else:
                        row.price_amount = 0.0
                    row.tax_amount = flt(row.amount - taxable_amount, 2)
                    original_net_total = doc.net_total + (doc.get("discount_amount", 0.00) or 0.00)
                    row.total_amount = row.amount
                else:
                    row.price_amount = row.rate
                    row.line_extension_amount = flt(row.amount, 2)
                    taxable_amount = flt(row.net_amount, 2)
                    row.tax_amount = flt(row.line_extension_amount * (row.tax_rate / 100), 2)
                    original_net_total = doc.net_total
                    row.total_amount = flt((row.line_extension_amount + row.tax_amount), 2)

                row.item_discount = flt(
                    (doc.discount_amount) * taxable_amount / original_net_total, 2
                ) if doc.get("discount_amount") else 0.00
            except Exception as e:
                frappe.log_error(
                    title=f"Failed to process purchase item {row.idx}",
                    message=f"Item: {row.item_code}\nError: {str(e)}\n{traceback.format_exc()}"
                )
                row.tax_rate = 0.0
                row.tax_amount = 0.0
                raise frappe.ValidationError("Tax calculation failed. Check Error Log.")
    except Exception as e:
        log_and_throw_error(
            operation="update_itemised_tax_data (purchase)",
            document_name=doc.name,
            exception=e
        )



def get_itemised_tax(taxes):

	itemised_tax = {}
	for tax in taxes:
		if getattr(tax, "category", None) and tax.category == "Valuation":
			continue

		item_tax_map = json.loads(tax.item_wise_tax_detail) if tax.item_wise_tax_detail else {}

		if item_tax_map:
			for item_code, tax_data in item_tax_map.items():
				itemised_tax.setdefault(item_code, frappe._dict())

				tax_rate = 0.0
				tax_amount = 0.0

				if isinstance(tax_data, list):
					tax_rate = flt(tax_data[0])
					tax_amount = flt(tax_data[1])
				else:
					tax_rate = flt(tax_data)

				itemised_tax[item_code][tax.description] = frappe._dict(dict(
                    tax_rate=tax_rate, 
                    tax_amount=tax_amount , 
                    included_in_print_rate=tax.included_in_print_rate , 
                    tax_account = tax.account_head
                ))

	return itemised_tax