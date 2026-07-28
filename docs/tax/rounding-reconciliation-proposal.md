# Tax Rounding Reconciliation — Design Proposal

> **Status: Pending tech-lead approval — NOT implemented.** This is a design proposal, not a
> description of current behavior. The shipping behavior is the subtraction method documented in
> [reference.md](reference.md); read this only when evaluating a change to it.

**Priority:** Medium · **Related:** [Per-Item Tax & Rounding](reference.md)

---

## Problem

For tax-inclusive items, ERPNext's per-item tax (multiplication method) differs from Optima's
per-item tax (subtraction method) by 0.01 on certain amounts (e.g. 310 SAR @ 15%). This causes:

1. **UI inconsistency** — tax table shows 40.44, item row shows 40.43.
2. **Potential outstanding-amount issues** in multi-item or edge cases.
3. **Audit confusion** — two "correct" tax amounts on one document.

## Proposed solution — authoritative source + remainder distribution

Use ERPNext's `item_wise_tax_detail` as the single source of truth for per-item tax, then derive
everything else from it.

**Step 1 — take the tax amount from `item_wise_tax_detail`** (`zatca/itemised_tax.py`):

```python
# CURRENT: subtraction (diverges from tax table)
row.tax_amount = flt(row.amount - taxable_amount, 2)               # 40.43

# PROPOSED: ERPNext's computed tax
if included_in_print_rate:
    row.tax_amount = flt(tax_amount, 2)                            # 40.44 (matches table)
    row.line_extension_amount = flt(row.amount - row.tax_amount, 2)
```

**Step 2 — remainder distribution on the last item**, reconciling the summed per-item tax / net
against `total_taxes_and_charges` / `net_total` (the "last item adjustment" pattern ERPNext core
already uses for Actual-type tax):

```python
tax_diff = flt(flt(doc.total_taxes_and_charges, 2) - sum(flt(r.tax_amount, 2) for r in doc.items), 2)
if abs(tax_diff) <= 0.05 and doc.items:
    doc.items[-1].tax_amount = flt(doc.items[-1].tax_amount + tax_diff, 2)
# (mirror for line_extension_amount vs net_total)
```

**Step 3 — point the XML builder's document totals at the summed per-item values**
(`zatca/classes/invoice.py`) instead of ERPNext's `net_total`.

## Trade-off

| Approach | Per-line `net+tax=total` | Document `Σtax = tax_total` |
|----------|:---:|:---:|
| **A — current (subtraction)** | ✅ 269.57 + 40.43 = 310.00 | ❌ 40.43 ≠ 40.44 |
| **B — proposed (authoritative + remainder)** | ❌ off by 0.01 | ✅ 40.44 = 40.44 |
| **C — hybrid (recommended)** | ✅ | ✅ via existing doc-level adjustment |

This is the fundamental trade-off: **per-line consistency OR document-level consistency**, not
both, for trigger amounts.

## Recommendation — Approach C (hybrid)

Keep the subtraction method for per-line consistency and the existing document-level XML
reconciliation; add a validation **warning** when the item total diverges from the tax table. It
is the safest path: it preserves working ZATCA XML generation, introduces no new per-line
discrepancy, and the only visible artifact (tax table showing 310.01) is ERPNext core display
behavior that can't change without an upstream patch.

## If Approach B is chosen — test matrix

Regression-test with existing ZATCA-submitted invoices, plus: (1) clean division 230@15%,
(2) trigger 310@15%, (3) multi-item inclusive, (4) mixed inclusive/exclusive, (5) with discount,
(6) multi-currency, (7) credit note/return, (8) zero-rated mixed with 15%. For each, verify
per-line `net+tax=total` (±0.01), `Σline = TaxExclusiveAmount`, `Σtax = TaxAmount`,
`TaxExclusive + Tax = TaxInclusive` (exact), XML schema passes, GL balances, full payment → 0.00
outstanding.

**Files to modify:** `zatca/itemised_tax.py` (per-item logic), `zatca/classes/invoice.py`
(document totals source).
