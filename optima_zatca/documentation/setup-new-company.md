## ZATCA Integration Flow

```mermaid
graph TD
    A[Start Setup] --> B[Retrieve Company Data]
    B --> C[Generate CSR & Keys]
    C --> D{Has OTP?<br>Not Checked CSID?}
    
    D -->|Yes| E[Get Compliance Certificate]
    D -->|No| F{CSID Already Valid?}
    
    E --> G[Save Certificate Details]
    G --> H[Send Sample Invoices]
    
    F -->|Yes| H
    F -->|No| I[Mark Setup as Failed]
    
    H --> J{All Sample Invoices<br>Processed?}
    J -->|Yes| K[Get Production Certificate]
    J -->|No| L[Partial Completion]
    
    K --> M[Save Production Credentials]
    L --> M
    
    M --> N{Successfully<br>Configured?}
    N -->|Yes| O[Notify Full Success]
    N -->|No| P[Notify Partial Success]
    
    O --> Q[End]
    P --> Q
    I --> Q

    style D fill:#666,stroke:#bbbbbb
    style I fill:#999,stroke:#fbc02d
    style K fill:#999,stroke:#fbc02d
    style E fill:#666,stroke:#2e7d32
    style L fill:#666,stroke:#2e7d32
    style J fill:#444,stroke:#c62828
    style N fill:#666,stroke:#bbbbbb
    style O fill:#666,stroke:#2e7d32
    style P fill:#666,stroke:#f9a825
    style Q fill:#444,stroke:#333