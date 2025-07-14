```mermaid
graph LR
    subgraph "Entry Points"
        A[Web Page]
        B[API Endpoint]
        C[Document Event]
    end
    
    subgraph "Processing Layer"
        D[setup.py]
        E[invoice.py]
        F[api.py]
    end
    
    subgraph "Core Classes"
        G[ZatcaInvoiceData]
        H[ZatcaInvoiceValidate]
        I[ZatcaXmlGenerator]
    end
    
    subgraph "Support Modules"
        J[utils.py]
        K[keys.py]
        L[request.py]
    end
    
    A --> D
    B --> F
    C --> E
    E --> G
    G --> H
    G --> I
    D --> K
    F --> L