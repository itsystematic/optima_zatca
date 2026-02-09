# Tax Rounding Reconciliation - Implementation Plan

**Status**: Pending tech lead approval
**Priority**: Medium
**Related**: [Tax-Inclusive Rounding Pipeline](./tax-inclusive-rounding-pipeline.md)

---

## Problem Statement

For tax-inclusive items, ERPNext's per-item tax (multiplication method) differs from Optima's
per-item tax (subtraction method) by 0.01 on certain amounts. This causes:

1. **UI inconsistency**: Tax table shows 40.44, item row shows 40.43
2. **Potential outstanding amount issues**: In multi-item or edge-case scenarios
3. **Audit confusion**: Two different "correct" tax amounts on the same document

---

## Proposed Solution: Authoritative Source + Remainder Distribution

### Core Principle

Use ERPNext's `item_wise_tax_detail` as the **single source of truth** for per-item tax
amounts, then derive all other values from it to ensure consistency across the tax table,
item rows, and ZATCA XML.

### Implementation Steps

#### Step 1: Use `item_wise_tax_detail` Tax Amount Directly

**File**: `optima_zatca/zatca/itemised_tax.py`

Currently, for `included_in_print_rate` items:
```python
# CURRENT: Subtraction method (diverges from tax table)
row.tax_amount = flt(row.amount - taxable_amount, 2)
```

Proposed change:
```python
# PROPOSED: Use ERPNext's computed tax amount from item_wise_tax_detail
if included_in_print_rate:
    row.tax_amount = flt(tax_amount, 2)  # tax_amount from get_itemised_tax()
    row.line_extension_amount = flt(row.amount - row.tax_amount, 2)
    taxable_amount = row.line_extension_amount
    # ... rest of calculation
```

**Effect**: Per-item tax (40.44) now matches ERPNext's tax table.
`line_extension_amount` becomes 310.00 - 40.44 = 269.56 (differs from ERPNext `net_amount`
of 269.57 by 0.01).

#### Step 2: Remainder Distribution on Last Item

After computing all items, reconcile any rounding remainder against the document totals.
The "last item adjustment" pattern is already used by ERPNext core for "Actual" tax type
distribution (see `taxes_and_totals.py` line 406-409).

```python
# After the item loop, reconcile sums against document totals
total_item_tax = sum(flt(row.tax_amount, 2) for row in doc.items)
total_item_net = sum(flt(row.line_extension_amount, 2) for row in doc.items)

# Reconcile tax
expected_tax = flt(doc.total_taxes_and_charges, 2)
tax_diff = flt(expected_tax - total_item_tax, 2)
if abs(tax_diff) <= 0.05 and doc.items:
    last_item = doc.items[-1]
    last_item.tax_amount = flt(last_item.tax_amount + tax_diff, 2)

# Reconcile net (for included_in_print_rate)
expected_net = flt(doc.net_total, 2)
net_diff = flt(expected_net - total_item_net, 2)
if abs(net_diff) <= 0.05 and doc.items:
    last_item = doc.items[-1]
    last_item.line_extension_amount = flt(last_item.line_extension_amount + net_diff, 2)
```

#### Step 3: Adjust ZATCA XML Builder

**File**: `optima_zatca/zatca/classes/invoice.py`

Update `_get_tax_exclusive_amount()` to use the sum of per-item `line_extension_amount`
values instead of ERPNext's `net_total`:

```python
def _get_tax_exclusive_amount(self) -> str:
    """Get tax exclusive amount from sum of per-item line extensions."""
    if self.included_in_print_rate:
        items = self.sales_invoice.get("items", [])
        amount = sum(
            abs(flt(self._safe_float(item.get("line_extension_amount")), 2))
            for item in items
        )
    else:
        amount = self.sales_invoice.get("net_total", 0)
    return f"{abs(flt(amount, 2)):.2f}"
```

Similarly, the document-level `TaxAmount` should use the sum of per-item tax amounts
(after remainder distribution) rather than `_validate_and_adjust_tax_amount()`.

---

## Expected Outcome

### For the 310 SAR Example (Single Item)

| Field | Before | After |
|-------|--------|-------|
| `tax_amount` (per-item) | 40.43 | 40.44 |
| `line_extension_amount` (per-item) | 269.57 | 269.56 |
| `total_amount` (per-item) | 310.00 | 310.00 |
| ERPNext tax table `tax_amount` | 40.44 | 40.44 |
| ERPNext `net_total` | 269.57 | 269.57 |

After remainder distribution:

| Field | Value |
|-------|-------|
| Per-item tax_amount | 40.44 (matches tax table) |
| Per-item line_extension_amount | 269.56 + 0.01 = 269.57 (reconciled to net_total) |
| Sum check | 269.57 + 40.44 = 310.01 (per-item), but total_amount = 310.00 |

**Note**: Per-line `line_extension + tax = total` will be off by 0.01 in the reconciled case.
This is the fundamental trade-off: either per-line consistency OR document-level consistency.

---

## Trade-off Analysis

### Approach A: Current (Subtraction Method)

```
Per-line: net + tax = total    -> 269.57 + 40.43 = 310.00  CONSISTENT
Document: sum(tax) = tax_total -> 40.43 != 40.44            INCONSISTENT
```

**Pros**: Per-line amounts always add up. ZATCA line-level validation passes.
**Cons**: Item tax differs from tax table. Confusing for users.

### Approach B: Proposed (Authoritative Source + Remainder)

```
Per-line: net + tax = total    -> 269.57 + 40.44 = 310.01  OFF BY 0.01
Document: sum(tax) = tax_total -> 40.44 == 40.44            CONSISTENT
```

**Pros**: Item tax matches tax table. Document-level sums match ERPNext. Less confusion.
**Cons**: Per-line amounts may be off by 0.01. More complex code.

### Approach C: Hybrid (Recommended)

Use the subtraction method for per-line consistency, but add a **validation warning** when
the item-level total diverges from the tax table. Keep `_validate_and_adjust_tax_amount()`
for ZATCA XML reconciliation.

```
Per-line: net + tax = total    -> 269.57 + 40.43 = 310.00  CONSISTENT
Document: adjusted_tax         -> 40.43                      CONSISTENT (via adjustment)
ZATCA XML: all checks pass     -> YES
Display: add note to tax table -> "Rounding adjustment: 0.01"
```

**Pros**: Minimal code change. Per-line and document consistency. ZATCA passes.
**Cons**: Tax table still shows 40.44/310.01 (ERPNext core, cannot change without patching).

---

## Recommendation

**Approach C (Hybrid)** is recommended as the safest path because:

1. It preserves the existing working ZATCA XML generation
2. It does not introduce new discrepancies at the per-line level
3. The `_validate_and_adjust_tax_amount()` already handles document-level reconciliation
4. The only visible issue (tax table showing 310.01) is an ERPNext core display behavior
   that would require an upstream patch or monkey-patch to resolve

### If per-item consistency with the tax table is required (Approach B):

The implementation is more involved and requires careful testing with:
- Multi-item invoices (different items, different tax rates)
- Mixed tax-inclusive and tax-exclusive items
- Invoices with discounts
- Multi-currency invoices
- Credit notes and returns

---

## Testing Plan

### Test Cases

1. **Single item, tax-inclusive, clean division**: 230 SAR at 15% (net=200, tax=30)
2. **Single item, tax-inclusive, rounding trigger**: 310 SAR at 15% (the reported case)
3. **Multi-item, tax-inclusive**: Two items at 310 + 115 SAR
4. **Multi-item, mixed pricing**: One inclusive, one exclusive
5. **With discount**: 310 SAR inclusive with 10% discount
6. **Multi-currency**: Foreign currency invoice with conversion rate
7. **Credit note**: Return against the 310 SAR invoice
8. **Zero-rated items**: Items with 0% tax mixed with 15% items

### Validation Criteria

For each test case, verify:
- [ ] Per-item: `line_extension_amount + tax_amount = total_amount` (within 0.01)
- [ ] Document: `sum(line_extension_amount) = TaxExclusiveAmount` (within 0.01)
- [ ] Document: `sum(tax_amount) = TaxAmount` (within 0.01)
- [ ] Document: `TaxExclusiveAmount + TaxAmount = TaxInclusiveAmount` (exact)
- [ ] ZATCA XML passes schema validation
- [ ] GL entries balance (with or without round-off entry)
- [ ] Payment of full amount results in 0.00 outstanding

---

## Files to Modify

| File | Change |
|------|--------|
| `optima_zatca/zatca/itemised_tax.py` | Per-item tax calculation logic |
| `optima_zatca/zatca/classes/invoice.py` | Document-level totals source |
| (Optional) `optima_zatca/zatca/classes/xml.py` | No changes expected |

---

## Timeline Estimate

- Approach C (Hybrid): Minimal changes, mostly documentation and a validation warning
- Approach B (Full reconciliation): Requires all 8 test cases, regression testing with
  existing ZATCA-submitted invoices, and careful rollout
