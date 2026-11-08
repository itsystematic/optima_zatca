"""A retried onboarding keeps the key its compliance certificate was issued for."""

import unittest
from unittest.mock import MagicMock, patch

from optima_zatca.zatca import setup


def run_onboarding(settings):
	with (
		patch.object(setup.frappe.local, "site", "test.site", create=True),
		patch.object(setup.frappe, "get_doc", return_value=settings),
		patch.object(setup, "get_csr_identity", return_value={}),
		patch.object(setup, "GenerateCSR") as generate,
		patch.object(setup, "get_certificate"),
		patch.object(setup, "send_sample_sales_invoices"),
		patch.object(setup, "get_production_certificate"),
		patch.object(setup, "saving_data_to_company") as save,
		patch.object(setup, "notify_completion_status"),
		patch.object(setup, "handle_zatca_error") as failed,
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
