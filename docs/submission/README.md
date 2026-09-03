# Submission — Docs

Everything about sending a Sales Invoice to ZATCA in Phase 2 — clearance for standard (B2B)
invoices, reporting for simplified (B2C) invoices, and the full audit trail of every attempt.

| Document | For | What it covers |
|----------|-----|----------------|
| [user-guide.md](user-guide.md) | Accountants & implementers | The **Send to ZATCA** button, clearance vs reporting, reading Success/Warning/Failed, retrying, the cancel/delete block |
| [reference.md](reference.md) | Developers | The `send_to_zatca` → `submit_sales_invoice_to_zatca` pipeline, the pure `_decide_*` outcome logic, endpoints, and the Optima Zatca Logs record |

Submission is orchestrated by `zatca/submission_workflow.py` behind the single whitelisted
entry point `zatca/invoice.py::send_to_zatca`. New to the ZATCA vocabulary? Start with
[Concepts](../concepts.md).
