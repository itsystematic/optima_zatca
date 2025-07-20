# Module Structure

## Directory Layout
```markdown
optima_zatca/
├── init.py
├── hooks.py # App hooks and configurations
├── patches.txt # Database patches
├── requirements.txt # Python dependencies
│
├── optima_zatca/ # Main app module
│ ├── init.py
│ ├── boot.py # Boot session configurations
│ ├── utils.py # Utility functions after_app_install
│ │
│ ├── overrides/ # ERPNext overrides
│ │ ├── init.py
│ │ └── sales_invoice.py # Custom Sales Invoice class
│ │
│ ├── events/ # Document events
│ │ ├── init.py
│ │ └── sales_invoice.py # Sales Invoice events
│ │
│ ├── zatca/ # Core ZATCA module
│ │ ├── init.py
│ │ ├── setup.py # Company registration
│ │ ├── invoice.py # Invoice processing entry point
│ │ ├── api.py # ZATCA API interface
│ │ ├── request.py # HTTP request handling
│ │ ├── utils.py # ZATCA-specific utilities
│ │ ├── keys.py # CSR and key generation
│ │ ├── demo.py # Sample invoice processing
│ │ ├── logs.py # Logging functionality
│ │ │
│ │ ├── classes/ # Core classes
│ │ │ ├── init.py
│ │ │ ├── invoice.py # Invoice data processing
│ │ │ ├── validate.py # Validation logic
│ │ │ └── xml.py # XML generation
│ │ │
│ │ └── Samples/ # Sample files
│ │ ├── Standard/ # XML templates
│ │ └── Invoices/ # Sample invoice JSON
│ │
│ ├── public/ # Frontend assets
│ │ ├── js/ # JavaScript files
│ │ │ ├── company.js
│ │ │ ├── branch.js
│ │ │ ├── sales_invoice.js
│ │ │ └── ...
│ │ └── css/ # Stylesheets
│ │
│ ├── templates/ # HTML templates
│ │ └── pages/
│ │ └── zatca-onboarding.html
│ │
│ ├── www/ # Web pages
│ │ └── zatca-onboarding.py
│ │
│ └── files/ # Standard data files
│ ├── tax_category.csv
│ ├── tax_exemption.csv
│ └── registration_type.csv
│
└── optima_zatca/ # DocTypes
├── commercial_register/
├── optima_zatca_logs/
├── optima_zatca_setting/
├── prepayment_invoice/
├── registration_type/
├── sales_invoice_type/
├── tax_category/
└── tax_exemption/
```
## Module Descriptions

### Core Modules

#### hooks.py
Main configuration file for the Frappe app:
```python
app_name = "optima_zatca"
app_title = "Optima Zatca"
```
# Key configurations:
- after_app_install: Initial setup
- override_doctype_class: Custom Sales Invoice
- doc_events: Invoice event handlers
- doctype_js: Client-side scripts
- regional_overrides: Saudi-specific tax handling

## ZATCA Module Structure
## setup.py
## Handles company registration workflow:
- add_company_to_zatca(): Main registration orchestrator
- get_certificate(): Obtains compliance CSID
- get_production_certificate(): Obtains production CSID
- saving_register_data(): Saves company registration

## invoice.py
## Main entry point for invoice processing:
- send_to_zatca(): Processes and sends invoice
- update_itemised_tax_data(): Calculates tax details
- create_prepayment_invoice(): Handles prepayments

## api.py
## ZATCA API interface layer:
- get_zatca_csid(): Get compliance certificate
- get_production_csid(): Get production certificate
- make_invoice_request(): Submit invoice
- renew_production_csid(): Renew certificate

Classes Module
invoice.py (ZatcaInvoiceData)
Transforms ERPNext invoice to ZATCA format:
class ZatcaInvoiceData:
    # Handles:
    - Data loading and validation
    - Invoice type determination
    - Tax calculations
    - Prepayment processing

validate.py (ZatcaInvoiceValidate)
Comprehensive validation logic:
class ZatcaInvoiceValidate:
    # Validates:
    - Company settings
    - Invoice fields
    - Customer information
    - Tax compliance

xml.py (ZatcaXmlGenerator)
XML generation and signing:
class ZatcaXmlGenerator:
    # Processes:
    - XML template loading
    - Data population
    - Hash calculation
    - Digital signatures
    - QR code generation