"""
Installation and setup functions for Optima ZATCA app.
Called after app installation via after_install hook.
"""

import frappe
import os
import click


def after_install():
	"""
	Setup function called after app installation.
	Creates print formats and other initial configuration.
	"""
	click.secho("Starting Optima ZATCA installation...", fg="cyan")
	install_print_formats()
	frappe.db.commit()


def install_print_formats():
	"""
	Install ZATCA Print Formats from template files.
	Reads HTML and CSS from files and creates/updates Print Format documents.
	"""
	print_formats = [
		{
			"name": "Zatca Sales Invoice",
			"doc_type": "Sales Invoice",
			"html_file": "optima_zatca/print_format/zatca_sales_invoice/zatca_sales_invoice.html",
			"css_file": "optima_zatca/print_format/zatca_sales_invoice/zatca_sales_invoice.css",
		}
	]

	for pf_config in print_formats:
		try:
			create_or_update_print_format(
				name=pf_config["name"],
				doctype=pf_config["doc_type"],
				html_file=pf_config["html_file"],
				css_file=pf_config.get("css_file"),
			)
		except Exception as e:
			frappe.log_error(
				message=str(e),
				title=f"Error installing Print Format: {pf_config['name']}"
			)
			click.secho(f"Error installing Print Format '{pf_config['name']}': {str(e)}", fg="red")


def create_or_update_print_format(name, doctype, html_file, css_file=None):
	"""
	Create or update a Print Format by embedding HTML and CSS from files.
	
	This embeds the content in the database so users can see and customize it.
	The separate .html and .css files in git serve as the source of truth.

	Args:
		name: Name of the Print Format
		doctype: DocType this print format is for (e.g., "Sales Invoice")
		html_file: Filename of the HTML template (relative to app root)
		css_file: Optional filename of the CSS file (relative to app root)
	"""
	# Read HTML content from file
	html_path = frappe.get_app_path("optima_zatca", html_file)
	if not os.path.exists(html_path):
		raise FileNotFoundError(f"HTML template file not found: {html_path}")

	with open(html_path, "r", encoding="utf-8") as f:
		html_content = f.read()

	# Read CSS content from file if provided
	css_content = ""
	if css_file:
		css_path = frappe.get_app_path("optima_zatca", css_file)
		if os.path.exists(css_path):
			with open(css_path, "r", encoding="utf-8") as f:
				css_content = f.read()
		else:
			click.secho(f"Warning: CSS file not found: {css_path}", fg="yellow")

	# Check if Print Format exists
	if frappe.db.exists("Print Format", name):
		# Update existing - overwrite with latest from files
		doc = frappe.get_doc("Print Format", name)
		doc.html = html_content
		doc.css = css_content
		doc.disabled = 0
		doc.standard = "Yes"
		doc.flags.ignore_permissions = True
		doc.save()
		click.secho(f"✓ Updated Print Format: {name}", fg="green")
	else:
		# Create new with embedded HTML/CSS
		doc = frappe.get_doc({
			"doctype": "Print Format",
			"name": name,
			"doc_type": doctype,
			"module": "Optima Zatca",
			"standard": "Yes",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"html": html_content,
			"css": css_content,
			"disabled": 0,
			"default_print_language": "en",
			"font_size": 14,
			"line_breaks": 0,
			"margin_top": 15.0,
			"margin_bottom": 15.0,
			"margin_left": 15.0,
			"margin_right": 15.0,
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		click.secho(f"✓ Created Print Format: {name}", fg="green")