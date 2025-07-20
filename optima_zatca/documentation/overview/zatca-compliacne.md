## documentation/1-overview/zatca-compliance.md


# ZATCA Compliance Overview

## Phase 2 Requirements

The ZATCA Integration implements Phase 2 (Integration Phase) requirements:

### 1. Technical Requirements

#### XML Standards
- **UBL 2.1**: Universal Business Language format
- **UTF-8 Encoding**: All XML documents
- **XAdES Signatures**: XML Advanced Electronic Signatures
- **W3C Standards**: Compliance with XML specifications

#### Security Requirements
- **ECDSA Cryptography**: Elliptic Curve Digital Signature Algorithm
- **secp256k1 Curve**: For key generation
- **SHA256 Hashing**: For invoice hash calculation
- **X.509 Certificates**: For authentication

### 2. Invoice Types

#### Standard Invoice (B2B)
- For transactions between businesses
- Requires clearance from ZATCA
- Full buyer details required
- Real-time validation

#### Simplified Invoice (B2C)
- For transactions with consumers
- Reporting only (no clearance)
- Limited buyer information
- Batch reporting allowed

#### Special Types
- **Credit Notes**: For returns (Type 381)
- **Debit Notes**: For additional charges (Type 383)
- **Prepayment Invoices**: For advance payments (Type 386)

### 3. Mandatory Fields

#### Company Information
- Commercial Registration Number
- VAT Number (15 digits, starts and ends with 3)
- Arabic Company Name
- Complete Address (Building, Street, District, City, Postal)

#### Invoice Fields
- Sequential Invoice Counter (ICV)
- Previous Invoice Hash (PIH)
- UUID (Universally Unique Identifier)
- QR Code with specific format
- Digital Signature

#### Tax Categories
- **S**: Standard rate (15%)
- **Z**: Zero-rated (0% with reason)
- **E**: Exempt (with exemption reason)
- **O**: Out of scope

### 4. QR Code Specifications

The QR code must contain:
1. Seller's name
2. VAT registration number
3. Timestamp (Date and Time)
4. Invoice total (with VAT)
5. VAT total
6. Invoice hash
7. ECDSA signature
8. ECDSA public key
9. Certificate signature

### 5. API Endpoints

#### Compliance Phase
- CSR generation and certificate issuance
- Compliance invoice validation
- Test environment access

#### Production Phase
- Invoice clearance (B2B)
- Invoice reporting (B2C)
- Certificate renewal

## Compliance Checklist

- [ ] Valid Commercial Registration
- [ ] VAT Registration (15 digits)
- [ ] Arabic company name
- [ ] Complete address information
- [ ] ZATCA-approved certificate
- [ ] Sequential invoice numbering
- [ ] Previous invoice hash chain
- [ ] Valid QR code generation
- [ ] Digital signature implementation
- [ ] API integration testing