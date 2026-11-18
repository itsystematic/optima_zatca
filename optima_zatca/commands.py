"""bench commands for optima_zatca's Arabic catalog (locale/ar.po)."""

import os

import click
from frappe.commands import get_site, pass_context


def _bench_path(path):
	"""bench runs commands from sites/; a relative path is read from there, then from the bench."""
	if not path or os.path.isabs(path) or os.path.exists(path):
		return path and os.path.abspath(path)
	from frappe.utils import get_bench_path

	return os.path.join(get_bench_path(), path)


def _existing_file(ctx, param, value):
	path = _bench_path(value)
	if path and not os.path.isfile(path):
		raise click.BadParameter(f"File {value!r} does not exist.")
	return path


@click.command("zatca-arabic-harvest", help="Write a review CSV of Arabic found outside optima_zatca, or merge approved rows")
@click.option("--apply", "apply_path", callback=_existing_file, help="Reviewed CSV: merge rows with approved = yes")
@click.option("--from", "from_po", callback=_existing_file, help="Review this PO file (e.g. a DaaD release) instead of the site's apps")
@click.option("--status", "statuses", multiple=True, type=click.Choice(["new", "differs", "missing"]), help="Only write rows with this status (repeatable)")
@pass_context
def zatca_arabic_harvest(context, apply_path=None, from_po=None, statuses=()):
	import frappe

	from optima_zatca.arabic import harvest

	frappe.init(site=get_site(context))
	frappe.connect()
	try:
		if apply_path:
			harvest.apply_file(apply_path)
		else:
			harvest.harvest(from_po=from_po, statuses=statuses or harvest.STATUSES)
	finally:
		frappe.destroy()


@click.command("zatca-export-daad", help="Write the core (frappe/erpnext/hrms) part of optima_zatca's ar.po to DaaD's ar.po")
@click.option("--to", "target", required=True, help="e.g. apps/daad/daad/locale/ar.po")
def zatca_export_daad(target):
	from optima_zatca.arabic import export

	export.export(_bench_path(target))


commands = [zatca_arabic_harvest, zatca_export_daad]
