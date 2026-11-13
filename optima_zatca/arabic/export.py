"""`bench zatca-export-daad --to apps/daad/daad/locale/ar.po`: the community copy of the core Arabic.

DaaD (github.com/itsystematic/daad) is the public app that gives a plain frappe / erpnext / hrms
site our Arabic. Its ar.po is generated from optima_zatca's, never edited by hand: only msgids
that exist in frappe, erpnext and hrms go out, so no Optima string reaches the public app.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import click

from optima_zatca.arabic import catalog


def core_template_keys(apps=catalog.CORE_APPS):
	"""(msgid, msgctxt) the core apps' source declares, extracted fresh by Frappe's own POT builder.

	`frappe.gettext.translate.generate_pot` is what `bench generate-pot-file --app <app>` runs.
	Its writer is swapped for a collector, so the apps' committed main.pot files stay untouched.
	Its `ignore_translatable_strings_from` filter is switched off: erpnext and hrms use it to
	drop strings frappe's committed main.pot already lists, and a stale frappe POT would then
	hide strings erpnext and hrms still use. The union of the three apps needs no dedup.
	"""
	from frappe.gettext import translate

	collected = {}

	def collect(app, po, locale=None):
		collected[app] = po
		return Path(f"<{app}: in memory>")

	with (
		patch.object(translate, "write_catalog", collect),
		patch.object(translate, "_get_ignored_strings", lambda app: set()),
		patch("builtins.print"),
	):
		for app in apps:
			translate.generate_pot(app)

	keys = set()
	for po in collected.values():
		keys |= {(catalog.single(m.id), m.context or None) for m in po if m.id}
	return keys


def select_core(source, core_keys):
	"""The translated messages of `source` whose (msgid, msgctxt) is a core key."""
	return [
		message
		for message in source
		if message.id
		and not message.fuzzy
		and catalog.single(message.string)
		and (catalog.single(message.id), message.context or None) in core_keys
	]


def export(target, core_keys=None):
	"""Rewrite `target` with optima_zatca's Arabic for core msgids only, keeping its header."""
	target = Path(target)
	source = catalog.load(catalog.po_path())
	core_keys = core_template_keys() if core_keys is None else core_keys
	selected = select_core(source, core_keys)

	out = catalog.load(target) if target.exists() else source
	for message in list(out):
		if message.id:
			out.delete(message.id, context=message.context)
	for message in selected:
		out.add(message.id, message.string, context=message.context)
	out.revision_date = datetime.now()

	catalog.write(target, out)
	_, problems = catalog.validate(target)
	click.echo(
		f"{target}: {len(selected)} core entries of {len(core_keys)} core msgids "
		f"({len(source) - len(selected)} non-core or untranslated left out); "
		f"{len(problems)} placeholder warnings"
	)
	return len(selected), problems
