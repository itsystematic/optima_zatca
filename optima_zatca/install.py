"""
Installation and setup functions for Optima ZATCA app.
Called after app installation via after_install hook.
"""

import frappe
import click

from optima_zatca.setup.setup_vat_system.set_tax_configuration import create_complete_vat_system
from optima_zatca.setup.add_default_print_format import install_print_formats
from optima_zatca.setup.customizations import ensure_customizations, add_standard_data


# The patches that provision a site rather than migrate one.
#
# Frappe marks every entry in `patches.txt` as completed *before* it calls
# `after_install` (see `frappe/installer.py`: `set_all_patches_as_completed` runs
# ahead of the `after_install` hook), so on a fresh install none of these ever
# execute. That is why a newly installed site had no "Sales Invoice Type" records
# — no Normal, no Prepayment, no Adjustment — and therefore a mandatory
# `sales_invoice_type` link field on Sales Invoice with nothing to point at.
#
# Only patches doing work that `after_install` does not already do belong here.
# The rest of `patches.txt` is covered by the calls above: roles and custom
# fields by `ensure_customizations`, the mandatory Item taxes property setter by
# `create_complete_vat_system`, the print format by `install_print_formats`.
#
# They stay in `patches.txt` for sites upgrading from an earlier version, and are
# listed here for sites being created now. Every one of them is idempotent —
# each checks for what it is about to create, or writes with `update=True` — so
# running them in both paths is safe.
PROVISIONING_PATCHES = (
    "optima_zatca.patches.v15.create_prepayment_related_doctypes",
)


def after_install():
    """
    Setup function called after app installation.

    Creates the app's customizations (custom fields, property setters, roles),
    print formats, tax configuration, and the seed and reference data that the
    patches would otherwise only give to an upgrading site. This is the single
    self-setup entry point — it was previously (incorrectly) split with the
    after_app_install hook.
    """
    click.secho("🚀 Starting Optima ZATCA installation...", fg="cyan")

    install_print_formats()
    create_complete_vat_system()
    ensure_customizations()
    add_standard_data()
    # Runs last: the advance payment item it creates needs the selling tax
    # templates put in place by `create_complete_vat_system` above.
    run_provisioning_patches()

    frappe.db.commit()
    click.secho("✅ Optima ZATCA installation completed!", fg="green")


def run_provisioning_patches():
    """Run the idempotent provisioning patches that a fresh install would skip.

    One failure does not abort the rest: these provision independent things, and
    a site that is missing its print format is still better off with its invoice
    types than with neither.
    """
    for module in PROVISIONING_PATCHES:
        try:
            frappe.get_attr(f"{module}.execute")()
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(
                title=f"Optima ZATCA install: {module}",
                message=frappe.get_traceback(),
            )
            click.secho(f"  ⚠️  {module} did not complete; see the error log.", fg="yellow")
