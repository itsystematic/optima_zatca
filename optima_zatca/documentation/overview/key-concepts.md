# Key Concepts

## Core Terminology

### ZATCA (زاتكا)
Zakat, Tax and Customs Authority - The Saudi Arabian government body responsible for tax collection and customs.

### Fatoora
The Arabic term for invoice, used in the context of ZATCA's e-invoicing system.

### Phase 2 Integration
The mandatory integration phase requiring all businesses to connect their invoicing systems directly with ZATCA.

## Technical Concepts

### 1. Certificate Signing Request (CSR)
A cryptographic message sent to ZATCA to obtain a digital certificate for invoice signing.

**Components:**
- Common Name (CN): Unique identifier
- Organization Identifier: VAT number
- Serial Number: EGS serial number
- Industry/Location: Business details

### 2. Cryptographic Security Identifier (CSID)
The digital certificate issued by ZATCA for authenticating and signing invoices.

**Types:**
- **Compliance CSID**: For testing and validation
- **Production CSID**: For live invoice submission

### 3. Invoice Counter Value (ICV)
A sequential counter that must increment with each invoice, maintaining continuity.

### 4. Previous Invoice Hash (PIH)
The SHA256 hash of the previous invoice, creating a blockchain-like chain of invoices.

### 5. Invoice Types

#### By Transaction Type
- **Standard (B2B)**: Business-to-business, requires clearance
- **Simplified (B2C)**: Business-to-consumer, reporting only

#### By Document Type
- **Invoice (388)**: Standard sales invoice
- **Credit Note (381)**: For returns/refunds
- **Debit Note (383)**: For additional charges
- **Prepayment (386)**: For advance payments

### 6. Clearance vs Reporting

**Clearance (B2B)**:
- Real-time validation
- ZATCA approval required before issue
- Returns cleared invoice with ZATCA stamp

**Reporting (B2C)**:
- Post-facto reporting
- Can be batched
- No pre-approval needed

### 7. Tax Categories

### 8. XML Structure

The invoice XML follows UBL 2.1 standard with ZATCA extensions:

```xml
<Invoice>
    <UBLExtensions>
        <UBLExtension>
            <ExtensionContent>
                <sig:UBLDocumentSignatures>
                    <!-- Digital signature -->
                </sig:UBLDocumentSignatures>
            </ExtensionContent>
        </UBLExtension>
    </UBLExtensions>
    <!-- Invoice content -->
</Invoice>