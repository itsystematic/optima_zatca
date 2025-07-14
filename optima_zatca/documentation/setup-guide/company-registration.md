## documentation/2-setup-guide/company-registration.md


# Company Registration Guide

## Overview

Company registration is the process of onboarding your company with ZATCA's e-invoicing system. This involves obtaining digital certificates and validating your integration.

## Prerequisites

Before starting registration:

1. **Valid OTP** from ZATCA Onboarding Portal
2. **Commercial Registration Number**
3. **VAT Certificate** (Tax ID must be 15 digits)
4. **Company Details** in Arabic
5. **Complete Address** with Saudi National Address components

## Registration Process

### Step 1: Access ZATCA Onboarding

1. Navigate to **ZATCA Onboarding** from ERPNext desk
2. Click **"Register New Company"**

### Step 2: Enter Company Information

#### Basic Information
- **Company**: Select from ERPNext companies
- **Company Name in Arabic**: As per commercial registration
- **Tax ID**: 15-digit VAT number (3XXXXXXXXXXXXX3)

#### Commercial Registration
- **CR Number**: 10-digit commercial registration
- **CR Name**: Branch/location name
- **Address Components**:
  - Building Number (4 digits)
  - Street Name
  - District
  - City
  - Postal Code (5 digits)
  - Additional Number (optional)

### Step 3: Multiple Branches

For companies with multiple branches:

```javascript
// Example branch structure
{
  "branches": [
    {
      "commercial_register_name": "Main Branch",
      "commercial_register_number": "1234567890",
      "building_no": "1234",
      "street_name": "King Fahd Road",
      "district": "Al Olaya",
      "city": "Riyadh",
      "postal_code": "11111"
    },
    {
      "commercial_register_name": "Jeddah Branch",
      "commercial_register_number": "0987654321",
      // ... address details
    }
  ]
}
```
### System generates CSR with these components:
- Common Name: Auto-generated UUID
- Organization Unit: Commercial Register Name
- Organization Name: Company name in Arabic
- Organization Identifier: VAT Number
- Serial Number: 1-SOLUTION|2-ERPNEXT|3-UUID
- Country: SA