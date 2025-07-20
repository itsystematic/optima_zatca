## ZATCA CSR Generation Flow

```mermaid
graph TD
    A[Initialize GenerateCSR] --> B[Validate Inputs]
    B --> C{All Mandatory Fields Present?}
    C -->|Yes| D[Generate Required Fields]
    C -->|No| E[Throw Validation Error]
    
    D --> F[Create Private Key]
    F --> G[Generate Config File]
    G --> H[Generate CSR]
    H --> I[Create Public Key]
    
    I --> J{Files Created Successfully?}
    J -->|Yes| K[Read Generated Files]
    J -->|No| L[Throw OpenSSL Error]
    
    K --> M[Return CSR Details]
    L --> M
    
    style C fill:#666,stroke:#fbc02d
    style J fill:#666,stroke:#fbc02d
    style E fill:#f66,stroke:#c62828
    style L fill:#f66,stroke:#c62828
    style M fill:#345718,stroke:#2e7d32

    subgraph "Validation Phase"
        B
        C
        E
    end
    
    subgraph "Generation Phase"
        D
        F
        G
        H
        I
    end
    
    subgraph "Output Phase"
        J
        K
        L
        M
    end