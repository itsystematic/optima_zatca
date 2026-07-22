# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`optima_zatca` is a Frappe/ERPNext v15 app implementing Saudi Arabia's **ZATCA (Fatoora) e-invoicing** — Phase 1 (QR-only simplified invoices) and Phase 2 (full clearance/reporting). It turns an ERPNext Sales Invoice into signed UBL 2.1 XML, submits it to ZATCA's API, and records the full audit trail.

This app lives inside a larger Frappe bench at `/home/erpnext/fawaz`. The bench-level `CLAUDE.md` (one directory up) documents the other apps, the multiple sites, and general `bench` usage. **This bench hosts many sites — ask which site the user is on before running any `bench --site` command.** The rest of this file is specific to `optima_zatca`.

> Note: `.github/copilot-instructions.md` is an older AI-agent guide. It is mostly accurate but predates a refactor — trust this file where they disagree. Notably, the onboarding wizard is **React**, not Vue, and the submission logic now lives in `submission_workflow.py`.

## Commands

```bash
# Frappe-dependent tests (run inside a real site context)
bench --site <site> run-tests --app optima_zatca
bench --site <site> run-tests --app optima_zatca --module optima_zatca.zatca.tests.test_invoice

# ZATCA unit tests use unittest.mock only (no live Frappe DB, no HTTP) —
# so they also run under plain pytest from the bench root or app root:
python -m pytest apps/optima_zatca/optima_zatca/zatca/tests/ -v

# After Python changes
bench restart
# After hooks.py / fixture / custom-field changes
bench --site <site> clear-cache
bench --site <site> migrate

# Build the app's bundled desk JS (public/js) after editing it
bench build --app optima_zatca

# Onboarding wizard (React SPA) — see "Onboarding frontend" below
cd zatca-onboarding && yarn install && yarn dev      # dev server
yarn build                                            # emits to assets, base-pathed
```

## Submission Architecture

The Sales-Invoice-to-ZATCA path is deliberately layered so the decision logic is pure and testable, separate from the Frappe/HTTP side effects.

```
public/js/sales_invoice/zatca_buttons.js   "Send to ZATCA" button → frappe.call
        │
zatca/invoice.py  send_to_zatca(sales_invoice_name)   ← the ONLY @frappe.whitelist entry point
        │        (thin wrapper: loads the doc, delegates)
        ▼
zatca/submission_workflow.py  submit_sales_invoice_to_zatca(sales_invoice)   ← real orchestrator
        │   Validate → build+sign XML → POST → decide outcome → update invoice → log → post-success
        │
        ├── validate:  classes/validate.py   ZatcaInvoiceValidate
        ├── build XML: classes/invoice.py     ZatcaInvoiceData  (facade)
        │                 ├─ classes/invoice_context.py   InvoiceContextLoader → LoadedInvoiceContext
        │                 │      (fetches company / customer / addresses / settings)
        │                 ├─ classes/invoice_payload_builder.py  ZatcaInvoicePayloadBuilder (UBL dict)
        │                 └─ classes/xml.py    ZatcaXmlGenerator (lxml → hash → sign → QR)
        ├── transport: zatca/api.py           HTTP to clearance / reporting / compliance / onboarding
        └── log:       zatca/logs.py          make_action_log → "Optima Zatca Logs" doctype
```

**Two hard constraints when editing this path:**

1. `send_to_zatca(sales_invoice_name)` in `zatca/invoice.py` is the public whitelisted signature. **Do not change its name or arguments** — the frontend and other apps call it. Keep new helpers private (`_` prefix).
2. `submission_workflow.py` separates **pure decision functions** (`_decide_submission_outcome`, `_decide_invoice_status`, `_decide_log_status`, `_decide_post_success_policy`, `_is_success_status_code`, …) from **side-effect functions** (`_submit_to_zatca_api`, `_update_invoice_document`, `_log_action`, `_execute_post_success_actions`). The tests exercise the pure functions directly. Preserve that split — put branching logic in a `_decide_*` function, not inline in a side-effecting one.

### Clearance vs Reporting
- **Standard invoices (B2B)** → *clearance* endpoint; ZATCA must approve before the invoice is valid.
- **Simplified invoices (B2C)** → *reporting* endpoint; submitted and reported asynchronously.

`_decide_post_success_policy` also governs whether the invoice auto-submits after a successful send (gated by the manual-submit setting).

## Wiring (hooks.py)

- `override_doctype_class`: `Sales Invoice` → `overrides.sales_invoice.CustomSalesInvoice` (prepayment GL entries). Must subclass ERPNext's `SalesInvoice`.
- `doc_events` on `Sales Invoice`: `validate` → `validate_prepayments`, plus `on_submit` / `before_cancel` / `on_trash` in `events/sales_invoice.py`.
- `regional_overrides` (Saudi Arabia): replaces ERPNext's `update_itemised_tax_data` with `zatca/itemised_tax.py` for ZATCA-compliant per-line tax.
- `app_include_js`: the three `public/js/sales_invoice/*.js` modules are loaded **in dependency order** — `prepayment.js` (constants) first, then `pos_payments.js`, then `zatca_buttons.js`. Preserve that order.
- `website_route_rules` + `www/zatca-onboarding.html` serve the onboarding SPA at `/zatca-onboarding`.
- `after_install` / `after_app_install` run installers; migrations run the patches in `optima_zatca/patches.txt` (prepayment doctypes/fields, roles, print formats, item-tax setup).

## Key DocTypes

- **Optima Zatca Setting** — per-Commercial-Register config (certificates, endpoints, environment).
- **Zatca Main Settings** (single) — global toggles, including Phase 1 vs Phase 2.
- **Commercial Register** — multi-device support for one company.
- **Optima Zatca Logs** — one record per ZATCA API call (request/response XML, hashes, QR). Listed in `ignore_links_on_delete`.
- **Prepayment Invoice** / **Prepayment Details** — advance-payment linkage for adjustment invoices.
- **Zatca Vat Setting** / **Zatca Vat Sales Account** / **Zatca Vat Purchase Account** — VAT account mapping.

## Invoice types (prepayment model)

- **Normal** — standard invoice, UBL type code `388`.
- **Initial Prepayment / Prepayment** — advance payment, code `386`.
- **Adjustment / Final Adjustment** — references a prepayment via `deducted_taxable_amount` / `deducted_grand_total`. Client-side math is in `public/js/sales_invoice/prepayment.js`; server-side GL handling is in `CustomSalesInvoice`.

### How the Final Adjustment percentage is derived (and the precision trap)

A **Final Adjustment** settles whatever is left of a prepayment chain. Its `adjustment_percentage` is **auto-filled and locked** to the remaining share:

```
remaining_percentage   = 100 − Σ(adjustment_percentage of every earlier prepayment in the chain)
adjustment_percentage  = remaining_percentage      # for Final Adjustment
```

`Σ` is computed in `calculateRemainingFromUsedPercentages` (`public/js/sales_invoice/prepayment.js`), summing the rows loaded from `get_prepayment_details` — i.e. the **persisted `Prepayment Invoice` records**, not the live Sales Invoice values.

**Precision invariant (one number, four places — keep them all at 9 dp):**

| Layer | Where |
|---|---|
| Sales Invoice custom fields | `setup/customizations.py` → `PERCENTAGE_PRECISION = 9` |
| Server validation | `events/sales_invoice.py` → `PERCENTAGE_PRECISION = 9` |
| Client limit check | `public/js/sales_invoice.js` → `toFixed(9)` |
| **Persisted mirrors** | `Prepayment Invoice` **and** `Prepayment Details` — `adjustment_percentage` / `remaining_percentage` **precision `"9"`** |

The mirrors are the subtle one. They were historically `precision "0"` (stored as `decimal(21,0)`), so each stored adjustment truncated to a whole number; the Final Adjustment then summed integers and landed on e.g. **36** instead of **35.646222780**. The Sales Invoice fields were already 9 dp — the loss was purely at the `Prepayment Invoice` write in `_build_prepayment_payload` (`zatca/prepayment_invoice.py`). Raising the mirror precision fixes it **going forward only**: percentages already truncated in existing rows cannot be recovered.

- **`max_adjustment_limit`** ("Max Limit Percentage") is a *different* number — `grand_total × 100 / total_grands`, computed from currency totals, not from the percentages. It is accurate at 9 dp and is not affected by the mirror-precision issue.

## Crypto & PDF dependencies

Declared in `pyproject.toml`, installed via `bench setup requirements`: `cryptography` (signing), `asn1` (certificate/CSR encoding), `qrcode` (Phase-1 TLV QR), `pikepdf` (embedding invoice XML into a PDF/A-3 file — see `zatca/pdfa3.py`). CSR/key generation lives in `zatca/keys.py` (`GenerateCSR`) and `zatca/setup.py` (onboarding: CSR → compliance CSID → sample invoices → production CSID).

## Testing rules

- All ZATCA tests live in `optima_zatca/zatca/tests/` and use **`unittest.mock` only** — no live Frappe context, no real HTTP, no DB. This is why they run under bare `pytest`.
- When adding submission logic, add or extend a `_decide_*` pure function and unit-test it directly rather than testing the whole orchestrator with a live doc.

## Onboarding frontend (`zatca-onboarding/`)

A standalone **React + Vite** SPA (Ant Design, Redux Toolkit, `frappe-react-sdk`, socket.io) — the guided ZATCA device-onboarding wizard. It builds with `--base=/assets/optima_zatca/zatca-onboarding/` and its HTML entry is copied to `optima_zatca/www/zatca-onboarding.html` (see the `copy-html-entry` script). Lint with `yarn lint` (ESLint 9 flat config). It is served by Frappe via the `website_route_rules` hook, not by bench's asset bundler.
