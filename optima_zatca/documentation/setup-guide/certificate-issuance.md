```mermaid
    sequenceDiagram
    participant App
    participant ZATCA
    
    App->>ZATCA: Submit CSR + OTP
    ZATCA->>ZATCA: Validate request
    ZATCA->>App: Issue certificate
    App->>App: Store certificate
```