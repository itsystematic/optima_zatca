"""Sending a register again updates or resumes its stored records instead of adding new ones, and
another environment adds only its own setting."""

import unittest
from unittest.mock import patch

import frappe

from optima_zatca.zatca import setup

COMPANY = "Masar Demo"
BRANCH = {"commercial_register_name": "HQ", "commercial_register_number": "1010101010", "otp": "654321"}


def stored(**overrides):
	return {
		"company": COMPANY,
		"address": "Masar Demo HQ-Billing",
		"setting": "Masar Demo-1010101010",
		"check_csid": 0,
		"check_pcsid": 0,
		"csid_in_other_environment": False,
		**overrides,
	}


def register(stored_register, environment="production", configured=None):
	"""Run saving_branches_data for BRANCH: the {doctype: (name, values)} upserted, the onboard mock,
	and whether the branch was refused."""
	refused = False
	with (
		patch.object(setup.frappe, "conf", {"zatca_onboarding_environment": configured}),
		patch.object(setup, "_load_stored_register", return_value=stored_register),
		patch.object(setup, "_upsert", side_effect=lambda doctype, name, values, **kw: name or doctype) as upsert,
		patch.object(setup, "add_company_to_zatca") as onboard,
		patch.object(setup.frappe, "throw", side_effect=frappe.ValidationError),
		patch.object(setup, "_", side_effect=lambda message: message),
	):
		try:
			setup.saving_branches_data(
				company=COMPANY, tax_id="300000000000003", environment=environment, commercial_register=[BRANCH]
			)
		except frappe.ValidationError:
			refused = True
	return {c.args[0]: (c.args[1], c.args[2]) for c in upsert.call_args_list}, onboard, refused


class TestDecideRegisterAction(unittest.TestCase):
	def test_each_stored_state(self):
		cases = [
			(None, "save"),
			(stored(setting=None, check_csid=None, check_pcsid=None), "save"),
			(stored(), "save"),
			(stored(check_csid=1), "resume"),
			(stored(check_csid=1, check_pcsid=1), "connected"),
			(stored(company="Another Company"), "other_company"),
			(stored(setting=None, check_csid=None, check_pcsid=None, csid_in_other_environment=True), "save_setting"),
			(stored(csid_in_other_environment=True), "save_setting"),
			(stored(check_csid=1, csid_in_other_environment=True), "resume"),
		]
		for stored_register, expected in cases:
			with self.subTest(stored=stored_register):
				self.assertEqual(setup._decide_register_action(stored_register, COMPANY), expected)


class TestRegisterAgain(unittest.TestCase):
	def test_retry_before_the_csid_updates_the_stored_records(self):
		saved, onboard, _ = register(stored())
		self.assertEqual(saved["Address"][0], "Masar Demo HQ-Billing")
		self.assertEqual(saved["Optima Zatca Setting"][0], "Masar Demo-1010101010")
		self.assertEqual(saved["Optima Zatca Setting"][1]["otp"], "654321")
		onboard.assert_called_once_with("Masar Demo-1010101010")

	def test_retry_after_the_csid_resumes_without_writing(self):
		saved, onboard, _ = register(stored(check_csid=1))
		self.assertEqual(saved, {})
		onboard.assert_called_once_with("Masar Demo-1010101010")

	def test_a_refused_register_is_neither_saved_nor_onboarded(self):
		saved, onboard, refused = register(stored(check_csid=1, check_pcsid=1))
		self.assertTrue(refused)
		self.assertEqual(saved, {})
		onboard.assert_not_called()

	def test_another_environment_saves_only_its_own_setting(self):
		saved, onboard, _ = register(
			stored(setting=None, check_csid=None, check_pcsid=None, csid_in_other_environment=True), "simulation"
		)
		self.assertEqual(list(saved), ["Optima Zatca Setting"])
		name, values = saved["Optima Zatca Setting"]
		self.assertIsNone(name)
		self.assertEqual(values["api_endpoints"], "simulation")
		self.assertEqual(values["address"], "Masar Demo HQ-Billing")
		onboard.assert_called_once()

	def test_an_environment_the_site_does_not_offer_is_refused(self):
		saved, onboard, refused = register(None, "sandbox")
		self.assertTrue(refused)
		self.assertEqual(saved, {})
		onboard.assert_not_called()


class TestDecideEnvironment(unittest.TestCase):
	def test_requested_default_and_refused(self):
		cases = [
			("simulation", None, "simulation"),
			("production", None, "production"),
			(None, None, "production"),
			(None, "simulation", "simulation"),
			(None, "sandbox", "sandbox"),
			("sandbox", "sandbox", "sandbox"),
			("sandbox", None, None),
			("sandbox", "simulation", None),
			("staging", None, None),
		]
		for requested, configured, expected in cases:
			with self.subTest(requested=requested, configured=configured):
				self.assertEqual(setup._decide_environment(requested, configured), expected)

	def test_sandbox_is_offered_only_where_configured(self):
		self.assertEqual(setup.onboarding_environments(None), ["simulation", "production"])
		self.assertEqual(setup.onboarding_environments("sandbox"), ["sandbox", "simulation", "production"])
