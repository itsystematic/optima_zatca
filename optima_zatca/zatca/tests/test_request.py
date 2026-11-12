"""The transport refuses every ZATCA request while tests run, so no test can send one.

Each sender runs with its requests function patched, so even a broken guard sends nothing.
"""

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from optima_zatca.zatca import request


class TestRequestsBlockedInTests(UnitTestCase):
    def test_no_sender_reaches_zatca(self):
        senders = {
            "post": request.make_post_request,
            "get": request.make_get_request,
            "patch": request.make_patch_request,
        }
        for method, send in senders.items():
            with self.subTest(method=method), patch.object(request.requests, method) as http:
                with self.assertRaises(frappe.ValidationError):
                    send("Any Setting", "reporting", {}, {})
                http.assert_not_called()


class TestBaseUrl(UnitTestCase):
    def test_environment_comes_from_a_setting_name_or_a_loaded_setting(self):
        loaded = frappe.get_doc({"doctype": "Optima Zatca Setting", "api_endpoints": "simulation"})
        with patch.object(request.frappe.db, "get_value", return_value="sandbox") as get_value:
            self.assertEqual(request.get_base_url("Any Setting", "reporting"), request.BASEURL["sandbox"]["reporting"])
            # The sample-invoice and Send to ZATCA paths pass the document itself.
            self.assertEqual(request.get_base_url(loaded, "reporting"), request.BASEURL["simulation"]["reporting"])
            get_value.assert_called_once()
