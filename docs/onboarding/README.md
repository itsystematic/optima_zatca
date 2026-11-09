# Onboarding — Docs

Everything about connecting a company's device to ZATCA (Fatoora) — the one-time setup that
turns a Commercial Register into a certificate-holding device that can clear and report
invoices.

| Document | For | What it covers |
|----------|-----|----------------|
| [user-guide.md](user-guide.md) | Implementers | Prerequisites, the environment, the wizard steps, reading the progress board, retrying, renewal |
| [reference.md](reference.md) | Developers | Registration and retries, the `add_company_to_zatca` pipeline, CSR generation, the compliance→sample→production CSID stages, the ZATCA calls, the config doctypes, realtime progress |

Onboarding is driven from the wizard at `/zatca-onboarding` and orchestrated by
`zatca/setup.py`. Its state lives on the **Optima Zatca Setting** doctype (one per
**Commercial Register**), and it is resumable via the `check_csid` / `check_pcsid` stage flags.
