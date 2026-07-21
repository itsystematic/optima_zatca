"""
Teardown for Optima ZATCA, called before the app is uninstalled.

Removes the schema customizations the app owns (custom fields, property setters,
roles). It does NOT delete field values on existing documents or the app's own
DocTypes — Frappe removes the latter as part of uninstall.
"""

import frappe
import click

from optima_zatca.setup.customizations import remove_customizations


def before_uninstall():
    """Remove ZATCA custom fields, property setters, and roles."""
    click.secho("🧹 Removing Optima ZATCA customizations...", fg="cyan")

    remove_customizations()

    frappe.db.commit()
    click.secho("✅ Optima ZATCA customizations removed.", fg="green")
