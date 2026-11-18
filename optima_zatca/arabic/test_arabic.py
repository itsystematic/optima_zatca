"""Site-free tests for the Arabic catalog tooling (python -m unittest optima_zatca.arabic.test_arabic)."""

import unittest

from babel.messages.catalog import Catalog

from optima_zatca.arabic import catalog, export, harvest, load_order


def _po(*messages):
	po = Catalog(locale="ar")
	for msgid, msgstr, *context in messages:
		po.add(msgid, msgstr, context=context[0] if context else None)
	return po


class TestBuildRows(unittest.TestCase):
	def test_new_differs_and_same(self):
		# A source entry equal to ar.po must not reach the reviewer; new and different ones must.
		current = {("Approved", None): "معتمد"}
		sources = [("optima_hr:translations/ar.csv", {("Approved", None): "معتمد", ("Shift", None): "وردية", ("Approved", "x"): ""})]
		rows = harvest.build_rows(current, sources)
		self.assertEqual([(r[0], r[4]) for r in rows], [(("Shift", None), "new")])

		rows = harvest.build_rows(current, [("from:daad.po", {("Approved", None): "تمت الموافقة"})])
		self.assertEqual(rows, [(("Approved", None), "from:daad.po", "تمت الموافقة", "معتمد", "differs")])

	def test_missing_only_when_nobody_translates(self):
		# A core msgid some source translates is `new`, not `missing`; one with no Arabic anywhere is `missing`.
		rows = harvest.build_rows(
			{}, [("frappe:locale/ar.po", {("Search", None): "البحث"})], {("Search", None), ("Kanban", None)}
		)
		self.assertEqual({(r[0][0], r[4]) for r in rows}, {("Search", "new"), ("Kanban", "missing")})


class TestApplyRows(unittest.TestCase):
	def test_only_approved_rows_are_merged(self):
		# Unreviewed rows must never change ar.po.
		po = _po(("Approved", "تمت الموافقة"))
		rows = [
			{"msgid": "Approved", "msgctxt": "", "found_translation": "معتمد", "approved": "yes"},
			{"msgid": "Shift", "msgctxt": "", "found_translation": "وردية", "approved": ""},
			{"msgid": "Back", "msgctxt": "onboarding", "found_translation": "رجوع", "approved": "Yes"},
			{"msgid": "Empty", "msgctxt": "", "found_translation": "", "approved": "yes"},
		]
		self.assertEqual(harvest.apply_rows(po, rows), (1, 1, ["Empty"]))
		self.assertEqual(po.get("Approved").string, "معتمد")
		self.assertIsNone(po.get("Shift"))
		self.assertEqual(po.get("Back", "onboarding").string, "رجوع")


class TestExportSelection(unittest.TestCase):
	def test_only_translated_core_msgids_go_to_daad(self):
		# No Optima string may reach the public DaaD app.
		po = _po(("Sales Invoice", "فاتورة مبيعات"), ("Commercial Register", "السجل التجاري"), ("Back", "رجوع", "onboarding"), ("Item", ""))
		core = {("Sales Invoice", None), ("Back", None), ("Item", None)}
		self.assertEqual([m.id for m in export.select_core(po, core)], ["Sales Invoice"])


class TestPlaceholders(unittest.TestCase):
	def test_lost_placeholder_is_reported(self):
		po = _po(("Row {0}: {1}", "الصف {0}: {1}"), ("{0} of {1}", "{0} من"), ("%(count)s rows", "%(count)s صفوف"))
		self.assertEqual([p[0] for p in catalog.placeholder_problems(po)], ["{0} of {1}"])


class TestLoadOrder(unittest.TestCase):
	def test_good_order_is_silent(self):
		self.assertEqual(load_order.problems(["frappe", "erpnext", "hrms", "optima_zatca", "optima_feed"]), [])

	def test_core_app_after_optima_zatca_warns(self):
		# hrms loading after optima_zatca would override its Arabic.
		found = load_order.problems(["frappe", "erpnext", "optima_zatca", "hrms"])
		self.assertEqual(len(found), 1)
		self.assertIn("before hrms", found[0])

	def test_daad_installed_warns(self):
		found = load_order.problems(["frappe", "erpnext", "optima_zatca", "daad"])
		self.assertEqual(len(found), 1)
		self.assertIn("DaaD", found[0])

	def test_site_without_optima_zatca_is_ignored(self):
		self.assertEqual(load_order.problems(["frappe", "daad"]), [])


if __name__ == "__main__":
	unittest.main()
