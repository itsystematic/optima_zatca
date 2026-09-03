# Prepayment & Adjustment

Developer reference for the **prepayment / adjustment invoice** model — the validation rules,
the percentage-precision invariant, and the GL handling. For the accountant workflow, see
[user-guide.md](user-guide.md).

The model lives across three seams:

| Concern | Where |
|---------|-------|
| `validate` rules | `optima_zatca/events/prepayment.py` → `validate_prepayments(doc, event)` |
| GL / accounting | `optima_zatca/overrides/sales_invoice.py` → `CustomSalesInvoice` |
| Prepayment Invoice record | `optima_zatca/zatca/prepayment_invoice.py` |
| Client-side math | `public/js/sales_invoice/prepayment.js` |

`CustomSalesInvoice` **subclasses** ERPNext's `SalesInvoice` (wired via `override_doctype_class`)
— keep that inheritance.

---

## Invoice types and UBL codes

Classified by the **Sales Invoice Type** link field:

| Type | UBL `InvoiceTypeCode` |
|------|-----------------------|
| Normal | `388` |
| Initial Prepayment / Prepayment | `386` |
| Adjustment / Final Adjustment | reference a prepayment via `deducted_taxable_amount` / `deducted_grand_total` |

Constants: `NORMAL_INVOICE_TYPE`, `INITIAL_PREPAYMENT_TYPE`, `ADJUSTMENT_TYPES`
(`events/prepayment.py`); `PREPAYMENT_TYPE_CODE = "386"` (`prepayment_invoice.py`).

---

## The validation rules

`validate_prepayments` dispatches on type and runs the relevant checks:

| Validator | Rule |
|-----------|------|
| `_validate_unique_initial_prepayment` | A Sales Order may carry **at most one** Initial Prepayment invoice |
| `_validate_prepayment_linkage` | A return must reference an **existing**, **not-yet-linked** Prepayment Invoice |
| `_validate_required_fields` | `adjustment_percentage`, `total_grands`, `grand_total` must be present |
| `_validate_adjustment_percentage_range` | Percentage must be between 0% and 100% |
| `_validate_deducted_totals` | `deducted_grand_total` (abs) may not exceed `grand_total` |
| `_validate_adjustment_percentage_limit` | Percentage may not exceed the remaining limit (below) |
| `_validate_pos_payment_for_adjustment` / `_validate_non_pos_payment_for_adjustment` | Deducted + paid may not exceed `grand_total` |

> **Assert business-rule messages against the `_validate_*` helpers, not `validate_prepayments`.**
> The wrapper re-raises `ValidationError` untouched but funnels *unexpected* exceptions through
> `log_and_throw_error` (generic message + Error Log row). See the app
> [CLAUDE.md](../../CLAUDE.md) "Testing rules".

---

## Two different "percentages" — don't confuse them

### `adjustment_percentage` — the share this invoice settles

For a **Final Adjustment** it is auto-filled and locked to the remainder:

```
remaining_percentage  = 100 − Σ(adjustment_percentage of every earlier prepayment in the chain)
adjustment_percentage = remaining_percentage
```

`Σ` is summed in `calculateRemainingFromUsedPercentages` (`prepayment.js`) over the **persisted
Prepayment Invoice** records, not the live Sales Invoice values.

### `max_adjustment_limit` ("Max Limit Percentage") — a currency-derived ceiling

```
max_adjustment_limit = grand_total × 100 / total_grands      # _calculate_max_adjustment_limit
```

Computed from currency totals (accurate at 9 dp), **not** from summed percentages — so it is
*not* affected by the mirror-precision issue below.

---

## The precision invariant (one number, four places — all 9 dp)

`adjustment_percentage` must be carried at **9 decimal places** everywhere, or a Final
Adjustment lands on the wrong remainder:

| Layer | Where |
|-------|-------|
| Sales Invoice custom fields | `setup/customizations.py` → `PERCENTAGE_PRECISION = 9` |
| Server validation | `events/prepayment.py` → `PERCENTAGE_PRECISION = 9` |
| Client limit check | `public/js/sales_invoice.js` → `toFixed(9)` |
| **Persisted mirrors** | **Prepayment Invoice** and **Prepayment Details** — precision `"9"` |

> **The mirror is the trap.** The Prepayment Invoice / Prepayment Details `adjustment_percentage`
> were historically precision `"0"` (`decimal(21,0)`), truncating each stored adjustment to a
> whole number; the Final Adjustment then summed integers and landed on e.g. **36** instead of
> **35.646222780**. The loss was purely at the `Prepayment Invoice` write in
> `_build_prepayment_payload` (`prepayment_invoice.py`). Raising the mirror precision fixes it
> **going forward only** — percentages already truncated in existing rows can't be recovered.

---

## GL handling

`CustomSalesInvoice` builds the prepayment/adjustment GL entries on top of ERPNext's Sales
Invoice posting. The adjustment invoices net the previously-recognized advance against the
final revenue using `deducted_taxable_amount` / `deducted_grand_total`. The **Prepayment
Invoice** and **Prepayment Details** doctypes persist the chain linkage that
`get_prepayment_details` reads back for the client-side remaining-percentage math.
