# Per-Item Tax & Rounding — Docs

The ZATCA-compliant per-item tax subsystem — the `Saudi Arabia` regional override that computes
per-line tax for the UBL XML, and the tax-inclusive rounding behavior it entails.

| Document | For | What it covers |
|----------|-----|----------------|
| [reference.md](reference.md) | Developers | The regional override, per-item calculation (exclusive vs inclusive/subtraction), the custom fields, and the tax-inclusive 0.01 rounding trap |
| [rounding-reconciliation-proposal.md](rounding-reconciliation-proposal.md) | Developers | A **pending, unimplemented** design proposal to reconcile per-item tax with ERPNext's tax table |

This is an internal subsystem (no user guide) — tax is computed automatically. The tax-account
and item-tax-template **configuration** an implementer sets up lives in [setup](../setup/). Tax
categories (S / Z / E / O) are defined in [Concepts](../concepts.md).
