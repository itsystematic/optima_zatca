import click
import frappe


def execute():
	"""Pull in the redesigned ZATCA workspace.

	A fresh install imports the workspace JSON as it is, but an existing site
	already has the record — and Frappe leaves a public workspace alone once it
	exists, on the assumption that a user may have arranged it. That is the right
	default and the wrong outcome here: the old layout buried the onboarding link
	at the bottom of three charts, and worse, pointed it at `/app/zatca-onboarding`,
	a desk page that does not exist. Nothing on the old workspace reached the
	wizard at all.
	"""
	if not frappe.db.exists("DocType", "Workspace"):
		return

	click.secho("Refreshing the ZATCA workspace...", fg="cyan")
	try:
		frappe.reload_doc("optima_zatca", "workspace", "zatca", force=True)
		frappe.db.commit()
		click.secho("ZATCA workspace updated.", fg="green")
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Optima ZATCA: workspace refresh", message=frappe.get_traceback())
		click.secho("Could not refresh the ZATCA workspace; see the error log.", fg="yellow")
