# Per-Item Tax & Rounding

Developer reference for **ZATCA-compliant per-item tax** — the regional override that computes
per-line tax breakdowns for the UBL XML, and the tax-inclusive rounding behavior that follows
from it. This is an internal subsystem (no user guide); the tax-account *configuration* an
implementer touches lives in [setup](../setup/). Terminology in [Concepts](../concepts.md).

Override: `optima_zatca/zatca/itemised_tax.py` → `update_itemised_tax_data(doc)`

---

## The regional override

ZATCA needs tax broken out **per invoice line**, which ERPNext doesn't do natively. `hooks.py`
swaps ERPNext's function for Saudi Arabia only:

```python
regional_overrides = {
    "Saudi Arabia": {
        "erpnext.controllers.taxes_and_totals.update_itemised_tax_data":
            "optima_zatca.zatca.itemised_tax.update_itemised_tax_data"
    }
}
```

It routes by doctype — Purchase Invoice to its own handler, everything else (Sales Invoice,
Quotation, Sales Order, Delivery Note, POS Invoice) to the sales handler — and populates custom
fields on each item row:

| Field | Type | Meaning | Visible on PI |
|-------|------|---------|:---:|
| `tax_category` | Link → Tax Category | S / Z / E / O classification | No |
| `price_amount` | Float | Unit price before tax | No |
| `line_extension_amount` | Float | Net taxable amount for the line | No |
| `item_discount` | Float | Proportional discount for the line | No |
| `tax_rate` | Float | Combined tax rate (%) | **Yes** |
| `tax_amount` | Currency | Tax for the line | **Yes** |
| `total_amount` | Currency | Line total incl. tax | **Yes** |
| `tax_exemption` | Link → Tax Exemption | Exemption reason (user input) | No |

These map into the UBL 2.1 line: `line_extension_amount` → `LineExtensionAmount`,
`price_amount` → `PriceAmount`, `tax_amount` → `TaxAmount`, `tax_category` → `TaxCategory`,
`item_discount` → per-line `AllowanceCharge`.

---

## Per-item calculation

### Tax-exclusive pricing (`included_in_print_rate = False`, standard B2B)

| Field | Formula |
|-------|---------|
| `line_extension_amount` | `amount` (net) |
| `tax_amount` | `line_extension_amount × rate/100` |
| `total_amount` | `line_extension_amount + tax_amount` |

*100 SAR @ 15% → net 100.00, tax 15.00, total 115.00.*

### Tax-inclusive pricing (`included_in_print_rate = True`, retail B2C) — subtraction method

```python
row.line_extension_amount = flt(row.amount / ((row.tax_rate / 100) + 1), 2)   # net
row.tax_amount            = flt(row.amount - taxable_amount, 2)                # gross − net
row.total_amount          = row.amount                                        # gross
```

*115 SAR @ 15% → net 100.00, tax 15.00, total 115.00.*

**Why subtraction?** It guarantees `net + tax = gross` **exactly** per line, which UBL 2.1 line
validation requires (`RoundingAmount = LineExtensionAmount + TaxAmount`).

**On failure**, the handler logs the item + traceback to Error Log, sets safe defaults
(`tax_rate = tax_amount = 0.0`), and raises `ValidationError` — it never silently corrupts a line.

---

## The tax-inclusive rounding trap

For certain tax-inclusive amounts, two *valid* ways to compute the tax disagree by 0.01. Take
**310.00 SAR @ 15%**:

```
Net = 310 / 1.15 = 269.5652…  → rounded 269.57
```

| Method | Formula | Tax | net + tax |
|--------|---------|-----|-----------|
| **Multiplication** (ERPNext) | `269.57 × 0.15` | **40.44** | 310.01 |
| **Subtraction** (Optima) | `310.00 − 269.57` | **40.43** | 310.00 |

It is **mathematically impossible** for net = 269.57, tax = 40.44, and gross = 310.00 to all
hold at once — two of the three agree, one is off by 0.01. Trigger amounts at 15%: 310, 315,
320, 325, 510, 710… Amounts like 230, 345, 460, 575 divide cleanly and don't.

Where each layer lands:

| Layer | Tax | Consistent with 310.00 gross? |
|-------|-----|:---:|
| ERPNext tax table / `total_taxes_and_charges` | 40.44 (multiplication) | No (shows 310.01) |
| ERPNext `grand_total` | — | Yes (corrected via `grand_total_diff`) |
| Optima per-item | 40.43 (subtraction) | Yes |
| ZATCA XML (document + line) | 40.43 | Yes |

**The discrepancy is contained to the ERPNext tax-table UI** (40.44 / 310.01). The ZATCA XML is
internally consistent at both document and line levels — the XML builder reconciles the
document-level tax so `TaxExclusiveAmount + TaxAmount = TaxInclusiveAmount`. ERPNext's own
`make_round_off_gle` balances the GL with an automatic 0.01 round-off entry, and
`outstanding_amount` tracks the corrected `grand_total`, so a full payment clears cleanly.

> **A proposed alternative exists but is not implemented.** Making the per-item tax match
> ERPNext's tax table instead (authoritative-source + remainder distribution) is written up in
> [rounding-reconciliation-proposal.md](rounding-reconciliation-proposal.md) — **pending tech-lead
> approval**. It trades per-line consistency for document-level consistency; read it before
> touching `itemised_tax.py`.

### Rounding settings that matter

| Setting | Location | Effect |
|---------|----------|--------|
| Rounding Method | System Settings | Commercial Rounding (0.5 away from zero) is the default |
| Round Row Wise Tax | Accounts Settings | Off → tax rounded at total level, not per row |
| Currency Precision | System Settings | 2 dp for all amounts |

### Reproduce it

```python
# bench console
from frappe.utils import flt
amount, rate = 310.0, 15.0
net = flt(amount / (1 + rate / 100), 2)                 # 269.57
print("multiplication:", flt(net * rate / 100, 2))      # 40.44 → 310.01
print("subtraction:   ", flt(amount - net, 2))          # 40.43 → 310.00
```

---

## Related source

| File | Role |
|------|------|
| `zatca/itemised_tax.py` | Per-item tax calculation (this override) |
| `zatca/classes/invoice.py` / `invoice_payload_builder.py` | UBL builder + document-level tax reconciliation |
| `setup/customizations.py` | The item-row custom field definitions |
| `erpnext/controllers/taxes_and_totals.py` | ERPNext core tax engine (the multiplication side) |
