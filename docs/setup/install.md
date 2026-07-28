# Install & Migrate

Developer reference for how `optima_zatca` installs its customizations and evolves them on
existing sites. For the post-install configuration an implementer does, see
[configuration.md](configuration.md).

---

## Fresh install — `after_install`

`hooks.py` wires `after_install = "optima_zatca.install.after_install"`, which runs (in order):

| Step | Function | Creates |
|------|----------|---------|
| 1 | `install_print_formats` | The **Zatca Sales Invoice** print format |
| 2 | `create_complete_vat_system` | VAT accounts + the Item Tax Templates (when VAT accounts exist) |
| 3 | `ensure_customizations` | Custom fields + property setters (`setup/customizations.py`) |
| 4 | `add_standard_data` | Seed data — Sales Invoice Types, Tax Categories, Registration Types |

`after_install` is the **single self-setup entry point**. The `after_app_install` hook is
intentionally left disabled (reserved for reacting to *other* apps being installed).

> **Fresh-site caveat.** `create_complete_vat_system` only builds the Item Tax Templates when VAT
> accounts already exist, so a bare site can have none — the reason the site-agnostic test
> helpers fabricate their own (see the app [CLAUDE.md](../../CLAUDE.md) "Testing rules").

---

## Existing sites — `patches.txt`

Migrations run the `post_model_sync` patches, in this order:

| Patch (`optima_zatca.patches.v15.*`) | Does |
|--------------------------------------|------|
| `create_zatca_additoinal_role` | Adds the ZATCA role |
| `create_prepayment_related_doctypes` | Creates Prepayment Invoice / Prepayment Details |
| `create_prepayment_fields` | Adds the prepayment custom fields to Sales Invoice |
| `add_default_print_format_for_sales_invoice` | Installs the print format on already-installed sites |
| `set_item_taxes_reqd` | Makes the Item `taxes` table mandatory |
| `set_prepayment_percentage_precision` | Raises the mirror `adjustment_percentage` precision to 9 dp |

The last one is the going-forward fix for the [prepayment precision
trap](../prepayment/reference.md#the-precision-invariant-one-number-four-places--all-9-dp).

---

## After changing wiring

| You changed | Run |
|-------------|-----|
| `hooks.py` / fixtures / custom fields | `bench --site <site> clear-cache` then `bench --site <site> migrate` |
| Python | `bench restart` |
| `public/js` | `bench build --app optima_zatca` |

The customizations (`setup/customizations.py`) also carry `PERCENTAGE_PRECISION = 9`, one of the
four layers that must stay in sync — see [prepayment/reference.md](../prepayment/reference.md).
