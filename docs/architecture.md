# Architecture

```mermaid
flowchart LR
  subgraph Browser
    UI[HTML + CSS + JavaScript<br/>Guest / Front office / Manager / Admin views]
  end
  subgraph Flask["Flask API (backend/app.py)"]
    AUTH[Auth + role checks]
    BOOK[Bookings, rooms, invoices]
    OPS[Service requests, housekeeping, reviews]
    AIM[ai.py]
  end
  subgraph AI["AI layer"]
    ML[scikit-learn: occupancy forecast, price suggestions, review NLP]
    GEN[Gemini API: reply drafts, insights, multilingual concierge]
  end
  DB[(MySQL<br/>users, rooms, bookings, requests,<br/>reviews, invoices, price_overrides)]
  UI -- JSON over HTTP + bearer token --> AUTH
  AUTH --> BOOK & OPS & AIM
  BOOK & OPS --> DB
  AIM --> ML & GEN
  ML --> DB
```

Data flow for dynamic pricing: bookings table -> daily occupancy (pandas) -> GradientBoosting forecast + festival flag -> price multiplier -> manager approval -> `price_overrides` -> prices shown to guests in availability search.
