# Per-Item Tax Calculation Logic

This document explains how Optima ZATCA calculates per-item tax data for Sales and Purchase documents.

## Overview

Optima ZATCA uses a **regional override** mechanism to replace ERPNext's default `update_itemised_tax_data` function with custom logic for Saudi Arabia. This function calculates per-item tax breakdowns and populates custom fields on each item row.

**Hook Configuration** (in `hooks.py`):
```python
regional_overrides = {
    'Saudi Arabia': {
        'erpnext.controllers.taxes_and_totals.update_itemised_tax_data': 
        'optima_zatca.zatca.invoice.update_itemised_tax_data'
    }
}
```

---

## Supported Document Types

| Document Type | Status | Item Table Visibility |
|--------------|--------|----------------------|
| Sales Invoice | ✅ Supported | Hidden (used for ZATCA XML) |
| Quotation | ✅ Supported | Hidden |
| Sales Order | ✅ Supported | Hidden |
| Delivery Note | ✅ Supported | Hidden |
| POS Invoice | ✅ Supported | Hidden |
| Purchase Invoice | ✅ Supported | **Visible** (tax_rate, tax_amount, total_amount) |

---

## Function Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  update_itemised_tax_data(doc)                                  │
│  Location: optima_zatca/zatca/invoice.py                        │
├─────────────────────────────────────────────────────────────────┤
│  Routes based on doctype:                                       │
│  - Purchase Invoice → _calculate_purchase_invoice_item_taxes()  │
│  - All others → _calculate_sales_document_item_taxes()          │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────┐    ┌─────────────────────────────┐
│ Purchase Invoice    │    │ Sales Invoice, Quotation,   │
│ Handler             │    │ Sales Order, Delivery Note, │
│                     │    │ POS Invoice Handler         │
└─────────────────────┘    └─────────────────────────────┘
```

---

## Calculation Steps

### Step 1: Extract Itemised Tax Data

The function first extracts per-item tax information from the document's `taxes` table:

```python
itemised_tax = get_itemised_tax(doc.taxes)
```

**Returns a dictionary structure:**
```python
{
    "ITEM-001": {
        "VAT 15%": {
            "tax_rate": 15.0,
            "tax_amount": 150.00,
            "included_in_print_rate": 0,
            "tax_account": "VAT - Output - Company"
        }
    },
    "ITEM-002": {
        "VAT 15%": {
            "tax_rate": 15.0,
            "tax_amount": 75.00,
            "included_in_print_rate": 1,
            "tax_account": "VAT - Output - Company"
        }
    }
}
```

### Step 2: Get Tax Category

For each item with an `item_tax_template`, fetch the associated tax category:

```python
row.tax_category = frappe.db.get_value(
    "Item Tax Template", 
    row.item_tax_template, 
    "tax_category", 
    cache=True
)
```

### Step 3: Aggregate Taxes Per Item

Sum all tax components for each item:

```python
for d, tax in itemised_tax.get(row.item_code).items():
    tax_rate += tax.get('tax_rate', 0)
    tax_amount += tax.get("tax_amount")
    included_in_print_rate += tax.get("included_in_print_rate")
```

### Step 4: Calculate Fields Based on Pricing Method

#### **Tax-Inclusive Pricing** (`included_in_print_rate = True`)

When prices already include tax (e.g., retail B2C pricing):

| Field | Formula | Description |
|-------|---------|-------------|
| `line_extension_amount` | `amount / ((tax_rate/100) + 1)` | Taxable base (net amount) |
| `taxable_amount` | Same as above | Used for discount calculation |
| `price_amount` | `taxable_amount / qty` | Unit price before tax |
| `tax_amount` | `amount - taxable_amount` | Extracted tax portion |
| `total_amount` | `amount` | Original amount (unchanged) |

**Example**: Item costs 115 SAR (inclusive of 15% VAT)
- `line_extension_amount` = 115 / 1.15 = **100.00 SAR**
- `tax_amount` = 115 - 100 = **15.00 SAR**
- `total_amount` = **115.00 SAR**

#### **Tax-Exclusive Pricing** (`included_in_print_rate = False`)

When prices exclude tax (standard B2B pricing):

| Field | Formula | Description |
|-------|---------|-------------|
| `price_amount` | `rate` | Item unit rate |
| `line_extension_amount` | `amount` | Net amount |
| `taxable_amount` | `net_amount` | Base for tax calculation |
| `tax_amount` | `line_extension_amount * (tax_rate/100)` | Calculated tax |
| `total_amount` | `line_extension_amount + tax_amount` | Grand total |

**Example**: Item costs 100 SAR (exclusive of 15% VAT)
- `line_extension_amount` = **100.00 SAR**
- `tax_amount` = 100 * 0.15 = **15.00 SAR**
- `total_amount` = 100 + 15 = **115.00 SAR**

### Step 5: Calculate Item Discount

If the document has a discount, distribute it proportionally across items:

```python
row.item_discount = (doc.discount_amount * taxable_amount) / original_net_total
```

---

## Custom Fields Reference

These custom fields are added to item child tables:

| Field Name | Field Type | Description | Visible (PI) |
|------------|-----------|-------------|--------------|
| `tax_category` | Link → Tax Category | Tax classification (Standard, Zero-rated, Exempt) | No |
| `price_amount` | Float | Unit price before tax | No |
| `line_extension_amount` | Float | Net taxable amount for the line | No |
| `item_discount` | Float | Proportional discount for this item | No |
| `tax_rate` | Float | Combined tax rate (%) | **Yes** |
| `tax_amount` | Currency | Tax amount for this line | **Yes** |
| `total_amount` | Currency | Line total including tax | **Yes** |
| `tax_exemption` | Link → Tax Exemption | Exemption reason (user input) | No |

*PI = Purchase Invoice*

---

## Error Handling

If tax calculation fails for any item, the system:

1. Logs the error to Error Log doctype with full traceback
2. Sets safe defaults (`tax_rate = 0.0`, `tax_amount = 0.0`)
3. Raises `ValidationError` to prevent silent data corruption

```python
except Exception as e:
    frappe.log_error(
        title=f"Failed to process item {row.idx}",
        message=f"Item: {row.item_code}\nError: {str(e)}\n{traceback.format_exc()}"
    )
    row.tax_rate = 0.0
    row.tax_amount = 0.0
    raise frappe.ValidationError("Tax calculation failed. Check Error Log.")
```

---

## Usage in ZATCA XML Generation

The calculated fields are used when generating UBL 2.1 XML for ZATCA submission:

- `line_extension_amount` → `<cbc:LineExtensionAmount>`
- `price_amount` → `<cbc:PriceAmount>`
- `tax_amount` → `<cbc:TaxAmount>`
- `tax_category` → `<cac:TaxCategory>` classification
- `item_discount` → `<cac:AllowanceCharge>` per line

---

## Related Files

- **Function Implementation**: `optima_zatca/zatca/invoice.py`
- **Custom Field Definitions**: `optima_zatca/patches/v15/setup_customizations.py`
- **Hook Configuration**: `optima_zatca/hooks.py`
- **Legacy Field Definitions**: `optima_zatca/utils.py`
