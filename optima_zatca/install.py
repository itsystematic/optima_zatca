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
    # Both of these depend on what runs above: the advance payment item needs
    # the selling tax templates from `create_complete_vat_system`, and the grant
    # needs the "Zatca Manager" role from `ensure_customizations`.
    run_provisioning_patches()
    grant_onboarding_permissions()

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


#: The wizard's own records. A Zatca Manager runs the onboarding, so they need to
#: read and write these, but the role is created by a provisioning step that runs
#: after doctypes are synced — so the grant cannot live in the doctype JSON.
ONBOARDING_DOCTYPES = ("Zatca Onboarding Setup", "Zatca Onboarding Run")


def grant_onboarding_permissions():
    """Give Zatca Manager access to the onboarding records, once the role exists."""
    from frappe.permissions import add_permission, update_permission_property

    if not frappe.db.exists("Role", "Zatca Manager"):
        return

    for doctype in ONBOARDING_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": "Zatca Manager"}):
            continue
        try:
            add_permission(doctype, "Zatca Manager", 0)
            for right in ("read", "write", "create"):
                update_permission_property(doctype, "Zatca Manager", 0, right, 1)
        except Exception:
            frappe.log_error(
                title=f"Optima ZATCA install: permissions for {doctype}",
                message=frappe.get_traceback(),
            )
