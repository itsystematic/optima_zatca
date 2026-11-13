"""Read, check and write the Arabic catalog, `optima_zatca/locale/ar.po`.

optima_zatca's ar.po is the only Arabic file of the Optima suite: it holds the Arabic for
frappe, erpnext, hrms and every Optima app. Frappe compiles it to an MO file and loads it after
the apps listed before optima_zatca in Installed Applications, so its wording wins over theirs.
"""

import re
from pathlib import Path

from babel.messages.pofile import read_po, write_po

APP = "optima_zatca"
LOCALE = "ar"
CORE_APPS = ("frappe", "erpnext", "hrms")

# Positional ({0}) and named (%(name)s) placeholders must survive translation, or Frappe's
# format() call raises or drops a value. A bare %s is too common in prose to check reliably.
_PLACEHOLDER = re.compile(r"\{\d+\}|%\([A-Za-z_]+\)s")


def single(value):
	"""A message's id or string; plural entries keep their first form."""
	return value[0] if isinstance(value, (list, tuple)) else value


def po_path():
	import frappe

	return Path(frappe.get_app_path(APP)) / "locale" / f"{LOCALE}.po"


def load(path):
	"""The babel Catalog of a PO or POT file."""
	with open(path, "rb") as f:
		return read_po(f)


def entries(catalog):
	"""{(msgid, msgctxt): msgstr}. Untranslated and fuzzy entries have an empty msgstr."""
	return {
		(single(message.id), message.context or None): ""
		if message.fuzzy
		else (single(message.string) or "")
		for message in catalog
		if message.id
	}


def read_entries(path):
	return entries(load(path))


def read_csv(path):
	"""{(msgid, msgctxt): msgstr} from a Frappe translation CSV, read the way Frappe loads it."""
	from frappe.translate import read_csv_file
	from frappe.utils import strip

	found = {}
	for row in read_csv_file(str(path)):
		if len(row) not in (2, 3):
			continue
		msgid = row[0].replace("\\n", "\n")
		msgstr = strip(row[1].replace("\\n", "\n"))
		if msgid and msgstr:
			found[(msgid, (row[2] or None) if len(row) == 3 else None)] = msgstr
	return found


def placeholder_problems(catalog):
	"""(msgid, msgctxt, msgstr) of translations whose placeholders differ from the source."""
	problems = []
	for message in catalog:
		msgid, msgstr = single(message.id), single(message.string)
		if not msgid or not msgstr or message.fuzzy:
			continue
		if sorted(_PLACEHOLDER.findall(msgid)) != sorted(_PLACEHOLDER.findall(msgstr)):
			problems.append((msgid, message.context or "", msgstr))
	return problems


def validate(path):
	"""Parse the file the way Frappe compiles it and list placeholder mismatches.

	Raises if the file does not parse or has no translations; returns the mismatch list,
	which is a warning only because some catalogs inherit such entries from Crowdin.
	"""
	from babel.messages.mofile import write_mo
	from io import BytesIO

	catalog = load(path)
	translated = sum(1 for message in catalog if message.id and single(message.string))
	if not translated:
		raise ValueError(f"{path}: no translated entries")
	write_mo(BytesIO(), catalog)  # the same step Frappe's compile runs; raises on a broken catalog
	return catalog, placeholder_problems(catalog)


def write(path, catalog):
	"""Write a catalog the way Frappe writes its own (sorted, no wrapping), then re-read it."""
	path = Path(path)
	path.parent.mkdir(parents=True, exist_ok=True)
	with open(path, "wb") as f:
		write_po(f, catalog, sort_output=True, ignore_obsolete=True, width=None)
	load(path)  # refuse to report success on a file that does not parse
	return path


def compile_mo():
	"""Recompile optima_zatca's MO file so the running site picks up the new Arabic."""
	from frappe.gettext.translate import _compile_translation

	_compile_translation(APP, LOCALE, force=True)
