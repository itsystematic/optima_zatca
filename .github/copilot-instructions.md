# Optima ZATCA - AI Coding Agent Instructions

## Project Overview
Optima ZATCA is a Frappe/ERPNext app for Saudi Arabia ZATCA (Zakat, Tax and Customs Authority) e-invoicing compliance, covering Phase 1 (QR-only) and Phase 2 (full clearance/reporting). Built on ERPNext v15, it generates UBL 2.1 XML invoices, performs cryptographic signing, and integrates with ZATCA's Fatoora API.

## Architecture

### Core Components
- **`optima_zatca/zatca/`** - Main ZATCA business logic
  - `invoice.py` - Orchestrates invoice submission workflow (validation → XML → API → logging)
  - `classes/invoice.py` - `ZatcaInvoiceData` class transforms ERPNext Sales Invoice to ZATCA data model
  - `classes/xml.py` - `ZatcaXmlGenerator` creates UBL 2.1 XML with cryptographic signing
  - `classes/validate.py` - Pre-submission validation (addresses, tax categories, customer data)
  - `api.py` - HTTP client for ZATCA endpoints (clearance, reporting, onboarding, compliance)
  - `setup.py` - CSR generation, certificate retrieval, device onboarding workflow
  - `keys.py` - `GenerateCSR` class for cryptographic key generation using OpenSSL

- **`optima_zatca/overrides/`** - ERPNext class extensions
  - `sales_invoice.py` - `CustomSalesInvoice` extends `SalesInvoice` for prepayment GL entries

- **`optima_zatca/events/`** - Document event hooks
  - `sales_invoice.py` - Lifecycle hooks (validate, on_submit, on_cancel, on_trash)

### Key DocTypes
- **Optima Zatca Setting** - Per-commercial-register ZATCA configuration (certificates, endpoints, environment)
- **Commercial Register** - Multi-device support for single company
- **Optima Zatca Logs** - Audit trail for every ZATCA API call (request/response XML, hashes, QR codes)
- **Prepayment Invoice** - Tracks prepayment references for adjustment invoices

### Data Flow
1. User submits Sales Invoice → `validate_prepayments()` pre-checks → hooks blocked if Phase 2 & not ZATCA-approved
2. User clicks "Send to ZATCA" button → `send_to_zatca(invoice_name)` orchestrator
3. `ZatcaInvoiceData.__init__()` loads related docs (company settings, addresses, customer info)
4. `ZatcaInvoiceData.process()` → `_build_zatca_invoice_data()` → `_generate_xml()`
5. `ZatcaXmlGenerator` creates UBL XML → cryptographic hash → digital signature → QR code
6. `make_invoice_request()` POSTs to clearance (Standard) or reporting (Simplified) endpoint
7. Response processed → invoice updated (sent_to_zatca=1, clearance_or_reporting status)
8. `make_action_log()` persists full request/response for audit
9. If auto-submit enabled & success → `invoice.submit()` automatically

## ERPNext/Frappe Patterns

### Document Lifecycle
- Override standard classes via `hooks.py`: `override_doctype_class = {"Sales Invoice": "optima_zatca.overrides.sales_invoice.CustomSalesInvoice"}`
- Document events via `doc_events` hook for validation/submission logic
- Use `frappe.get_doc()` to load, `doc.save()` / `doc.submit()` to persist, `frappe.throw()` for validation errors

### Whitelisted Methods
- `@frappe.whitelist()` decorator exposes Python functions to client-side JS via `frappe.call()`
- Example: `optima_zatca/public/js/sales_invoice.js` calls `send_to_zatca` via frappe.call

### Custom Fields
- Defined in `optima_zatca/startup/` or via fixtures
- Access via `doc.get("custom_field_name")` or `doc.custom_field_name`
- Key custom fields: `commercial_register`, `sales_invoice_type`, `sent_to_zatca`, `clearance_or_reporting`

### Database Operations
- Use `frappe.db.set_value()` for single field updates without triggering full document save
- Use `frappe.db.commit()` explicitly after DB writes in background jobs
- Always use `ignore_permissions=True` in system/automated contexts

## Critical Conventions

### Invoice Type Handling
- **Normal**: Standard invoice (code "388")
- **Initial Prepayment/Prepayment**: Advance payment invoice (code "386")
- **Adjustment/Final Adjustment**: Links to prepayment via `deducted_taxable_amount` and `deducted_grand_total`
- Prepayment logic in `sales_invoice.js` and `CustomSalesInvoice` class

### Multi-Currency Support
- All amounts must use `flt()` from `frappe.utils` for precision handling
- ZATCA requires SAR base currency but supports multi-currency with exchange rates in XML

### Error Handling Pattern
```python
from optima_zatca.zatca.utils import log_and_throw_error

try:
    # operation
except Exception as e:
    log_and_throw_error(
        operation="Operation Name",
        document_name=doc.name,
        exception=e
    )
```
This creates user-friendly error messages with full stack traces in Error Log doctype.

### Testing
- Tests in `optima_zatca/zatca/tests/`
- Use `FrappeTestCase` as base class
- Mock ZATCA API responses with `@patch('optima_zatca.zatca.api.make_invoice_request')`
- Run: `bench --site [site] run-tests optima_zatca`

## Development Workflow

### Setup
```bash
bench get-app https://github.com/itsystematic/optima_zatca.git
bench setup requirements  # Install asn1==2.7.1 dependency
bench build --app optima_zatca
bench --site [site] install-app optima_zatca
bench --site [site] migrate
```

### Frontend (Vue onboarding wizard)
```bash
cd zatca-onboarding
yarn install
yarn dev  # Development mode
yarn build  # Production build
```

### Common Commands
- `bench restart` - Restart after Python changes
- `bench clear-cache` - Clear Frappe cache
- `bench --site [site] console` - Python REPL with Frappe context
- `bench show-config` - Display current bench configuration

### Debugging
- Enable Developer Mode: `bench set-config developer_mode 1`
- View logs: `tail -f logs/frappe.log` or Error Log doctype in UI
- Use `frappe.log_error()` for production debugging (creates Error Log entry)

## ZATCA-Specific Knowledge

### Onboarding Process
1. Generate CSR (`GenerateCSR` class) → Submit to ZATCA with OTP
2. Get compliance CSID → Send 6 sample invoices (2 Standard + 4 Simplified variations)
3. All samples pass → Get production CSID → Enable live submission

### Clearance vs Reporting
- **Standard Invoices** (B2B): Clearance endpoint - invoice blocked until ZATCA approves
- **Simplified Invoices** (B2C): Reporting endpoint - invoice submitted, ZATCA notified asynchronously

### QR Code Generation
- Phase 1: TLV-encoded data (seller name, VAT, timestamp, total, tax)
- Phase 2: ZATCA-signed QR from clearance/reporting response
- Always store both `qr_code_generated` (before ZATCA) and `qr_code` (from ZATCA response)

## Regional Override
```python
# hooks.py
regional_overrides = {
    'Saudi Arabia': {
        'erpnext.controllers.taxes_and_totals.update_itemised_tax_data': 
        'optima_zatca.zatca.invoice.update_itemised_tax_data'
    }
}
```
This replaces ERPNext's tax calculation with ZATCA-compliant version for Saudi companies.

## Files to Reference
- `optima_zatca/zatca/invoice.py` - Main submission orchestrator (read first for flow understanding)
- `optima_zatca/zatca/classes/invoice.py` - Data transformation logic
- `optima_zatca/hooks.py` - Frappe app configuration and event bindings
- `optima_zatca/public/js/sales_invoice.js` - Client-side prepayment calculations
- `optima_zatca/zatca/tests/test_zatca_integration.py` - Integration test patterns

## Common Gotchas
- Always validate `commercial_register` exists before ZATCA operations
- Use `frappe.db.get_single_value("Zatca Main Settings", "phase")` to check Phase 1 vs Phase 2 mode
- XML must be exactly UBL 2.1 spec - whitespace/encoding matters for hash validation
- ZATCA timestamps require specific ISO 8601 format with timezone
- Never modify `ksa_einv_qr` field after ZATCA approval (audit trail violation)
