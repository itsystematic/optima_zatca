# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`optima_zatca` is a Frappe/ERPNext app implementing Saudi Arabia's **ZATCA (Fatoora) e-invoicing** — Phase 1 (QR-only simplified invoices) and Phase 2 (full clearance/reporting). It turns an ERPNext Sales Invoice into signed UBL 2.1 XML, submits it to ZATCA's API, and records the full audit trail. `develop` (the default branch) and `version-16` target Frappe/ERPNext 16, and `version-15` targets 15. Work lands on `develop`, `version-16` moves only by release merges from it, and `version-15` gets labelled backports; `CONTRIBUTING.md` has the full branch, backport and release rules. Branch new work from `develop`, never from a release branch.

The v15 line runs in the bench at `/home/erpnext/fawaz`, whose bench-level `CLAUDE.md` documents the other apps, the sites and general `bench` usage. The v16 line runs in `/home/erpnext/frappe-bench16`, which has no bench-level guide. **Both benches host many sites — ask which site the user is on before running any `bench --site` command.** The rest of this file is specific to `optima_zatca`.

> Note: `.github/copilot-instructions.md` is an older AI-agent guide. It is mostly accurate but predates several refactors — trust this file where they disagree. Notably, the submission logic now lives in `submission_workflow.py`, and the onboarding wizard is the Vue app described under "Onboarding" below.

## Commands

```bash
# Bench test runs need a site, and they WRITE to it. On a site with no company, the app's
# before_tests hook (optima_zatca/tests/bootstrap.py) runs the setup wizard and commits a
# Saudi test company, and the Phase One QR test leaves its image file on disk. Run them only
# on a throwaway site (CI's test_site), never on a site holding real or restored data.
bench --site <throwaway-site> run-tests --app optima_zatca      # every suite, as CI runs it
bench --site <throwaway-site> run-tests --module optima_zatca.events.tests.test_prepayment

# The plain unittest.TestCase modules need no site. Run them from the app root with the
# bench env active (pytest is not installed in the Frappe 16 bench env):
python -m unittest optima_zatca.zatca.tests.test_onboarding_retry optima_zatca.zatca.tests.test_register_company \
    optima_zatca.zatca.tests.test_xml_transport \
    optima_zatca.zatca.tests.test_invoice_data optima_zatca.zatca.tests.test_prepayment_invoice \
    optima_zatca.arabic.test_arabic optima_zatca.zatca.tests.test_pdf_fonts

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
- `app_include_css` and `web_include_css`: `public/css/desk_fonts.bundle.css` is the **only** owner of `--font-stack` across the Optima suite, on the desk, the website and the portal — other apps must not set it, because whichever app's CSS loads last replaces the whole variable. It gives them:
  - the Saudi Riyal sign (U+20C0, U+FDFC) from `public/fonts/Claudion.ttf`, `unicode-range`-limited to those two characters and **first** in the stack. Almarai has its own older U+FDFC glyph, so Claudion must stay ahead of it.
  - Almarai (300/400/700/800) for Arabic text only: the self-hosted Arabic woff2 subsets `public/fonts/Almarai-<weight>-arabic.woff2` with an Arabic `unicode-range`, so Latin text keeps Inter. Always on, no setting. No CDN or Google Fonts anywhere.
  - `body .chart-container, body .graph-svg-tip { font-family: var(--font-stack) }` — frappe-charts injects its own `.chart-container` font into `<head>` at runtime, after every `app_include_css` link, so equal specificity would lose.

  The stack is a copy of Frappe's (`espresso/_typography.scss`) with Claudion and Almarai added — re-sync it if a Frappe upgrade changes it. As a bundle it needs `bench build --app optima_zatca`; in return its filename is content-hashed, so edits reach browsers despite nginx's one-year `/assets` cache. Print formats and PDF/A-3 do not use it; they load Claudion and Almarai themselves, from the TTF files in `public/fonts/` on the server. PDF/A-3 renders with `zatca/pdf_fonts.local_font_fetcher`: the Google Fonts `@import` Frappe adds for a format with a font set (ERPNext's "Sales Invoice Modern with Images" sets Inter) is answered with Frappe's local Inter plus Claudion for the Riyal sign, so no font request leaves the server. Arabic in Almarai needs a format that names Almarai, such as "Zatca Sales Invoice"; for any other format WeasyPrint falls back to the server's DejaVu Sans. "Zatca Sales Invoice" keeps its `@font-face` rules in its `.html` template, not its CSS: under PDF/A-3 (`pdfa3.py` sets `doc.flags.zatca_pdfa3`) the template emits the `__FONT_…__` / `__LETTERHEAD_LOGO_PATH__` placeholders that `pdfa3.py` replaces with `file://` paths and a base64 logo; every other print gets absolute URLs on the site (`frappe.utils.get_url`), because Frappe's URL expansion for wkhtmltopdf breaks a relative `url()` in `@font-face` and a placeholder URL makes wkhtmltopdf refuse the PDF. The format's CSS uses custom properties, which wkhtmltopdf ignores, so its downloaded PDF falls back to plain fonts; the browser print and PDF/A-3 render it fully.
- `app_include_js` also loads `public/js/desk_labels_i18n.js`: it passes the labels Frappe renders without `__()` (dock items and tooltips, module logo title, sidebar items, the "N Filters Applied" counter, "Tree Level", "Search") through `__()`, so `locale/ar.po` reaches them.
- `after_migrate`: `arabic/load_order.py` warns (Error Log + console, never reorders) when frappe, erpnext or hrms load after optima_zatca, or when `daad` is installed on the same site.
- `website_route_rules` + `www/zatca_onboarding.py` serve the onboarding SPA at `/zatca-onboarding/*` (see "Onboarding").
- `after_install` / `after_app_install` run installers; migrations run the patches in `optima_zatca/patches.txt` (prepayment doctypes/fields, roles, print formats, item-tax setup).

## Arabic (`locale/ar.po`)

`optima_zatca/locale/ar.po` is the **only** Arabic file of the Optima suite: frappe, erpnext, hrms and every Optima app (optima_feed, optima_hr, demo_access, …). No other Optima app ships `locale/ar.po` or `translations/ar.csv`, and there is no CSV here either; every Optima app lists `optima_zatca` in `required_apps`. Frappe compiles the file to `sites/assets/locale/ar/LC_MESSAGES/optima_zatca.mo` and lets it win over the apps installed before optima_zatca.

- Ambiguous terms use `msgctxt`; the code passes the same context.
- `bench --site <site> zatca-arabic-harvest` writes `translations_review/<date>.csv` (gitignored): Arabic found in other installed apps' PO/CSV files and Translation records that is `new` or `differs`, plus core msgids with no Arabic anywhere (`missing`). `--from <file.po>` reviews one PO file instead (e.g. a DaaD release with community fixes); `--status` limits the rows. A person marks rows `approved = yes`; `--apply <csv>` merges only those, validates the file and recompiles the MO.
- `bench zatca-export-daad --to apps/daad/daad/locale/ar.po` writes the public DaaD app's catalog: only msgids that exist in frappe, erpnext and hrms (extracted fresh with Frappe's own POT builder), keeping DaaD's header. Never edit core wording in DaaD by hand.
- `arabic/catalog.py` validates a catalog (it must parse and compile; `{0}` / `%(name)s` placeholders must match). `arabic/test_arabic.py` is a site-free `unittest` module.

## Key DocTypes

- **Optima Zatca Setting** — one per Commercial Register **and environment** (certificates, endpoints). The one ticked `use_for_invoices` signs the register's invoices; `invoice_context._get_company_settings` selects by that flag, never by `commercial_register` alone.
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

### Base classes (Frappe 16)

Import them from `frappe.tests`. The base class decides how the runner prepares a suite:

| Test | Base class | Runs |
|---|---|---|
| Decisions on an in-memory doc (needs doctype meta, saves nothing) | `UnitTestCase` | under bench; the "unit" category builds no test records |
| Real saves, submits, GL rows | `IntegrationTestCase` | under bench; the "integration" category runs this app's `before_tests` first |
| Pure code, with Frappe faked or absent | plain `unittest.TestCase` | bare with `python -m unittest` (see Commands), and again in the bench run |

- **Never subclass `FrappeTestCase`.** On Frappe 16 it is a deprecated stand-in, and the runner prepares such suites the old way: it walks the whole app and builds test records for every `test_*.py` in a `doctype/` folder. That walk reached ERPNext's test utilities and failed CI with `MandatoryError: [Item, _Test Item]: taxes`.
- **Keep `IntegrationTestCase` suites outside `doctype/` folders.** Inside one, `setUpClass` builds test records for the doctype's whole link graph.
- **Roll back after every test.** Give every integration suite a `tearDown` with `frappe.db.rollback()`, plus `frappe.clear_cache()` when it touches Singles or Company. The class itself rolls back only once, after its last test.
- **Never import `erpnext.tests.*`**, or ERPNext test helpers such as `create_sales_invoice`. Importing them runs `BootStrapTestData`, whose `_Test Item` has no taxes and is refused by the mandatory Item `taxes` rule (#96 asks whether to keep that rule). CI's first step greps for such imports and fails the build.
- **Assert messages in matrix tests, never in integration tests.** Every case names the bug it catches.

```
optima_zatca/tests/bootstrap.py    before_tests: the Saudi test company (see CI below)
optima_zatca/tests/utils.py        shared factories
optima_zatca/tests/isolation.py    load_with_fakes(): import a module against fake dependencies
events/tests/                      validate / lifecycle doc_events, matrix + integration pairs
zatca/tests/                       submission, onboarding, itemised tax
optima_zatca/report/advance_payment_report/test_advance_payment_report.py
```

`events/tests/helpers.py` only re-exports `optima_zatca.tests.utils`, because optima_masar's integration tests import the factories from that path.

### `zatca/tests/` — submission, onboarding and itemised tax

- The submission and onboarding tests use **`unittest.mock` only**: no real HTTP (`zatca/request.py` also throws on any request while `frappe.in_test`). The two `*_integration.py` modules are the exceptions:
  - `test_zatca_integration` sends a saved draft through `send_to_zatca`, with the transport mocked.
  - `test_itemised_tax_integration` saves a standard-rated invoice.
- A test that needs a fake `frappe` loads its module with `load_with_fakes()`, never by assigning `sys.modules` itself. A fake left in `sys.modules` reaches every later test in the same `--app` run.
- When adding submission logic, add or extend a `_decide_*` pure function and unit-test it directly rather than testing the whole orchestrator with a live doc.

### `events/tests/` — the `validate`/lifecycle doc_events (two layers)

The prepayment `validate` rules (`events/prepayment.py`) are covered by a **two-layer** suite that runs under `bench` (they need the real doctype meta):

- **Matrix layer** (`test_prepayment.py`, `UnitTestCase`) — exhaustive branch coverage. Builds an unsaved `frappe.new_doc("Sales Invoice")`, sets fields in memory, and calls the private `_validate_*` helpers directly (mocking `frappe.db.get_value` for the two lookup helpers). No `insert()`, no teardown. Assert the **real business-rule message** here, because `validate_prepayments` re-raises `ValidationError` untouched but funnels *unexpected* exceptions through `log_and_throw_error` (generic message + Error Log row) — so the wrapper is the wrong seam for message assertions.
- **Integration layer** (`test_prepayment_integration.py`, `IntegrationTestCase`) — `frappe.db.rollback()` in `tearDown`. Saves a real Sales Invoice so the `validate` hook fires end-to-end, proving wiring the matrix layer can't (hook registered, custom fields carry values by validate time, a blocked invoice actually fails `insert()`). Asserts only *that* a `ValidationError` is raised — message coverage is the matrix layer's job. Never `submit()` (that triggers the ZATCA `on_submit` path).

### Factories (`optima_zatca/tests/utils.py`)

**The factories are site-agnostic — keep them that way.** They provision their own dedicated `Optima Zatca Test …` records (party, item, item-tax-template, commercial register + address) rather than borrowing whatever the site contains; borrowing broke them on a fresh site (the first "non-stock" item found was a fixed asset).

- **Each one takes the company's own record, never another company's.** The template factory asks for `KSA VAT 15% Selling` by title; taking the company's first template once gave CI a 0% purchase one. A fabricated Commercial Register takes a CRN derived from the company, because registers are named by their CRN.
- **Watch for the KSA landmines already handled there:** `customer_type="Individual"` (dodges mandatory registration/`tax_id`), the mandatory Item `taxes` table, and pre-seeding order/invoice `taxes` rows **with `cost_center`**.
- **Only CI proves the fabricate branches.** Existing sites already have the records, so the *fabricate* branches only run on a fresh CI site. A wrong field name there stays invisible locally (as the `Sales Invoice Type` `type` field and the fixed-asset item both did), so a green CI run is the real proof.

### CI

`.github/workflows/ci.yml` runs on a fresh `test_site`:

1. It refuses imports of ERPNext test modules.
2. It runs the site-free `unittest` modules before the site exists.
3. It runs `bench --site test_site run-tests --app optima_zatca`, which discovers every `test_*.py`, so a new test file needs no CI change.

**The company comes from this app's `before_tests`, `optima_zatca/tests/bootstrap.py`.** ERPNext 16 no longer completes the setup wizard before tests. On a site with no company, the hook runs it for **Optima Zatca Test Company (`OZT`), Saudi Arabia / SAR**. It then creates the VAT accounts and item tax templates and runs the provisioning patches, which `after_install` skipped while there was no company. A site that already has a company is left alone. Because the CI company is Saudi, CI also runs the region-gated code: the itemised-tax override and the Phase One QR.

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
- **Environments side by side.** The wizard sends an `environment` (chosen on Review); `_decide_environment` accepts `simulation` and `production`, plus `sandbox` only when the site config key `zatca_onboarding_environment` is `sandbox` (that key is also the default). A register gets one Optima Zatca Setting per environment, named `{company}-{CRN}-{environment}` (older settings keep `{company}-{CRN}`), with a unique index on (`commercial_register`, `api_endpoints`). The Address and Commercial Register are shared, so once any environment has a compliance CSID another environment only saves its own setting (`save_setting`). Onboarding ticks `use_for_invoices` on a register's first setting to reach the production CSID; moving invoices to another environment is a manual tick on the form, which unticks the others. No patch ticks pre-existing settings: an upgraded site must tick each register's setting once, or Send to ZATCA refuses its invoices. The sandbox OTP is `123345`.
- **Mock.** The `#backend` Vite alias picks `src/api/mock.ts` (under `VITE_ZATCA_API=mock`) or `live.ts`, so the mock never ships. Keep the mock's events identical to what `setup.py` and `demo.py` publish.
- **Strings.** `__()` reads `boot.translations` (Frappe's `get_all_translations`). Add wizard strings to `locale/ar.po` (see "Arabic" below). An entry without context overrides the core wording desk-wide, so where the core translation is wrong for the wizard, give the entry a `msgctxt` (`Back` with context `onboarding` → `رجوع`). `yarn dev:mock ?lang=ar` reads the same file.
- **Socket.io** connects to `<origin or :socketio_port>/<site_name>`: the namespace must be the site name, as in Frappe's own client.
- The old desk page `/app|desk/zatca-onboarding` only redirects here; the workspace shortcut links here directly.

**Known gaps in the v15 onboarding backend** (not fixed yet): `demo.py` reports gateway errors (429/520/522 from ZATCA's Cloudflare) as "Was Rejected in Zatca" and swallows exceptions without a log; `register_company` has no permission check, and `api.get_production_csid` is whitelisted though only `setup.py` calls it; Phase 1 still requests certificates like Phase 2. Certificate renewal is broken: `api.renew_production_csid` passes `header=` to `request.make_patch_request` (parameter `headers`), which passes `header=` on to `requests.patch` — both raise `TypeError`.