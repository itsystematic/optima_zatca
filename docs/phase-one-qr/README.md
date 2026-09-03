# Phase-1 QR — Docs

The Phase-1 (simplified invoice) **TLV QR** generated at submit, plus the Sales Invoice
lifecycle guards in the same module (submit-gating, cancel/delete blocks).

| Document | For | What it covers |
|----------|-----|----------------|
| [reference.md](reference.md) | Developers | The `on_submit` QR path, the five-field TLV encoding + the 255-byte cap, and the pure cancel/delete guards |

This is an internal subsystem (no user guide) — the QR simply appears on the invoice. Code
lives in `events/sales_invoice.py`; the Phase-2 QR is produced during
[submission](../submission/) instead. Terminology in [Concepts](../concepts.md).
