# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""Advance Payment Report: each prepayment chain of Sales Invoices and the advance it still holds.

A chain starts at an Initial Prepayment. Each invoice names the one before it in previous_prepayment,
and a return names the invoice it reverses in return_against. Advance-side invoices add their taxable
amount to the chain's balance and settlements take off their deducted_taxable_amount, as
CustomSalesInvoice posts them to the advance account. Amounts are in company currency; deductions
and returns are stored negative, and only the formatter puts them in parentheses.

Sales Invoices are read rather than the Prepayment Invoice records: those exist only once ZATCA
accepted the invoice, outlive a cancelled invoice, and held whole-number percentages before the
precision fix.

execute() reads; build_report() and everything below it work on plain rows, which is what the tests feed.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Max
from frappe.utils import flt, getdate
from frappe.utils.nestedset import get_descendants_of

INITIAL_PREPAYMENT = "Initial Prepayment"
FINAL_ADJUSTMENT = "Final Adjustment"
ADVANCE_TYPES = (INITIAL_PREPAYMENT, "Prepayment")
SETTLEMENT_TYPES = ("Adjustment", FINAL_ADJUSTMENT)
CHAIN_TYPES = ADVANCE_TYPES + SETTLEMENT_TYPES

FULL_CHAIN = "Full Chain"
SINGLE_TYPE = "Single Type"
APPROACH_TYPES = {"Prepayment": ADVANCE_TYPES, "Adjustment": SETTLEMENT_TYPES}

OPEN = "Open"
CLOSED = "Closed"

# Matches the Sales Invoice adjustment_percentage field (setup/customizations.py).
PERCENTAGE_PRECISION = 9
CHART_CUSTOMERS = 10


def execute(filters=None):
    filters = parse_filters(filters)
    return build_report(
        get_invoices(filters),
        filters,
        frappe.get_cached_value("Company", filters.company, "default_currency"),
        frappe.get_precision("Sales Invoice", "base_net_total") or 2,
    )


def parse_filters(filters):
    filters = frappe._dict(filters or {})
    filters.from_date, filters.to_date = getdate(filters.from_date), getdate(filters.to_date)
    filters.approach = filters.approach or FULL_CHAIN

    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date must be on or before To Date."))
    if filters.approach == SINGLE_TYPE and filters.invoice_type not in CHAIN_TYPES:
        frappe.throw(
            _("Choose an Invoice Type from {0} for the Single Type approach.").format(
                ", ".join(_(name) for name in CHAIN_TYPES)
            )
        )

    filters.customer_groups = with_descendants("Customer Group", filters.customer_group)
    filters.cost_centers = with_descendants("Cost Center", filters.cost_center)
    return filters


def with_descendants(doctype, name):
    if not name:
        return ()
    return (name, *get_descendants_of(doctype, name, ignore_permissions=True))


def get_invoices(filters):
    """Every submitted chain invoice of the company, whatever its date: a chain is linked whole
    before the period cuts it, so a backdated invoice never loses its parent."""
    invoice = frappe.qb.DocType("Sales Invoice")
    item = frappe.qb.DocType("Sales Invoice Item")
    item_sales_order = (
        frappe.qb.from_(item)
        .select(Max(item.sales_order))
        .where((item.parent == invoice.name) & (item.parenttype == "Sales Invoice"))
    )

    query = (
        frappe.qb.from_(invoice)
        .select(
            invoice.name,
            invoice.posting_date,
            invoice.creation,
            invoice.customer,
            invoice.customer_name,
            invoice.customer_group,
            invoice.currency,
            invoice.sales_invoice_type,
            invoice.is_return,
            invoice.return_against,
            invoice.previous_prepayment,
            invoice.prepayment_sales_order,
            item_sales_order.as_("item_sales_order"),
            invoice.cost_center,
            invoice.project,
            invoice.base_net_total,
            invoice.deducted_taxable_amount,
            invoice.deducted_tax_amount,
            invoice.adjustment_percentage,
            invoice.clearance_or_reporting,
        )
        .where(invoice.company == filters.company)
        .where(invoice.docstatus == 1)
        .where(invoice.sales_invoice_type.isin(CHAIN_TYPES))
    )
    if filters.customer:
        query = query.where(invoice.customer == filters.customer)
    if filters.currency:
        query = query.where(invoice.currency == filters.currency)

    return query.run(as_dict=True)


def build_report(invoices, filters, currency, precision=2):
    chains = [chain for chain in build_chains(invoices, filters, precision) if chain_in_scope(chain, filters)]
    return (
        get_columns(filters.approach),
        get_rows(chains, filters, currency, precision),
        None,
        get_chart(chains, currency),
        get_summary(chains, currency, precision),
    )


# ====================================================================================================
# CHAINS


def build_chains(invoices, filters, precision=2):
    chains = (build_chain(members, filters, precision) for members in link_chains(invoices))
    return [chain for chain in chains if chain]


def link_chains(invoices):
    """The invoices split into chains, each in link order from its root, the chains in root date order.

    Link order beats posting date, so a backdated Adjustment still follows the advance it consumes.
    An invoice whose parent is missing (cancelled, or never sent) roots a chain of its own rather than
    being dropped.
    """
    names = {row.name for row in invoices}
    children = defaultdict(list)
    roots = []
    for row in sorted(invoices, key=lambda row: (getdate(row.posting_date), str(row.creation or ""), row.name)):
        parent = row.return_against if row.is_return else row.previous_prepayment
        if parent in names:
            children[parent].append(row)
        else:
            roots.append(row)

    def walk(row):
        return [row, *(member for child in children[row.name] for member in walk(child))]

    return [walk(root) for root in roots]


def build_chain(members, filters, precision=2):
    """The chain as of To Date, or None when it has no invoice by then. Each member gets its signed
    deductions and the balance after it; the opening is what the invoices before From Date left."""
    rows = [row for row in members if getdate(row.posting_date) <= filters.to_date]
    if not rows:
        return None

    balance = 0.0
    for row in rows:
        row.advance = _round(advance_amount(row), precision)
        row.deducted_taxable = _round(signed_deduction(row, row.deducted_taxable_amount), precision)
        row.deducted_vat = _round(signed_deduction(row, row.deducted_tax_amount), precision)
        row.balance_delta = _round(row.advance + row.deducted_taxable, precision)
        balance = row.balance = _round(balance + row.balance_delta, precision)
        row.signed_percentage = _round(-signed_deduction(row, row.adjustment_percentage), PERCENTAGE_PRECISION)

    def total(selected):
        return _round(sum(row.balance_delta for row in selected), precision)

    during = [row for row in rows if getdate(row.posting_date) >= filters.from_date]
    status = chain_status(rows)
    return frappe._dict(
        root=rows[0],
        invoices=rows,
        sales_order=next(filter(None, map(invoice_sales_order, rows)), None),
        opening=total(row for row in rows if getdate(row.posting_date) < filters.from_date),
        advanced=total(row for row in during if row.sales_invoice_type in ADVANCE_TYPES),
        deducted=_round(-total(row for row in during if row.sales_invoice_type in SETTLEMENT_TYPES), precision),
        total_deducted=_round(-total(row for row in rows if row.sales_invoice_type in SETTLEMENT_TYPES), precision),
        balance=balance,
        remaining_percentage=_round(100 - sum(row.signed_percentage for row in rows), PERCENTAGE_PRECISION),
        status=status,
        days_since_last_invoice=None
        if status == CLOSED
        else (filters.to_date - max(getdate(row.posting_date) for row in rows)).days,
    )


def advance_amount(row):
    if row.sales_invoice_type not in ADVANCE_TYPES:
        return 0.0
    return flt(row.base_net_total)


def signed_deduction(row, amount):
    """A settlement's deduction as it moves the advance: negative, and positive on its return.

    Prepayments carry deducted_* too, but the client fills them with the running total of the
    advances before them, and CustomSalesInvoice deducts nothing for them, so they count as zero.
    """
    if row.sales_invoice_type not in SETTLEMENT_TYPES:
        return 0.0
    amount = abs(flt(amount))
    return amount if row.is_return else -amount


def invoice_sales_order(row):
    return row.prepayment_sales_order or row.item_sales_order


def chain_status(rows):
    """Closed while a Final Adjustment stands; returning it reopens the chain."""
    returned = {row.return_against for row in rows if row.is_return}
    closed = any(
        row.sales_invoice_type == FINAL_ADJUSTMENT and not row.is_return and row.name not in returned for row in rows
    )
    return CLOSED if closed else OPEN


def _round(value, precision):
    # Float noise such as -2e-13 rounds to -0.0, which would print as a negative zero.
    return flt(value, precision) or 0.0


# ====================================================================================================
# SELECTION
# Only a chain's first invoices carry its Sales Order, so Sales Order and Customer Group always match
# on the whole chain. Cost Center and Project can change along it: a chain matches if any invoice
# does, and a flat row only on its own value.


def in_period(row, filters):
    return filters.from_date <= getdate(row.posting_date) <= filters.to_date


def chain_in_scope(chain, filters):
    """A chain the period touches (open at From Date, or invoiced inside it) that the filters match."""
    rows = chain.invoices
    return (
        (chain.opening != 0 or any(in_period(row, filters) for row in rows))
        and (not filters.sales_order or any(invoice_sales_order(row) == filters.sales_order for row in rows))
        and (not filters.customer_groups or any(row.customer_group in filters.customer_groups for row in rows))
        and (not filters.cost_centers or any(row.cost_center in filters.cost_centers for row in rows))
        and (not filters.project or any(row.project == filters.project for row in rows))
    )


def row_in_scope(row, filters):
    types = (filters.invoice_type,) if filters.approach == SINGLE_TYPE else APPROACH_TYPES.get(filters.approach)
    return (
        in_period(row, filters)
        and row.sales_invoice_type in (types or CHAIN_TYPES)
        and (not filters.cost_centers or row.cost_center in filters.cost_centers)
        and (not filters.project or row.project == filters.project)
    )


# ====================================================================================================
# OUTPUT


def get_columns(approach):
    """The tree shows each chain's state on its own row; a flat row names its chain instead."""
    is_tree = approach == FULL_CHAIN

    def column(fieldname, label, fieldtype, width, options=None, **extra):
        return {"fieldname": fieldname, "label": _(label), "fieldtype": fieldtype, "options": options, "width": width, **extra}

    def amount(fieldname, label, width=130):
        return column(fieldname, label, "Currency", width, "company_currency")

    chain_state = [
        column("remaining_percentage", "Remaining %", "Percent", 130, precision=PERCENTAGE_PRECISION),
        column("status", "Status", "Data", 90),
        column("days_since_last_invoice", "Days Since Last Invoice", "Int", 110),
    ]
    return [
        column("invoice", "Invoice", "Link", 160, "Sales Invoice"),
        column("posting_date", "Date", "Date", 100),
        column("customer", "Customer", "Link", 180, "Customer"),
        column("invoice_type", "Type", "Data", 150),
        *([] if is_tree else [column("chain", "Chain", "Link", 140, "Sales Invoice")]),
        amount("advance", "Advance"),
        amount("deducted_taxable", "Deducted Taxable"),
        amount("deducted_vat", "Deducted VAT", 120),
        column("adjustment_percentage", "Adjustment %", "Percent", 130, precision=PERCENTAGE_PRECISION),
        amount("balance", "Advance Balance", 140),
        *(chain_state if is_tree else []),
        column("cost_center", "Cost Center", "Link", 150, "Cost Center"),
        column("project", "Project", "Link", 120, "Project"),
        column("currency", "Currency", "Link", 80, "Currency"),
        column("sales_order", "Sales Order", "Link", 140, "Sales Order"),
        column("zatca_status", "ZATCA Status", "Data", 110),
    ]


def get_rows(chains, filters, currency, precision=2):
    # The datatable treats the data as a tree once any row has an indent, so flat rows carry none.
    if filters.approach != FULL_CHAIN:
        return [
            invoice_row(chain, row, currency)
            for chain in chains
            for row in chain.invoices
            if row_in_scope(row, filters)
        ]

    rows = []
    for chain in chains:
        rows.append(chain_row(chain, currency, precision))
        rows += [
            {
                **invoice_row(chain, row, currency),
                "parent_chain": chain.root.name,
                "indent": 1,
                "out_of_range": int(getdate(row.posting_date) < filters.from_date),
            }
            for row in chain.invoices
        ]
    return rows


def invoice_row(chain, row, currency):
    invoice_type = _(row.sales_invoice_type)
    return {
        "invoice": row.name,
        "posting_date": row.posting_date,
        "customer": row.customer,
        "invoice_type": _("{0} (Return)").format(invoice_type) if row.is_return else invoice_type,
        "chain": chain.root.name,
        "advance": row.advance,
        "deducted_taxable": row.deducted_taxable,
        "deducted_vat": row.deducted_vat,
        "adjustment_percentage": row.signed_percentage,
        "balance": row.balance,
        "cost_center": row.cost_center,
        "project": row.project,
        "currency": row.currency,
        "sales_order": invoice_sales_order(row),
        "zatca_status": row.clearance_or_reporting,
        "company_currency": currency,
    }


def chain_row(chain, currency, precision=2):
    def total(fieldname, digits=precision):
        return _round(sum(flt(row.get(fieldname)) for row in chain.invoices), digits)

    root = chain.root
    return {
        "invoice": root.name,
        "posting_date": root.posting_date,
        "customer": root.customer,
        "invoice_type": _("Chain"),
        "chain": root.name,
        "advance": total("advance"),
        "deducted_taxable": total("deducted_taxable"),
        "deducted_vat": total("deducted_vat"),
        "adjustment_percentage": total("signed_percentage", PERCENTAGE_PRECISION),
        "balance": chain.balance,
        "remaining_percentage": chain.remaining_percentage,
        "status": _(chain.status),
        "status_indicator": "orange" if chain.status == OPEN else "green",
        "days_since_last_invoice": chain.days_since_last_invoice,
        "currency": root.currency,
        "sales_order": chain.sales_order,
        "company_currency": currency,
        "indent": 0,
    }


def get_summary(chains, currency, precision=2):
    """A roll-forward of the advance account over the chains in scope, whatever the approach."""
    opening = _round(sum(chain.opening for chain in chains), precision)
    advanced = _round(sum(chain.advanced for chain in chains), precision)
    deducted = _round(sum(chain.deducted for chain in chains), precision)
    open_chains = sum(chain.status == OPEN for chain in chains)

    def amount_card(label, value):
        return {"label": _(label), "value": value, "datatype": "Currency", "currency": currency}

    return [
        amount_card("Opening Advance Balance", opening),
        amount_card("Advances Invoiced in Period", advanced),
        amount_card("Advances Deducted in Period", deducted),
        amount_card("Closing Advance Balance", _round(opening + advanced - deducted, precision)),
        {"label": _("Open Chains"), "value": _("{0} of {1}").format(open_chains, len(chains)), "datatype": "Data"},
    ]


def get_chart(chains, currency):
    """The customers holding the most unearned advance, deducted against remaining."""
    remaining, deducted, names = defaultdict(float), defaultdict(float), {}
    for chain in chains:
        customer = chain.root.customer
        remaining[customer] += chain.balance
        deducted[customer] += chain.total_deducted
        names[customer] = chain.root.customer_name or customer

    top = sorted((c for c in remaining if remaining[c] > 0), key=lambda c: (-remaining[c], c))[:CHART_CUSTOMERS]
    if not top:
        return None

    return {
        "data": {
            "labels": [names[customer] for customer in top],
            "datasets": [
                {"name": _("Deducted"), "values": [deducted[customer] for customer in top]},
                {"name": _("Remaining"), "values": [remaining[customer] for customer in top]},
            ],
        },
        "type": "bar",
        "barOptions": {"stacked": 1},
        "fieldtype": "Currency",
        "options": "currency",
        "currency": currency,
    }
