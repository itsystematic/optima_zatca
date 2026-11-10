# Onboarding — User Guide

A plain-language guide for implementers to connecting a company's devices to ZATCA
(Fatoora). For the technical flow and the fields it writes, see [reference.md](reference.md).

Onboarding is a **one-time** activity per device. You do it once for each **commercial
register** (each branch/device that will issue invoices), and after it succeeds that register
can clear and report invoices. You do **not** repeat it for every invoice.

The guided **onboarding wizard** lives at **`/zatca-onboarding`** on your site (the ZATCA
workspace's **Set up e-invoicing** shortcut opens it). It walks you through the steps below and
then shows a live progress board, one row per register.

---

## Before you start

Have these ready. The wizard creates the Commercial Register and its address for you, so they
do not need to exist yet.

| You need | For | Rules the wizard checks |
|----------|-----|-------------------------|
| The company's **Arabic name** | The company | Required |
| The company's **VAT number** | The company | 15 digits, starting and ending with 3 |
| Each register's **name** and **CRN** | Each register | CRN is 10 digits, and not already added |
| Each register's **Saudi National Address** | Each register | Short address, building no (4 digits), street, secondary no, district, city, postal code (5 digits) |
| One **OTP** per register from the Fatoora portal | Each register | 6 digits |

> **One OTP, one register.** Each OTP you generate in the Fatoora portal authorizes one
> register, and it expires quickly. Generate them just before the Review step.

---

## The environment

Every register connects to one of three ZATCA environments:

| Environment | Use it for |
|-------------|-----------|
| **sandbox** | First trials and development — throwaway certificates |
| **simulation** | Pre-production rehearsal that mirrors production behavior |
| **production** | The live connection that issues real, legally-valid invoices |

You choose **simulation** or **production** on the Review step, and the OTPs must come from the
matching Fatoora portal. **Sandbox** is offered only on a site whose administrator set
`zatca_onboarding_environment` to `sandbox` in the site configuration; that key also preselects
the environment.

A register can be connected in more than one environment, side by side: rehearse in simulation,
then connect the same register to production. Each environment issues its own certificate — a
simulation certificate can't clear production invoices — and the register list shows each
environment's status:

| Status | Meaning | Action offered |
|--------|---------|----------------|
| **Connected** | Production CSID issued | — |
| **In progress** | Compliance CSID issued, sample invoices or production CSID still to do | **Resume**, without an OTP |
| **Not connected** | Saved, but ZATCA refused the compliance CSID | **Resume**, with a new OTP |

An environment the register has not been connected in yet appears as **Connect to …**. Once
any environment has a compliance CSID, the register's details are in that certificate, so the
wizard sends them as they are.

> **Which environment signs your invoices.** A register's first connected environment signs
> its invoices, marked **Invoices** in the list. Connecting a second environment does not move
> them: to switch, tick **Use for Invoices** on that environment's Optima Zatca Setting. Only a
> connected setting can be ticked, and ticking it unticks the register's other settings.
>
> **Upgrading a site onboarded before environments.** Its settings arrive unticked. Tick **Use
> for Invoices** once on each register's Optima Zatca Setting, or Send to ZATCA refuses that
> register's invoices.

---

## The steps

```mermaid
flowchart LR
    A["Phase"] --> B["One or several<br/>registers"]
    B --> C["Company"]
    C --> D["Registers"]
    D --> E["Review<br/>+ OTPs"]
    E --> F["Progress<br/>board"]
    F --> G["Done"]
```

1. **Phase.** Choose **Phase 1** (QR code only) or **Phase 2** (integration with ZATCA).
2. **How many registers.** **Main CRN** for a single register, or **Multiple CRNs** for a main
   register and its branches.
3. **Company.** Pick the company and enter its Arabic name and VAT number.
4. **Registers.** Add each register's name, CRN and National Address.
5. **Review.** Check everything, confirm the data is correct, and enter one OTP per register.
6. **Progress.** Each register goes through three stages on its own row:
   - the **compliance certificate** (CSID),
   - six **test invoices**,
   - the **production certificate** (PCSID).

   The registers are processed one after another.
7. **Done.** When the board finishes, the last page shows how many registers are live.

---

## Reading the progress board

| A register's row shows | Meaning | What to do |
|------------------------|---------|-----------|
| **Waiting** | Its turn has not come yet | Nothing |
| **Requesting compliance certificate** / **Test invoice n of 6** / **Requesting production certificate** | That stage is running | Wait |
| **Connected** | Production certificate obtained; the register is live | Nothing — start invoicing |
| **Compliance certificate refused** | ZATCA refused the OTP or the data | **Retry** asks for a fresh OTP |
| **Test invoice rejected** / **Production certificate refused** | A later stage failed | **Retry** |
| **Could not start** | The request was refused before any stage ran, e.g. a CRN that belongs to another company | Fix the cause, then retry |

**Retrying is safe.** A retry picks up where that register stopped and never creates a second
copy of its records. Registers that are already connected stay connected while you retry the
others.

> **Details are fixed after the compliance certificate.** The register's name, VAT number and
> address are written into that certificate. A retry after it reuses them as they were, so
> correct any mistake before the certificate is issued.

---

## After onboarding

- **Default register.** The wizard does not choose one. To have new sales invoices pick a
  register automatically, tick **Is Default** on that register's **Commercial Register** in the
  desk. A company can have only one.
- **Renewing a certificate.** Production certificates expire. The **Optima Zatca Setting** form
  has a **Renew Production Certificate** button (under **Setup Zatca**), which needs a fresh OTP
  from the Fatoora portal entered on that form first.

> **Renewal does not work yet.** It currently fails before it reaches ZATCA. Until it is fixed,
> contact support when a production certificate nears expiry.
