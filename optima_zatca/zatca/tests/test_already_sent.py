"""Send to ZATCA refuses an invoice that a ZATCA log already records as accepted."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from optima_zatca.zatca.classes.validate import ZatcaInvoiceValidate


def _unsent_invoice_validator():
    """A validator for an invoice whose sent flag is clear, built without running every check."""
    with patch.object(ZatcaInvoiceValidate, "validate"):
        return ZatcaInvoiceValidate({}, {"name": "SINV-1", "sent_to_zatca": 0}, {}, {}, {})


def _logs_with_status(status):
    """Stands in for the log query: finds the invoice's one log only if the filter asks for its status."""

    def get_all(doctype, filters):
        return [{"name": "LOG-1"}] if status in filters["status"][1] else []

    return get_all


def _check_with_log(status):
    with patch(
        "optima_zatca.zatca.classes.validate.frappe.db.get_all", side_effect=_logs_with_status(status)
    ):
        _unsent_invoice_validator().validate_sales_invoice_sender()


class TestAlreadySent(FrappeTestCase):
    def test_accepted_log_blocks_a_resend(self):
        # A missing comma once joined the two statuses into "SuccessWarning", which no log has.
        for status in ("Success", "Warning"):
            with self.subTest(status=status), self.assertRaises(frappe.ValidationError):
                _check_with_log(status)

    def test_failed_log_allows_a_retry(self):
        _check_with_log("Failed")
