"""
Installation and setup functions for Optima ZATCA app.
Called after app installation via after_install hook.
"""

import frappe
import click
from optima_zatca.setup.add_default_print_format import install_print_formats


def after_install():
	"""
	Setup function called after app installation.
	Creates print formats and other initial configuration.
	"""
	click.secho("Starting Optima ZATCA installation...", fg="cyan")
	install_print_formats()
	frappe.db.commit()
