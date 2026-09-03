# Onboarding — Docs

Everything about connecting a company's device to ZATCA (Fatoora) — the one-time setup that
turns a Commercial Register into a certificate-holding device that can clear and report
invoices.

| Document | For | What it covers |
|----------|-----|----------------|
| [user-guide.md](user-guide.md) | Implementers | Prerequisites, choosing the environment, the wizard steps, reading the result, renewal |
| [reference.md](reference.md) | Developers | The `add_company_to_zatca` pipeline, CSR generation, the compliance→sample→production CSID stages, the config doctypes, realtime progress |

Onboarding is orchestrated by `zatca/setup.py` and driven from the React wizard at
`/zatca-onboarding`. Its state lives on the **Optima Zatca Setting** doctype (one per
**Commercial Register**), and it is resumable via the `check_csid` / `check_pcsid` stage flags.
