# Configuration — Setup Guide

A guide for implementers to configuring a site for ZATCA **after** the app is installed and a
device is [onboarded](../onboarding/user-guide.md). For how these records get created at install
time, see [install.md](install.md).

---

## 1. Company

Each ZATCA company needs, on the **Company** doctype and its address:

| Where | Field | Value |
|-------|-------|-------|
| Company | `company_name_in_arabic` | The legal Arabic name (required) |
| Company | `tax_id` | 15-digit VAT number (starts and ends with `3`) |
| Company Address | Building Number | 4 digits |
| Company Address | Street, District, City | Text |
| Company Address | Postal Code | 5 digits |
| Company Address | Country | Saudi Arabia |

The address must be a complete **Saudi National Address** — ZATCA rejects the CSR otherwise.

---

## 2. Zatca Main Settings

The global toggles (single doctype):

| Setting | Effect |
|---------|--------|
| **Phase** | Phase 1 (QR only) vs Phase 2 (clearance/reporting) |
| **Manual submit** | Off = auto-submit the invoice after a successful send; On = you submit it yourself |
| **Enable cancel invoice** | Allow cancelling an already-finalized ZATCA invoice (off by default) |
| **Enable delete invoice** | Allow deleting an already-finalized ZATCA invoice (off by default) |

The two override toggles are the escape hatch behind the
[cancel/delete block](../phase-one-qr/reference.md#cancel--delete-guards).

---

## 3. VAT accounts & tax templates

ZATCA needs per-line VAT, which requires an **Item Tax Template** carrying the VAT rate and a
tax **category** (see [Concepts](../concepts.md) for S / Z / E / O):

```
Item Tax Template  →  "Standard VAT 15%"
    company        =  <your company>
    tax_category   =  S           (Standard rate)
    taxes          =  [ VAT account @ 15% ]
```

The installer's `create_complete_vat_system` seeds the VAT accounts and templates when it can;
the **Zatca Vat Setting** doctype maps which accounts are the sales/purchase VAT accounts. Items
must then carry a tax template (the Item `taxes` table is mandatory on a ZATCA site).

---

## 4. Invoice types

The seeded **Sales Invoice Type** records drive the prepayment model:

| Type | Use |
|------|-----|
| **Normal** | Standard invoice |
| **Initial Prepayment** | First advance against a Sales Order |
| **Prepayment** | Subsequent advance |
| **Adjustment** | Settles part of an advance on delivery |
| **Final Adjustment** | Settles the remainder |

See [prepayment/user-guide.md](../prepayment/user-guide.md) for how they chain together.
