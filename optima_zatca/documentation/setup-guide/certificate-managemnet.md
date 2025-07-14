## documentation/2-setup-guide/certificate-management.md


# Certificate Management

## Overview

Digital certificates are the cornerstone of ZATCA's security model. This guide covers certificate lifecycle management, storage, and troubleshooting.

## Certificate Types

### 1. Compliance Certificate (CSID)
- **Purpose**: Testing and validation
- **Validity**: 1 year
- **Environment**: Sandbox/Simulation
- **Usage**: Compliance invoice testing

### 2. Production Certificate (PCSID)
- **Purpose**: Live invoice submission
- **Validity**: 1 year  
- **Environment**: Production
- **Usage**: Real invoice clearance/reporting

## Certificate Components

### 1. Private Key

- **Algorithm**: ECDSA with secp256k1 curve
- **Storage**: Encrypted in database
- **Usage**: Signing invoices

### 2. Public Key

- **Derived from**: Private key
- **Usage**: QR code generation
- **Shared with**: ZATCA

### 3. X.509 Certificate

- **Contains**: Public key, company info, ZATCA signature
- **Usage**: Authentication with ZATCA

## Certificate Generation Process

### Step 1: Key Pair Generation
```python
# System automatically generates using OpenSSL:
openssl ecparam -name secp256k1 -genkey -noout -out private.pem
```

# Configuration file includes:
[req]
distinguished_name = dn
[dn]
C = SA  # Country
O = Company Name (Arabic)
OU = Commercial Register Name
CN = Unique Identifier