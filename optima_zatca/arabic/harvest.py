"""`bench --site <site> zatca-arabic-harvest`: Arabic found outside optima_zatca, for human review.

The harvest never changes ar.po by itself. It writes a review CSV; a person marks rows
`approved = yes`, and `--apply <csv>` merges only those rows.

Statuses:
  new      the source has Arabic for a msgid ar.po does not translate
  differs  the source's Arabic differs from ar.po's
  missing  a frappe / erpnext / hrms msgid that no source and not ar.po translates
"""

import csv
from pathlib import Path

import click

from optima_zatca.arabic import catalog

FIELDS = ["msgid", "msgctxt", "source", "found_translation", "zatca_translation", "status", "approved"]
STATUSES = ("new", "differs", "missing")


def build_rows(current, sources, core_msgids=()):
	"""Review rows for each source entry that is new to ar.po or differs from it.

	`current` is {(msgid, msgctxt): msgstr} of ar.po, translated entries only.
	`sources` yields (label, entries) with the same shape; an empty msgstr means untranslated.
	`core_msgids` are the (msgid, msgctxt) keys of frappe / erpnext / hrms; those with no Arabic
	anywhere become `missing` rows.
	"""
	rows, seen = [], set()
	for label, entries in sources:
		for key, found in entries.items():
			if not found:
				continue
			seen.add(key)
			existing = current.get(key)
			if existing == found:
				continue
			rows.append((key, label, found, existing or "", "differs" if existing else "new"))

	rows += [
		(key, "core", "", "", "missing")
		for key in sorted(core_msgids, key=lambda k: (k[0], k[1] or ""))
		if key not in current and key not in seen
	]
	return rows


def installed_sources(apps):
	"""(label, entries) for each Arabic source on this site outside optima_zatca."""
	import frappe

	for app in apps:
		root = Path(frappe.get_app_path(app))
		po_path = root / "locale" / "ar.po"
		if po_path.exists():
			yield f"{app}:locale/ar.po", catalog.read_entries(po_path)
		csv_path = root / "translations" / "ar.csv"
		if csv_path.exists():
			yield f"{app}:translations/ar.csv", catalog.read_csv(csv_path)

	records = frappe.get_all(
		"Translation", filters={"language": "ar"}, fields=["source_text", "translated_text", "context"]
	)
	yield "Translation", {(r.source_text, r.context or None): r.translated_text for r in records}


def core_msgids(apps):
	"""(msgid, msgctxt) of the core apps' committed templates (main.pot, else their ar.po)."""
	import frappe

	keys = set()
	for app in catalog.CORE_APPS:
		if app not in apps:
			continue
		locale_dir = Path(frappe.get_app_path(app)) / "locale"
		for name in ("main.pot", "ar.po"):
			if (locale_dir / name).exists():
				keys |= set(catalog.read_entries(locale_dir / name))
				break
	return keys


def write_review(rows, target, statuses=STATUSES):
	target = Path(target)
	target.parent.mkdir(parents=True, exist_ok=True)
	with open(target, "w", newline="", encoding="utf-8") as f:
		writer = csv.writer(f)
		writer.writerow(FIELDS)
		for (msgid, msgctxt), label, found, existing, status in rows:
			if status in statuses:
				writer.writerow([msgid, msgctxt or "", label, found, existing, status, ""])
	return target


def harvest(from_po=None, statuses=STATUSES, target=None):
	"""Write the review CSV. With `from_po`, that PO file (e.g. a DaaD release) is the only source."""
	import frappe
	from frappe.utils import today

	current = {key: value for key, value in catalog.read_entries(catalog.po_path()).items() if value}
	apps = frappe.get_installed_apps()
	if from_po:
		sources = [(f"from:{Path(from_po).name}", catalog.read_entries(from_po))]
		core = set()
	else:
		sources = installed_sources([app for app in apps if app != catalog.APP])
		core = core_msgids(apps) if "missing" in statuses else set()

	rows = build_rows(current, sources, core)
	name = today()
	if from_po:
		name += f"-from-{Path(from_po).stem}"
	if tuple(statuses) != STATUSES:
		name += "-" + "-".join(statuses)
	target = target or Path(frappe.get_app_path(catalog.APP)) / "translations_review" / f"{name}.csv"
	write_review(rows, target, statuses)

	counts = {status: sum(1 for row in rows if row[4] == status) for status in statuses}
	click.echo(f"{target}: {sum(counts.values())} rows, {counts}")
	return target, counts


def apply_rows(po, rows):
	"""Merge reviewed rows with approved = yes into a babel catalog. Returns (added, updated, skipped)."""
	added = updated = 0
	skipped = []
	for row in rows:
		if (row.get("approved") or "").strip().lower() != "yes":
			continue
		msgid, msgctxt = row.get("msgid"), row.get("msgctxt") or None
		msgstr = (row.get("found_translation") or "").strip()
		if not msgid or not msgstr:
			skipped.append(msgid)
			continue
		message = po.get(msgid, msgctxt)
		if message is None:
			po.add(msgid, msgstr, context=msgctxt)
			added += 1
		elif catalog.single(message.string) != msgstr or message.fuzzy:
			message.string = msgstr
			message.flags.discard("fuzzy")
			updated += 1
	return added, updated, skipped


def apply_file(path):
	"""Merge only rows with approved = yes into ar.po, validate it, then recompile the MO."""
	po_path = catalog.po_path()
	po = catalog.load(po_path)
	with open(path, newline="", encoding="utf-8") as f:
		added, updated, skipped = apply_rows(po, csv.DictReader(f))

	catalog.write(po_path, po)
	_, problems = catalog.validate(po_path)
	catalog.compile_mo()
	for msgid in skipped:
		click.echo(f"Skipped, no translation: {msgid!r}")
	click.echo(
		f"Added {added}, updated {updated}; {len(problems)} placeholder warnings. "
		"Run bench --site <site> clear-cache to see them."
	)
	return added, updated
