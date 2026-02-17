"""
Arabic-friendly Money in Words Formatting
==========================================

This module provides customized money-to-words conversion specifically designed
for Arabic/Saudi localization, with proper word order and spacing.

Key differences from Frappe's default:
- Word order: Amount before currency (e.g., "One Hundred SAR" not "SAR One Hundred")
- Extra spacing for Arabic text rendering
- Simplified translation wrapping
"""

import frappe
from frappe.utils import flt, cint, get_number_format_info, in_words, Optional


def custom_money_in_words(
    number: str, main_currency: Optional[str] = None, fraction_currency: Optional[str] = None
):
    """
    Returns string in words with currency and fraction currency.
    Customized for Arabic/Saudi compliance with proper word order and spacing.

    Args:
        number: The amount to convert
        main_currency: Main currency code (e.g., "SAR")
        fraction_currency: Fraction currency name (e.g., "Halala")

    Returns:
        Formatted money in words string
    """
    from frappe.utils import get_defaults

    _ = frappe._

    try:
        # note: `flt` returns 0 for invalid input and we don't want that
        number = float(number)
    except ValueError:
        return ""

    number = flt(number)
    if number < 0:
        return ""

    d = get_defaults()
    if not main_currency:
        main_currency = d.get("currency", "INR")
    if not fraction_currency:
        fraction_currency = frappe.db.get_value(
            "Currency", main_currency, "fraction", cache=True
        ) or _("Cent")

    number_format = (
        frappe.db.get_value("Currency", main_currency, "number_format", cache=True)
        or frappe.db.get_default("number_format")
        or "#,###.##"
    )

    fraction_length = get_number_format_info(number_format)[2]

    n = "%.{0}f".format(fraction_length) % number

    numbers = n.split(".")
    main, fraction = numbers if len(numbers) > 1 else [n, "00"]

    if len(fraction) < fraction_length:
        zeros = "0" * (fraction_length - len(fraction))
        fraction += zeros

    in_million = True
    if number_format == "#,##,###.##":
        in_million = False

    # 0.00
    if main == "0" and fraction in ["00", "000"]:
        out = "{0} {1}".format(_(main_currency), _("Zero"))
    # 0.XX
    elif main == "0":
        out = _(in_words(fraction, in_million).title()) + "  " + _(fraction_currency)
    else:
        # Main amount with currency (amount before currency for Arabic)
        out = _(in_words(main, in_million).title()) + "  " + _(main_currency)
        if cint(fraction):
            out = (
                out
                + " "
                + _("and")
                + "  "
                + _(in_words(_(fraction), in_million).title())
                + "  "
                + _(fraction_currency)
            )

    return out + "  " + _("only") + " " + "."


def set_custom_money_in_words(doc, method=None):
    """
    Document hook to override in_words fields with Arabic-friendly formatting.
    This is called automatically via Frappe's doc_events hooks.

    Args:
        doc: The document being saved
        method: Hook method name (not used)
    """
    # Skip if not relevant document type or doesn't have the fields
    if not doc.meta.get_field("in_words") and not doc.meta.get_field("base_in_words"):
        return

    try:
        # Handle Sales/Purchase documents (Invoice, Order, Receipt, Delivery Note, Quotation)
        if hasattr(doc, "grand_total") and doc.meta.get_field("in_words"):
            # Check if document has is_rounded_total_disabled method
            if hasattr(doc, "is_rounded_total_disabled"):
                amount = abs(
                    doc.grand_total
                    if doc.is_rounded_total_disabled()
                    else doc.rounded_total
                )
            else:
                amount = abs(doc.grand_total)

            doc.in_words = custom_money_in_words(amount, doc.currency)

        if hasattr(doc, "base_grand_total") and doc.meta.get_field("base_in_words"):
            # Get company currency
            company_currency = frappe.get_cached_value(
                "Company", doc.company, "default_currency"
            )

            if hasattr(doc, "is_rounded_total_disabled"):
                base_amount = abs(
                    doc.base_grand_total
                    if doc.is_rounded_total_disabled()
                    else doc.base_rounded_total
                )
            else:
                base_amount = abs(doc.base_grand_total)

            doc.base_in_words = custom_money_in_words(base_amount, company_currency)

        # Handle Payment Entry specifically
        if doc.doctype == "Payment Entry":
            company_currency = frappe.get_cached_value(
                "Company", doc.company, "default_currency"
            )

            if doc.payment_type == "Pay":
                base_amount = (
                    abs(doc.base_paid_amount) if hasattr(doc, "base_paid_amount") else 0
                )
                amount = abs(doc.paid_amount) if hasattr(doc, "paid_amount") else 0
                currency = (
                    doc.paid_to_account_currency
                    if hasattr(doc, "paid_to_account_currency")
                    else company_currency
                )
            elif doc.payment_type == "Receive":
                base_amount = (
                    abs(doc.base_received_amount)
                    if hasattr(doc, "base_received_amount")
                    else 0
                )
                amount = (
                    abs(doc.received_amount) if hasattr(doc, "received_amount") else 0
                )
                currency = (
                    doc.paid_from_account_currency
                    if hasattr(doc, "paid_from_account_currency")
                    else company_currency
                )
            else:
                return

            if doc.meta.get_field("base_in_words"):
                doc.base_in_words = custom_money_in_words(base_amount, company_currency)
            if doc.meta.get_field("in_words"):
                doc.in_words = custom_money_in_words(amount, currency)

        # Handle Journal Entry specifically
        if doc.doctype == "Journal Entry" and doc.meta.get_field(
            "total_amount_in_words"
        ):
            company_currency = frappe.get_cached_value(
                "Company", doc.company, "default_currency"
            )
            amt = flt(doc.total_debit) - flt(doc.total_credit)
            doc.total_amount_in_words = custom_money_in_words(amt, company_currency)

        # Handle Salary Slip (HRMS)
        if doc.doctype == "Salary Slip":
            if doc.meta.get_field("total_in_words") and hasattr(doc, "rounded_total"):
                company_currency = frappe.get_cached_value(
                    "Company", doc.company, "default_currency"
                )
                doc.total_in_words = custom_money_in_words(
                    doc.rounded_total,
                    doc.currency if hasattr(doc, "currency") else company_currency,
                )

            if doc.meta.get_field("base_total_in_words") and hasattr(
                doc, "base_rounded_total"
            ):
                company_currency = frappe.get_cached_value(
                    "Company", doc.company, "default_currency"
                )
                doc.base_total_in_words = custom_money_in_words(
                    doc.base_rounded_total, company_currency
                )

    except Exception as e:
        # Log the error but don't break the document save
        frappe.log_error(
            title=f"Error in set_custom_money_in_words for {doc.doctype}",
            message=frappe.get_traceback(),
        )
