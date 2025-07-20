## ZATCA work Flow for setup compnay

```mermaid
sequenceDiagram
    participant User
    participant ERPNext
    participant ZATCA_API
    participant Database

    User->>ERPNext: Initiate ZATCA Setup
    ERPNext->>Database: Load Company Settings
    ERPNext->>OpenSSL: Generate CSR/Keys
    OpenSSL-->>ERPNext: Return Crypto Assets
    ERPNext->>ZATCA_API: Submit CSR + OTP
    ZATCA_API-->>ERPNext: Compliance Certificate
    ERPNext->>Database: Store Certificate
    ERPNext->>ZATCA_API: Submit Sample Invoices
    ZATCA_API-->>ERPNext: Invoice Validation Results
    ERPNext->>ZATCA_API: Request Production Cert
    ZATCA_API-->>ERPNext: Production Certificate
    ERPNext->>User: Notify Completion