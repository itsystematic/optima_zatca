"""
Installation and setup functions for Optima ZATCA app.
Called after app installation via after_install hook.
"""

import frappe
import click

from optima_zatca.setup.setup_vat_system.set_tax_configuration import create_complete_vat_system
from optima_zatca.setup.add_default_print_format import install_print_formats
from optima_zatca.setup.customizations import ensure_customizations, add_standard_data


def after_install():
    """
    Setup function called after app installation.

    Creates the app's customizations (custom fields, property setters, roles),
    print formats, tax configuration, and seed data. This is the single
    self-setup entry point — it was previously (incorrectly) split with the
    after_app_install hook.
    """
    click.secho("🚀 Starting Optima ZATCA installation...", fg="cyan")

    install_print_formats()
    create_complete_vat_system()
    ensure_customizations()
    add_standard_data()

    frappe.db.commit()
    click.secho("✅ Optima ZATCA installation completed!", fg="green")