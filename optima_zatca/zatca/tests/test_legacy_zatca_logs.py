"""What each row of the optima app's old Zatca Logs becomes when it is moved into Optima Zatca Logs."""

import json
import unittest
from datetime import datetime

import frappe

from optima_zatca.patches.v16 import move_legacy_zatca_logs as legacy

CREATED = datetime(2024, 11, 3, 9, 15, 2, 123456)


def legacy_row(**values):
    row = frappe._dict(
        name="a1b2c3d4e5",
        owner="cashier@example.com",
        creation=CREATED,
        status="Success",
        method="generate_zatca_invoice_request",
        message=json.dumps({"clearanceStatus": "CLEARED"}),
        reference_doctype="Sales Invoice",
        reference_name="ACC-SINV-2024-00042",
        company="Legacy Co",
        uuid="6f1c7c7e-0000-4000-8000-000000000042",
        icv="42",
        hash="aGFzaA==",
    )
    row.update(values)
    return row


class TestLegacyZatcaLog(unittest.TestCase):
    def test_a_legacy_row_stays_out_of_every_icv_pih_chain(self):
        log = legacy._optima_log(legacy_row())

        self.assertIsNone(log.get("commercial_register"), "a legacy row with a register can head a live ICV/PIH chain")
        self.assertIsNone(log.get("environment"), "a legacy row with an environment can head a live ICV/PIH chain")

    def test_a_row_keeps_its_name_owner_and_creation(self):
        log = legacy._optima_log(legacy_row())

        self.assertEqual(log["doctype"], "Optima Zatca Logs")
        self.assertEqual(
            (log["name"], log["owner"], log["creation"]),
            ("a1b2c3d4e5", "cashier@example.com", CREATED),
            "the audit trail loses who sent the invoice and when",
        )
        self.assertEqual(log["reference_name"], "ACC-SINV-2024-00042", "the already-sent check stops seeing the invoice")

    def test_only_rows_handle_optima_zatca_did_not_copy_are_copied(self):
        copied = legacy_row(name="copied", uuid="uuid-1", hash="hash-1")
        same_uuid_other_hash = legacy_row(name="retried", uuid="uuid-1", hash="hash-2")
        no_uuid = legacy_row(name="early", uuid=None, hash=None)

        logs = legacy._logs_to_copy([copied, same_uuid_other_hash, no_uuid], {("uuid-1", "hash-1"), (None, None)})

        self.assertEqual(
            [log["name"] for log in logs],
            ["retried", "early"],
            "a copied row is copied twice, or a row the early logger wrote without a uuid is lost",
        )

    def test_endpoint_comes_from_the_method_or_zatca_answer(self):
        both_statuses = json.dumps({"clearanceStatus": None, "reportingStatus": None})
        cases = [
            ("send_sample_sales_invoices (Test Invoice)", both_statuses, "complainace_checks", "a sample invoice counts as a real one"),
            ("generate_zatca_invoice_request", json.dumps({"clearanceStatus": "NOT_CLEARED"}), "clearance", "a refused clearance is lost"),
            ("generate_zatca_invoice_request", json.dumps({"reportingStatus": "REPORTED"}), "reporting", "a reported invoice is lost"),
            ("generate_zatca_invoice_request", "<html>Bad Gateway</html>", None, "a non-JSON answer crashes the patch"),
            ("generate_zatca_invoice_request", json.dumps(["not", "an", "object"]), None, "a JSON list crashes the patch"),
            (None, None, None, "a row with no method or message crashes the patch"),
        ]
        for method, message, expected, bug in cases:
            with self.subTest(method=method, message=message):
                self.assertEqual(legacy._api_endpoint(method, message), expected, bug)
