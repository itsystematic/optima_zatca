"""A retried onboarding keeps the key its compliance certificate was issued for, and a register's
first connected setting is the one that signs its invoices."""

import unittest
from unittest.mock import MagicMock, patch

from optima_zatca.zatca import setup


def pass_every_sample_invoice(settings, setting_updates):
	setting_updates.update({field: True for field in setup.SAMPLE_INVOICE_FIELDS})


def run_onboarding(settings, invoices_pass=False, register_has_invoice_setting=False):
	with (
		patch.object(setup.frappe.local, "site", "test.site", create=True),
		patch.object(setup.frappe, "get_doc", return_value=settings),
		patch.object(setup, "get_csr_identity", return_value={}),
		patch.object(setup, "GenerateCSR") as generate,
		patch.object(setup, "get_compliance_certificate"),
		patch.object(setup, "send_sample_sales_invoices", side_effect=pass_every_sample_invoice if invoices_pass else None),
		patch.object(setup.frappe, "db", MagicMock(**{"exists.return_value": register_has_invoice_setting})),
		patch.object(setup, "get_production_certificate"),
		patch.object(setup, "saving_data_to_setting") as save,
		patch.object(setup, "notify_completion_status"),
		patch.object(setup, "notify_failure_status") as failed,
	):
		generate.return_value.get_generated_details.return_value = {"private_key": "NEW", "csr": "CSR"}
		setup.add_company_to_zatca(settings.name)
	failed.assert_not_called()
	return generate, save


class TestOnboardingRetry(unittest.TestCase):
	def test_first_run_generates_the_key(self):
		generate, save = run_onboarding(MagicMock(check_csid=0, check_pcsid=0, otp="123345"))
		generate.assert_called_once()
		self.assertEqual(save.call_args.args[1]["private_key"], "NEW")

	def test_retry_after_the_compliance_csid_keeps_the_stored_key(self):
		generate, save = run_onboarding(MagicMock(check_csid=1, check_pcsid=0, otp="123345"))
		generate.assert_not_called()
		self.assertNotIn("private_key", save.call_args.args[1])


class TestInvoiceSetting(unittest.TestCase):
	def test_the_first_connected_setting_of_a_register_signs_its_invoices(self):
		_, save = run_onboarding(MagicMock(check_csid=1, check_pcsid=0, otp="123345"), invoices_pass=True)
		self.assertEqual(save.call_args.args[1]["use_for_invoices"], 1)

	def test_a_later_environment_leaves_the_invoices_where_they_are(self):
		_, save = run_onboarding(
			MagicMock(check_csid=1, check_pcsid=0, otp="123345"), invoices_pass=True, register_has_invoice_setting=True
		)
		self.assertNotIn("use_for_invoices", save.call_args.args[1])
