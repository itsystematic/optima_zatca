# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`optima_zatca` is a Frappe/ERPNext app implementing Saudi Arabia's **ZATCA (Fatoora) e-invoicing** — Phase 1 (QR-only simplified invoices) and Phase 2 (full clearance/reporting). It turns an ERPNext Sales Invoice into signed UBL 2.1 XML, submits it to ZATCA's API, and records the full audit trail. The `version-15` branch is the v15 line; the `version-16*` branches target Frappe/ERPNext 16.

The v15 line runs in the bench at `/home/erpnext/fawaz`, whose bench-level `CLAUDE.md` documents the other apps, the sites and general `bench` usage. The v16 line runs in `/home/erpnext/frappe-bench16`, which has no bench-level guide. **Both benches host many sites — ask which site the user is on before running any `bench --site` command.** The rest of this file is specific to `optima_zatca`.

> Note: `.github/copilot-instructions.md` is an older AI-agent guide. It is mostly accurate but predates several refactors — trust this file where they disagree. Notably, the submission logic now lives in `submission_workflow.py`, and the onboarding wizard is the Vue app described under "Onboarding" below.

## Commands

```bash
# Bench test runs need a site, and on Frappe 16 they WRITE to it: importing ERPNext's
# test utilities runs BootStrapTestData, which commits test companies, users, custom
# fields and System Settings changes (time zone, precision). Run them only on a
# throwaway site (CI's test_site) — never on a site holding real or restored data.
bench --site <throwaway-site> run-tests --app optima_zatca
bench --site <throwaway-site> run-tests --module optima_zatca.zatca.tests.test_invoice

# zatca/tests modules built on plain unittest.TestCase need no site. Run them from the
# app root with the bench env active (pytest is not installed in the bench env):
python -m unittest optima_zatca.zatca.tests.test_onboarding_retry optima_zatca.zatca.tests.test_register_company \
    optima_zatca.zatca.tests.test_xml_transport \
    optima_zatca.zatca.tests.test_invoice_data optima_zatca.zatca.tests.test_prepayment_invoice

# The events/tests/ suites need real doctype meta, so they run under bench.
# Matrix = in-memory logic; integration = real save:
bench --site <throwaway-site> run-tests --module optima_zatca.events.tests.test_prepayment
bench --site <throwaway-site> run-tests --module optima_zatca.events.tests.test_prepayment_integration

# After Python changes
bench restart
# After hooks.py / fixture / custom-field changes
bench --site <site> clear-cache
bench --site <site> migrate

# Build the app's bundled desk JS (public/js) and the onboarding wizard after editing them
bench build --app optima_zatca

# Onboarding wizard (Vue SPA) — see "Onboarding" below
cd zatca-onboarding && yarn install
yarn dev:mock     # mocked backend; ?scenario=ok|reject|otp  ?seed=registered|empty  ?lang=ar
yarn dev          # against the running bench (proxies /api, /assets, /socket.io)
yarn test         # vitest: progress.ts and validation.ts
yarn typecheck
yarn build        # what bench build runs; also copies the HTML entry to www/
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

**Frappe 16:** `frappe.db.get_value` refuses a Document as its filter (`ValueError: Unsupported filters type`). `get_base_url` in `zatca/request.py` takes either the setting's name or the loaded setting, because `submission_workflow.py` and the onboarding's `demo.py` pass the document. Pass names to `get_value` in new code.

## Wiring (hooks.py)

- `override_doctype_class`: `Sales Invoice` → `overrides.sales_invoice.CustomSalesInvoice` (prepayment GL entries). Must subclass ERPNext's `SalesInvoice`.
- `doc_events` on `Sales Invoice`: `validate` → `validate_prepayments`, plus `on_submit` / `before_cancel` / `on_trash` in `events/sales_invoice.py`.
- `regional_overrides` (Saudi Arabia): replaces ERPNext's `update_itemised_tax_data` with `zatca/itemised_tax.py` for ZATCA-compliant per-line tax.
- `app_include_js`: the three `public/js/sales_invoice/*.js` modules are loaded **in dependency order** — `prepayment.js` (constants) first, then `pos_payments.js`, then `zatca_buttons.js`. Preserve that order.
- `app_include_css`: `public/css/desk_fonts.bundle.css` is the **only** owner of the desk's `--font-stack` across the Optima suite — other apps must not set it, because whichever app's CSS loads last replaces the whole variable. It gives the desk:
  - the Saudi Riyal sign (U+20C0, U+FDFC) from `public/fonts/Claudion.ttf`, `unicode-range`-limited to those two characters and **first** in the stack. Almarai has its own older U+FDFC glyph, so Claudion must stay ahead of it.
  - Almarai (300/400/700/800) for Arabic text only, via an Arabic `unicode-range`, so Latin text keeps Inter.
  - `body .chart-container { font-family: var(--font-stack) }` — frappe-charts injects its own `.chart-container` font into `<head>` at runtime, after every `app_include_css` link, so equal specificity would lose.

  The stack is a copy of Frappe's (`espresso/_typography.scss`) with Claudion and Almarai added — re-sync it if a Frappe upgrade changes it. As a bundle it needs `bench build --app optima_zatca`; in return its filename is content-hashed, so edits reach browsers despite nginx's one-year `/assets` cache. Print formats and PDF/A-3 do not use it; they load Claudion and Almarai themselves.
- `website_route_rules` + `www/zatca_onboarding.py` serve the onboarding SPA at `/zatca-onboarding/*` (see "Onboarding").
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

There are **two test suites with deliberately different rules** — match the one you're adding to.

### `zatca/tests/` — submission and onboarding logic (mock-only)

- Tests for the submission pipeline and onboarding live in `optima_zatca/zatca/tests/` and use **`unittest.mock` only** — no real HTTP (`zatca/request.py` also throws on any request while `frappe.flags.in_test`), no DB writes.
- Their base class decides where they run. On Frappe 16 the `FrappeTestCase` modules (`test_invoice`, `test_request`, `test_zatca_integration`) open a site in `setUpClass`, so they need a throwaway site. The `unittest.TestCase` modules run bare with `python -m unittest` (see Commands). **Use plain `unittest.TestCase` for new mock-only tests**, as `test_onboarding_retry.py` does.
- When adding submission logic, add or extend a `_decide_*` pure function and unit-test it directly rather than testing the whole orchestrator with a live doc.

### `events/tests/` — the `validate`/lifecycle doc_events (two layers)

The prepayment `validate` rules (`events/prepayment.py`) are covered by a **two-layer** suite that runs under `bench` (they need the real doctype meta), not bare pytest:

- **Matrix layer** (`test_prepayment.py`) — exhaustive branch coverage. Builds an unsaved `frappe.new_doc("Sales Invoice")`, sets fields in memory, and calls the private `_validate_*` helpers directly (mocking `frappe.db.get_value` for the two lookup helpers). No `insert()`, no teardown. Assert the **real business-rule message** here, because `validate_prepayments` re-raises `ValidationError` untouched but funnels *unexpected* exceptions through `log_and_throw_error` (generic message + Error Log row) — so the wrapper is the wrong seam for message assertions.
- **Integration layer** (`test_prepayment_integration.py`) — `FrappeTestCase` with `frappe.db.rollback()` in `tearDown`. Saves a real Sales Invoice so the `validate` hook fires end-to-end, proving wiring the matrix layer can't (hook registered, custom fields carry values by validate time, a blocked invoice actually fails `insert()`). Asserts only *that* a `ValidationError` is raised — message coverage is the matrix layer's job. Never `submit()` (that triggers the ZATCA `on_submit` path).

**`events/tests/helpers.py` is site-agnostic — keep it that way.** It provisions its own dedicated `Optima Zatca Test …` records (party, item, item-tax-template, commercial register + address) rather than borrowing whatever the site contains; borrowing broke it on a fresh site (the first "non-stock" item found was a fixed asset). Each `get_or_create_*` reuses a real site's record where one fits and fabricates a minimal one otherwise, so a scratch CI site and a real KSA site behave identically. When you add a new fixture, watch for the KSA landmines already handled there: `customer_type="Individual"` (dodges mandatory registration/`tax_id`), the mandatory Item `taxes` table, and pre-seeding order/invoice `taxes` rows **with `cost_center`**. Because existing sites already have the records, the *fabricate* branches only run on a fresh CI site — a wrong field name there stays invisible locally (as the `Sales Invoice Type` `type` field and the fixed-asset item both did), so a green CI run is the real proof.

**CI** (`.github/workflows/ci.yml`) runs the `events/tests/` suites (prepayment and sales invoice, matrix + integration each) on a throwaway `test_site`; ERPNext's `before_tests` hook supplies the company + chart of accounts. The `zatca/tests/` suite is not yet wired into CI, so its tests only run when someone runs them.

## Onboarding (`/zatca-onboarding`)

The device-onboarding wizard: a **Vue 3 + frappe-ui + Tailwind** SPA in `zatca-onboarding/`, built into `public/zatca-onboarding/` with its HTML entry copied to `www/zatca-onboarding.html` (build output, gitignored). It is a guided task, not documentation: phase → CR type → company → registers → review + OTPs → progress board → done.

```
www/zatca_onboarding.py   host page: guests → login, website users → /, then a boot JSON
        │                 (csrf_token, site_name, socketio_port under bench start, lang, rtl, translations)
        │ 1. frappe.client.get_list Company
        │ 2. zatca.api.get_companies_registered   → Landing (none yet) or the registered list
        │ 3. zatca.api.register_company           → fired once; the board follows the events
        │ realtime "zatca" {message, indicator, percentage, complete, commercial_register_name}
        ▼
zatca/setup.py  saving_register_data → per CR: Address → Commercial Register → Optima Zatca Setting
                → add_company_to_zatca: CSR + keys → compliance CSID (OTP) → 6 sample invoices (demo.py)
                  → production CSID
```

- **v15 backend contract.** `register_company` takes `commercial_register` as a **JSON string** — `validate_register_data` only parses strings, and a list crashes it. On Add CR the wizard sends only the new CRs, never the ones already registered.
- **Fire, then listen.** The board is driven only by the `zatca` events; `progress.ts` maps them (green 20 CSID, 30–80 accepted invoices, red ≥ 20 rejected, red 0 certificate error, 95 PCSID, `complete`). It never waits for `register_company`, which in v15 returns only after the whole run (≥ 30 s per CR: a 5 s sleep after each sample invoice), so moving the run to background jobs needs no UI change.
- **Retry resumes.** A retry re-sends the same branch, and `_decide_register_action` matches it to what is stored for its CRN: new → created; before the compliance CSID → its Address, Commercial Register and Optima Zatca Setting are updated in place (so a fresh OTP after a refused CSID is saved); after the CSID → resumed untouched, because the register's identity went into the CSR. A CRN of another company, or one already connected, is refused. `check_csid` also gates key generation: the CSID is bound to the key it was requested with, and replacing that key silently breaks every later invoice signature. `demo.py` skips sample invoices already accepted.
- **Environment.** `api_endpoints` comes from the site config key `zatca_onboarding_environment` (`sandbox` or `simulation`) and defaults to `production`. The sandbox OTP is `123345`.
- **Mock.** The `#backend` Vite alias picks `src/api/mock.ts` (under `VITE_ZATCA_API=mock`) or `live.ts`, so the mock never ships. Keep the mock's events identical to what `setup.py` and `demo.py` publish.
- **Strings.** `__()` reads `boot.translations` (Frappe's `get_all_translations`). Add wizard strings to `translations/ar.csv`, but never a string Frappe or ERPNext already translates — a row here overrides it desk-wide. Where the core translation is wrong for the wizard, use the context column (`Back,رجوع,onboarding`).
- **Socket.io** connects to `<origin or :socketio_port>/<site_name>`: the namespace must be the site name, as in Frappe's own client.
- The old desk page `/app|desk/zatca-onboarding` only redirects here; the workspace shortcut links here directly.

**Known gaps in the v15 onboarding backend** (not fixed yet): `demo.py` reports gateway errors (429/520/522 from ZATCA's Cloudflare) as "Was Rejected in Zatca" and swallows exceptions without a log; `register_company` has no permission check; Phase 1 still requests certificates like Phase 2.