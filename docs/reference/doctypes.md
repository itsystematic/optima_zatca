# DocType Reference

Developer reference — the doctypes `optima_zatca` defines, grouped by purpose, with the domain
that owns each. Field-level detail lives with the owning domain.

---

## Onboarding & device configuration

| DocType | Kind | Purpose | Domain |
|---------|------|---------|--------|
| **Optima Zatca Setting** | Normal | Per-device onboarding config + full CSR/CSID state machine (one per Commercial Register) | [onboarding](../onboarding/reference.md) |
| **Commercial Register** | Normal | A company's device/branch; `is_main` / `is_default` flags (one default per company) | [onboarding](../onboarding/reference.md) |
| **Commercial Registers For Zatca** | Child | Multi-device rows on a company | onboarding |
| **Registration Type** | Normal | Taxpayer registration classification used in the CSR | onboarding |

## Global settings

| DocType | Kind | Purpose | Domain |
|---------|------|---------|--------|
| **Zatca Main Settings** | Single | Global toggles — `phase` (Phase 1 / Phase 2), `enable_cancel_invoice`, `enable_delete_invoice`, manual-submit | [submission](../submission/reference.md) · [phase-one-qr](../phase-one-qr/reference.md) |

## Prepayment

| DocType | Kind | Purpose | Domain |
|---------|------|---------|--------|
| **Prepayment Invoice** | Normal | Persisted advance-payment record; `adjustment_percentage` mirror (precision 9) | [prepayment](../prepayment/reference.md) |
| **Prepayment Details** | Child | Chain rows read back by the client remaining-percentage math | prepayment |

## VAT / tax configuration

| DocType | Kind | Purpose | Domain |
|---------|------|---------|--------|
| **Zatca Vat Setting** | Normal | VAT account mapping | [tax](../tax/reference.md) · [setup](../setup/) |
| **Zatca Vat Sales Account** | Child | Output-VAT account rows | tax |
| **Zatca Vat Purchase Account** | Child | Input-VAT account rows | tax |
| **Tax Exemption** | Normal | Exemption reason (per-line `tax_exemption` on items) | tax |

## Reference data & audit

| DocType | Kind | Purpose | Domain |
|---------|------|---------|--------|
| **Sales Invoice Type** | Normal | The invoice-type list (Normal, Initial Prepayment, Prepayment, Adjustment, Final Adjustment) | prepayment / submission |
| **Optima Zatca Logs** | Normal | One record per ZATCA API call — request/response XML, hashes, QR, status. In `ignore_links_on_delete` | [submission](../submission/reference.md) |

---

Invoice-type codes (388 / 386 …) and tax categories (S / Z / E / O) are defined in
[Concepts](../concepts.md).
