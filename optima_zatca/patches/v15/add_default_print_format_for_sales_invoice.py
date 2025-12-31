import click
import frappe
from optima_zatca.install import install_print_formats


def execute():
    click.secho("Adding default print format for Sales Invoice...", fg="cyan")
    try:
        install_print_formats()
        frappe.db.commit()
        click.secho("Default print format for Sales Invoice added successfully.", fg="green")
    except Exception as e:
        frappe.db.rollback()
        click.secho(f"Error adding default print format for Sales Invoice: {str(e)}", fg="red")
        raise