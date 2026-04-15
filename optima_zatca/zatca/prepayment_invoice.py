from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import frappe

from optima_zatca.zatca.utils import log_and_throw_error


PREPAYMENT_DOCTYPE = "Prepayment Invoice"
PREPAYMENT_TYPE_CODE = "386"
FINAL_ADJUSTMENT_TYPE = "Final Adjustment"
ADJUSTMENT_TYPE = "Adjustment"


@dataclass(frozen=True)
class PrepaymentChainState:
    """Capture the chain fields needed to persist a prepayment record."""

    has_previous_prepayment: bool
    previous_prepayment_invoice: str | None
    prepayment_type: str | None


@dataclass(frozen=True)
class CompanyCurrencyAmounts:
    """Keep company-currency totals together for payload creation."""

    grand_total: Any
    tax_amount: Any
    taxable_amount: Any


def create_prepayment_invoice(sales_invoice: Any, uuid: str) -> None:
    """Persist the linked prepayment document after a successful send."""
    try:
        chain_state = _resolve_chain_state(sales_invoice)
        _mark_related_prepayments(sales_invoice)

        prepayment_invoice = frappe.get_doc(
            _build_prepayment_payload(sales_invoice, uuid, chain_state)
        )
        prepayment_invoice.insert(ignore_permissions=True)
    except Exception as e:
        log_and_throw_error(
            operation="create prepayment invoice",
            document_name=sales_invoice.name,
            exception=e,
        )


def _build_prepayment_payload(
    sales_invoice: Any,
    uuid: str,
    chain_state: PrepaymentChainState,
) -> dict[str, Any]:
    """Assemble the prepayment document fields from the source invoice."""
    amounts = _get_company_currency_amounts(sales_invoice)

    return {
        "doctype": PREPAYMENT_DOCTYPE,
        "uuid": uuid,
        "percent": get_tax_rate_from_items(sales_invoice),
        "issue_time": format_issue_time(sales_invoice.posting_time),
        "prepayment_type_code": PREPAYMENT_TYPE_CODE,
        "id": sales_invoice.get("name"),
        "customer": sales_invoice.get("customer"),
        "currency": sales_invoice.get("currency"),
        "sales_invoice": sales_invoice.get("name"),
        "sales_order": _resolve_sales_order(sales_invoice),
        "is_return": sales_invoice.get("is_return"),
        "adjustment_percentage": _resolve_adjustment_percentage(sales_invoice),
        "issue_date": sales_invoice.get("posting_date"),
        "grand_total": amounts.grand_total,
        "tax_category": sales_invoice.get("tax_category"),
        "has_previous_prepayment": chain_state.has_previous_prepayment,
        "is_debit_note": sales_invoice.get("is_debit_note"),
        "prepayment_type": chain_state.prepayment_type,
        "previous_prepayment_invoice": chain_state.previous_prepayment_invoice,
        "tax_amount": amounts.tax_amount,
        "remaining_percentage": sales_invoice.get("remaining_percentage"),
        "taxable_amount": amounts.taxable_amount,
    }


def _resolve_chain_state(sales_invoice: Any) -> PrepaymentChainState:
    """Derive prepayment chain fields before persistence and mutations."""
    prepayment_type = sales_invoice.get("sales_invoice_type")
    previous_prepayment_invoice = sales_invoice.get("previous_prepayment")
    has_previous_prepayment = bool(previous_prepayment_invoice)

    if (
        sales_invoice.get("return_against")
        and sales_invoice.get("sales_invoice_type") == FINAL_ADJUSTMENT_TYPE
    ):
        prepayment_type = ADJUSTMENT_TYPE

    if sales_invoice.get("is_return"):
        has_previous_prepayment = True
        previous_prepayment_invoice = sales_invoice.get("return_against")

    return PrepaymentChainState(
        has_previous_prepayment=has_previous_prepayment,
        previous_prepayment_invoice=previous_prepayment_invoice,
        prepayment_type=prepayment_type,
    )


def _mark_related_prepayments(sales_invoice: Any) -> None:
    """Update linked prepayment rows so the chain stays consistent."""
    previous_prepayment = sales_invoice.get("previous_prepayment")
    if previous_prepayment:
        frappe.db.set_value(PREPAYMENT_DOCTYPE, previous_prepayment, "is_linked", 1)

    returned_prepayment = sales_invoice.get("return_against")
    if not returned_prepayment:
        return

    frappe.db.set_value(PREPAYMENT_DOCTYPE, returned_prepayment, "been_return", 1)
    frappe.db.set_value(PREPAYMENT_DOCTYPE, returned_prepayment, "is_linked", 1)

    if sales_invoice.get("sales_invoice_type") == FINAL_ADJUSTMENT_TYPE:
        frappe.db.set_value(
            PREPAYMENT_DOCTYPE,
            returned_prepayment,
            "prepayment_type",
            ADJUSTMENT_TYPE,
        )


def _get_company_currency_amounts(sales_invoice: Any) -> CompanyCurrencyAmounts:
    """Prefer company-currency totals so downstream math stays consistent."""
    return CompanyCurrencyAmounts(
        grand_total=sales_invoice.get("base_grand_total")
        or sales_invoice.get("grand_total"),
        tax_amount=sales_invoice.get("base_total_taxes_and_charges")
        or sales_invoice.get("total_taxes_and_charges"),
        taxable_amount=sales_invoice.get("base_net_total")
        or sales_invoice.get("net_total"),
    )


def _resolve_sales_order(sales_invoice: Any) -> str | None:
    """Prefer the explicit prepayment Sales Order over item-derived links."""
    prepayment_sales_order = sales_invoice.get("prepayment_sales_order")
    if prepayment_sales_order:
        return prepayment_sales_order

    items = sales_invoice.get("items") or []
    first_item = items[0] if items else {}
    return first_item.get("sales_order")


def _resolve_adjustment_percentage(sales_invoice: Any) -> Any:
    """Flip return percentages so persisted adjustments preserve intent."""
    adjustment_percentage = sales_invoice.get("adjustment_percentage")
    if sales_invoice.get("is_return"):
        return adjustment_percentage * -1

    return adjustment_percentage


def format_issue_time(posting_time: Any) -> str:
    """Normalize posting time to `HH:MM:SS` for prepayment persistence."""
    if not posting_time:
        return ""

    time_str = str(posting_time)
    if "." in time_str:
        time_str = time_str.split(".")[0]

    parts = time_str.split(":")
    if len(parts) >= 1:
        parts = [part.zfill(2) for part in parts]
        time_str = ":".join(parts)

    return time_str


def get_tax_rate_from_items(sales_invoice: Any) -> float:
    """Return the first item tax rate so the payload mirrors the invoice."""
    items = sales_invoice.get("items") or []
    return items[0].get("tax_rate", 0) if items else 0
