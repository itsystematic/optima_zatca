"""A sample invoice that fails before ZATCA answers is logged and reported as unchecked, never as
rejected by ZATCA."""

import unittest
from unittest.mock import MagicMock, patch

import frappe

from optima_zatca.zatca import demo

BLANK_VAT_NUMBER = AttributeError("'NoneType' object has no attribute 'encode'")


class TestSampleInvoiceLocalError(unittest.TestCase):
	def test_a_build_error_is_logged_and_not_reported_as_a_rejection(self):
		settings = frappe._dict(name="OZS-TEST", commercial_register="1010101010", invoice_one=1)
		with (
			patch.object(demo, "_", lambda text: text),
			patch.object(demo, "get_company_info", return_value={}),
			patch.object(demo, "get_public_info", return_value={}),
			patch.object(demo, "ZatcaXml", side_effect=BLANK_VAT_NUMBER),
			patch.object(demo, "make_invoice_request") as send,
			patch.object(demo.frappe, "session", MagicMock(user="Administrator")),
			patch.object(demo.frappe, "publish_realtime") as publish,
			patch.object(demo.frappe, "log_error") as log_error,
		):
			demo.send_sample_sales_invoices(settings, {})

		send.assert_not_called()
		self.assertEqual(log_error.call_count, 5, "every unchecked invoice leaves an Error Log")
		events = [call.args[1] for call in publish.call_args_list]
		self.assertEqual(len(events), 5)
		for event in events:
			self.assertNotIn("Rejected", event["message"])
			self.assertIn(str(BLANK_VAT_NUMBER), event["message"])
			self.assertEqual(event["commercial_register_name"], "1010101010", "the wizard drops an event with no register")
			self.assertEqual(event["percentage"], 20, "the wizard reads a red event under 20 as a failed certificate")
