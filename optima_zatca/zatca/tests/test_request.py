"""The transport refuses every ZATCA request while tests run, so no test can send one.

Each sender runs with its requests function patched, so even a broken guard sends nothing.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from optima_zatca.zatca import request


class TestRequestsBlockedInTests(FrappeTestCase):
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
