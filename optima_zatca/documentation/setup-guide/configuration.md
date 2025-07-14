## documentation/2-setup-guide/configuration.md


# Configuration Guide

## Overview

This guide covers all configuration options for the ZATCA Integration app, from basic setup to advanced customizations.

## System Configuration

### 1. ZATCA Main Settings

Navigate to: **ZATCA Onboarding > ZATCA Main Settings**

```python
{
    "phase": "Phase 2",  # Current implementation phase
    "manual_submit": 0,  # Auto-submit invoices after ZATCA approval
    "default_environment": "production"  # sandbox/simulation/production
}

# In Company doctype
{
    "company_name_in_arabic": "الشركة العربية",  # Required
    "tax_id": "123456789012345",  # 15 digits
    "enable_zatca": 1
}

# Company Address must include:
{
    "building_no": "1234",  # 4 digits
    "street_name": "King Fahd Road",
    "district": "Al Olaya",
    "city": "Riyadh",
    "pincode": "12345",  # 5 digits
    "country": "Saudi Arabia"
}

# Configure tax templates
{
    "doctype": "Item Tax Template",
    "title": "Standard VAT 15%",
    "company": "Your Company",
    "tax_category": "S",  # Link to Tax Category
    "taxes": [{
        "tax_type": "VAT 15%",
        "tax_rate": 15
    }]
}

# Available Invoice types:
{
    "Normal": "Standard invoice",
    "Credit Note": "For returns",
    "Debit Note": "Additional charges",
    "Elementary Advance Payment": "Single advance",
    "Initial Prepayment": "First in series",
    "Prepayment": "Subsequent advances",
    "Adjustment": "Partial delivery",
    "Final Adjustment": "Final settlement"
}
```