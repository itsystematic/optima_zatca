# ZATCA Concepts & Glossary

Orientation for every reader — the ZATCA (Fatoora) vocabulary the rest of these docs assume.
Skim it once; each domain links back here for the terms it uses.

---

## The authority and the phases

- **ZATCA (زاتكا)** — the Saudi *Zakat, Tax and Customs Authority*, which runs the national
  e-invoicing programme.
- **Fatoora (فاتورة)** — "invoice"; ZATCA's e-invoicing platform is branded Fatoora.
- **Phase 1 (Generation)** — every invoice must carry a **QR code** and be a structured
  electronic document. No live connection to ZATCA. See [phase-one-qr](phase-one-qr/).
- **Phase 2 (Integration)** — invoices are **signed** and sent to ZATCA over its API, either
  cleared or reported. Requires onboarding a certificate. See [onboarding](onboarding/) and
  [submission](submission/).

## Clearance vs reporting

The two Phase-2 submission modes — which one an invoice takes is decided by its type:

| | **Clearance** | **Reporting** |
|---|---|---|
| For | **Standard / B2B** invoices | **Simplified / B2C** invoices |
| Timing | ZATCA must **approve before** the invoice is valid | Submitted **after** issue (may be batched) |
| Result | ZATCA returns a cleared, stamped invoice | ZATCA acknowledges the report |

## Invoice types (UBL document type codes)

| Code | Type | Notes |
|------|------|-------|
| **388** | Standard invoice | The normal sales invoice |
| **381** | Credit note | Returns / refunds |
| **383** | Debit note | Additional charges |
| **386** | Prepayment invoice | Advance payments — see [prepayment](prepayment/) |

## Tax categories

Per-line VAT category, per ZATCA:

| Code | Category | Rate |
|------|----------|------|
| **S** | Standard rate | 15% |
| **Z** | Zero-rated | 0% (reason required) |
| **E** | Exempt | 0% (exemption reason required) |
| **O** | Out of scope | — |

## The cryptographic chain

Phase-2 invoices form a tamper-evident chain — each references the one before it:

- **CSR** — Certificate Signing Request; what the device sends ZATCA to obtain its certificate.
- **CSID / PCSID** — Cryptographic Stamp Identifier: the **compliance** certificate (testing)
  and the **production** certificate (live). See [onboarding](onboarding/reference.md).
- **ICV** — Invoice Counter Value: a sequential counter that must increment with every invoice.
- **PIH** — Previous Invoice Hash: the SHA-256 hash of the prior invoice, linking the chain.
- **UUID** — a unique identifier per invoice.

## Standards & crypto

- **UBL 2.1** — the Universal Business Language XML the invoice is expressed in (UTF-8).
- **XAdES** — the XML Advanced Electronic Signature profile used to sign the invoice.
- **ECDSA on `secp256k1`** — the signing key algorithm/curve ZATCA mandates; **SHA-256** for
  hashing; **X.509** certificates for authentication.

## What the QR encodes

- **Phase 1** — a 5-field TLV: seller name, VAT number, timestamp, invoice total, VAT total.
  See [phase-one-qr/reference.md](phase-one-qr/reference.md).
- **Phase 2** — the Phase-1 five **plus** invoice hash, ECDSA signature, ECDSA public key, and
  (for standard invoices) the certificate signature.

---

## Company prerequisites (recap)

Every ZATCA-connected company needs: a valid **Commercial Registration**, a 15-digit **VAT
number** (starts and ends with `3`), an **Arabic company name**, and a complete **Saudi
National Address** (building, street, district, city, postal code). The
[onboarding user guide](onboarding/user-guide.md) covers these in context.
