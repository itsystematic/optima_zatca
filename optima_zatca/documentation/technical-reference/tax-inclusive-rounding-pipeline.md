# Tax-Inclusive Rounding Pipeline

## The Problem

When an item price **includes tax** (`included_in_print_rate = True`), a fundamental rounding
conflict arises between two valid methods of computing the tax amount. This document traces
the complete tax calculation pipeline, identifies where each rounding decision is made, and
explains why a 0.01 discrepancy appears in certain amounts (e.g., 310 SAR at 15% VAT).

---

## 1. The Mathematical Impossibility

Given a tax-inclusive amount of **310.00 SAR** at **15% VAT**:

```
Net = 310 / 1.15 = 269.565217...
Net (rounded to 2 dp) = 269.57
```

Two legitimate approaches to compute the tax:

| Approach | Formula | Result | Net + Tax |
|----------|---------|--------|-----------|
| **Multiplication** | 269.57 x 0.15 | **40.44** | 310.01 |
| **Subtraction** | 310.00 - 269.57 | **40.43** | 310.00 |

**It is mathematically impossible for all three values (net=269.57, tax=40.44, gross=310.00)
to be simultaneously true.** Two of the three must agree; one will always be off by 0.01 for
amounts where the division does not produce a clean decimal.

### When Does This Occur?

The issue occurs when `gross / (1 + rate)` produces a value where the third decimal place
causes the second decimal to round **up**, creating a net amount that, when multiplied back
by the rate, overshoots the original gross.

Common trigger amounts at 15% VAT include: 310, 315, 320, 325, 510, 710, etc.

Amounts like 230, 345, 460, 575 divide cleanly and do not exhibit this issue.

---

## 2. ERPNext Core Tax Pipeline

### Stage 1: Net Amount Calculation

**File**: `erpnext/controllers/taxes_and_totals.py` - `determine_exclusive_rate()`

For `included_in_print_rate` items, ERPNext back-calculates the net amount:

```python
item.net_amount = flt(amount / (1 + cumulated_tax_fraction), item.precision("net_amount"))
item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate"))
```

For 310 SAR: `net_amount = flt(310 / 1.15, 2) = 269.57`

### Stage 2: Tax Amount Calculation (Multiplication Method)

**File**: `erpnext/controllers/taxes_and_totals.py` - `get_current_tax_amount()`

ERPNext computes tax per item using the **multiplication method**:

```python
# Line 510
current_tax_amount = (tax_rate / 100.0) * item.net_amount
# = 0.15 * 269.57 = 40.4355
```

This value is stored (unrounded) in `item_wise_tax_detail`:
```json
{"item_code": [15.0, 40.4355]}
```

### Stage 3: Tax Totals and Rounding

**File**: `erpnext/controllers/taxes_and_totals.py` - `round_off_totals()`

```python
tax.tax_amount = flt(tax.tax_amount, tax.precision("tax_amount"))
# flt(40.4355, 2) = 40.44
```

The cumulative total on the tax row:
```python
tax.total = flt(net_total + tax_amount) = flt(269.57 + 40.44) = 310.01
```

### Stage 4: Grand Total Adjustment

**File**: `erpnext/controllers/taxes_and_totals.py` - `adjust_grand_total_for_inclusive_tax()`

ERPNext detects the discrepancy and computes a correction factor:

```python
diff = self.doc.total + non_inclusive_tax_amount - flt(last_tax.total, ...)
# diff = 310.00 + 0 - 310.01 = -0.01

if abs(diff) <= (5.0 / 10 ** tax_precision):
    self.grand_total_diff = diff  # stores -0.01
```

### Stage 5: Final Totals

**File**: `erpnext/controllers/taxes_and_totals.py` - `calculate_totals()`

```python
self.doc.grand_total = flt(last_tax.total) + grand_total_diff
# = 310.01 + (-0.01) = 310.00  (CORRECTED)

self.doc.total_taxes_and_charges = flt(grand_total - net_total - grand_total_diff, ...)
# = flt(310.00 - 269.57 - (-0.01)) = 40.44  (NOT CORRECTED)
```

### Summary of ERPNext Stored Values

| Field | Value | Corrected? |
|-------|-------|------------|
| `grand_total` | 310.00 | Yes (via grand_total_diff) |
| `net_total` | 269.57 | N/A (original calculation) |
| `total_taxes_and_charges` | 40.44 | No (multiplication method) |
| `tax.tax_amount` | 40.44 | No |
| `tax.total` | 310.01 | No (visible in tax table UI) |
| `item_wise_tax_detail` | 40.4355 | Raw, unrounded |

### GL Entry Handling

When the invoice is submitted:

| Entry | Account | Amount |
|-------|---------|--------|
| Debit | Expense | 269.57 |
| Debit | Tax | 40.44 |
| Credit | Supplier/Customer | 310.00 |
| Credit | **Round-off Account** | **0.01** (auto-generated) |

ERPNext's `make_round_off_gle()` in `erpnext/accounts/general_ledger.py` automatically
detects the debit/credit imbalance and creates a round-off entry. The `outstanding_amount`
is based on `grand_total` (310.00), so a full payment should clear it.

---

## 3. Optima ZATCA Per-Item Calculation (Subtraction Method)

### Current Implementation

**File**: `optima_zatca/zatca/itemised_tax.py`

For `included_in_print_rate` items, Optima uses the **subtraction method**:

```python
row.line_extension_amount = flt(row.amount / ((row.tax_rate / 100) + 1), 2)
# = flt(310 / 1.15, 2) = 269.57

taxable_amount = flt(row.amount / ((row.tax_rate / 100) + 1), 2)
# = 269.57

row.tax_amount = flt(row.amount - taxable_amount, 2)
# = flt(310.00 - 269.57, 2) = 40.43

row.total_amount = row.amount
# = 310.00
```

### Per-Item Consistency Check

```
line_extension_amount + tax_amount = total_amount
269.57 + 40.43 = 310.00  (CONSISTENT)
```

### Why the Subtraction Method?

The subtraction method ensures that per-line amounts are always internally consistent:
`net + tax = gross` holds exactly. This is a requirement for UBL 2.1 invoice line validation,
where `RoundingAmount` (per-line gross) must equal `LineExtensionAmount + TaxAmount`.

---

## 4. ZATCA XML Builder Reconciliation

### Document-Level Tax Adjustment

**File**: `optima_zatca/zatca/classes/invoice.py` - `_validate_and_adjust_tax_amount()`

The XML builder detects and corrects the ERPNext rounding mismatch at the document level:

```python
net_total = 269.57
tax_amount = 40.44  # from ERPNext total_taxes_and_charges
grand_total = 310.00

calculated_total = net_total + tax_amount  # = 310.01
difference = grand_total - calculated_total  # = -0.01

adjusted_tax = tax_amount + difference  # = 40.44 + (-0.01) = 40.43
```

This ensures the ZATCA XML satisfies: `TaxExclusiveAmount + TaxAmount = TaxInclusiveAmount`.

### Final ZATCA XML Values

| XML Element | Source | Value |
|---|---|---|
| **Document Level** | | |
| `TaxExclusiveAmount` | ERPNext `net_total` | 269.57 |
| `TaxInclusiveAmount` | ERPNext `grand_total` | 310.00 |
| `TaxTotal/TaxAmount` | Adjusted by `_validate_and_adjust_tax_amount` | 40.43 |
| `PayableAmount` | Calculated from tax-inclusive | 310.00 |
| **Per Line** | | |
| `LineExtensionAmount` | Optima `line_extension_amount` | 269.57 |
| `TaxAmount` | Optima `tax_amount` (subtraction) | 40.43 |
| `RoundingAmount` | Optima `total_amount` | 310.00 |
| `PriceAmount` | Optima `price_amount` | 269.57 |

### Consistency Verification

```
Document:  269.57 + 40.43 = 310.00 = TaxInclusiveAmount    OK
Per-line:  269.57 + 40.43 = 310.00 = RoundingAmount         OK
Cross:     sum(LineExtensionAmount) = TaxExclusiveAmount     OK
Cross:     sum(per-item TaxAmount) = Document TaxAmount      OK
```

---

## 5. The Discrepancy Summary

| Layer | Tax Amount | Method | Consistent with gross? |
|-------|-----------|--------|----------------------|
| ERPNext tax table | 40.44 | Multiplication | No (310.01) |
| ERPNext `total_taxes_and_charges` | 40.44 | From tax table | No |
| ERPNext `grand_total` | 310.00 | Adjusted | Yes |
| Optima per-item | 40.43 | Subtraction | Yes (310.00) |
| ZATCA XML doc-level | 40.43 | Adjusted | Yes (310.00) |
| ZATCA XML per-line | 40.43 | Subtraction | Yes (310.00) |

**The discrepancy is contained to the ERPNext UI display** (tax table showing 310.01 and 40.44).
The ZATCA XML is internally consistent at both document and line levels.

---

## 6. Affected Scenarios

### Confirmed Working

- Single-item invoices with tax-inclusive pricing
- ZATCA XML generation and validation
- GL entry balancing (via auto round-off)

### Potential Issues

- **Multi-item invoices**: When multiple items have rounding errors, the cumulative difference
  may exceed 0.01, and the per-item subtraction totals may diverge further from the tax table
- **Outstanding amount**: In edge cases, if the grand_total correction does not persist correctly
  (e.g., frontend/backend desync during save), the 0.01 may appear as outstanding
- **User confusion**: The tax table UI showing 310.01 and 40.44 while items show 40.43

---

## 7. System Settings That Affect Rounding

| Setting | Location | Current Value | Effect |
|---------|----------|--------------|--------|
| Rounding Method | System Settings | Commercial Rounding | 0.5 always rounds up |
| Round Row Wise Tax | Accounts Settings | Off (0) | Tax rounded at total level, not per-item |
| Currency Precision | System Settings | 2 | All amounts rounded to 2 decimal places |

### Rounding Methods Available in Frappe

- **Banker's Rounding**: 0.5 rounds to nearest even (Python `decimal.ROUND_HALF_EVEN`)
- **Banker's Rounding (legacy)**: 0.5 always rounds up (Frappe's historical default)
- **Commercial Rounding**: 0.5 always rounds away from zero

All three methods produce the same result for 40.4355 -> 40.44 (since the third decimal is 5
followed by non-zero digits).

---

## 8. Related Files

| File | Role |
|------|------|
| `erpnext/controllers/taxes_and_totals.py` | ERPNext core tax calculation engine |
| `frappe/utils/data.py` | `flt()` and `rounded()` functions |
| `erpnext/accounts/general_ledger.py` | GL entry creation and round-off |
| `optima_zatca/zatca/itemised_tax.py` | Per-item tax calculation (regional override) |
| `optima_zatca/zatca/classes/invoice.py` | ZATCA XML builder with rounding adjustment |
| `optima_zatca/zatca/classes/xml.py` | XML element creation |

---

## 9. Appendix: Reproduction Script

```python
# Run in bench console to reproduce the rounding issue
from frappe.utils import flt

amount = 310.0
rate = 15.0

net = amount / (1 + rate / 100)
net_rounded = flt(net, 2)

tax_multiply = flt(net_rounded * (rate / 100), 2)
tax_subtract = flt(amount - net_rounded, 2)

print(f"Gross: {amount}")
print(f"Net (raw): {net}")
print(f"Net (rounded): {net_rounded}")
print(f"Tax (multiplication): {tax_multiply}")
print(f"Tax (subtraction): {tax_subtract}")
print(f"Multiplication check: {net_rounded} + {tax_multiply} = {net_rounded + tax_multiply}")
print(f"Subtraction check: {net_rounded} + {tax_subtract} = {net_rounded + tax_subtract}")
```

Output:
```
Gross: 310.0
Net (raw): 269.5652173913044
Net (rounded): 269.57
Tax (multiplication): 40.44
Tax (subtraction): 40.43
Multiplication check: 269.57 + 40.44 = 310.01
Subtraction check: 269.57 + 40.43 = 310.0
```
