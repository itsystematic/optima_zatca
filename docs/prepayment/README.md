# Prepayment & Adjustment — Docs

Everything about advance-payment invoicing under ZATCA — prepayment invoices (UBL `386`) and
the adjustment chain that draws them down to 100%.

| Document | For | What it covers |
|----------|-----|----------------|
| [user-guide.md](user-guide.md) | Accountants & implementers | The invoice types, how a prepayment chain works, the Final Adjustment auto-fill, what gets validated |
| [reference.md](reference.md) | Developers | The `validate_prepayments` rule set, `adjustment_percentage` vs `max_adjustment_limit`, the **9-dp precision invariant**, and `CustomSalesInvoice` GL |

The model spans `events/prepayment.py` (validation), `overrides/sales_invoice.py` (GL), and the
**Prepayment Invoice** / **Prepayment Details** doctypes. Invoice-type codes are in
[Concepts](../concepts.md).
