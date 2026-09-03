"""Integration smoke tests for the Sales Invoice lifecycle doc_events.

These save/submit/cancel/delete real invoices so the ``on_submit`` /
``before_cancel`` / ``on_trash`` hooks fire end-to-end, proving the wiring the
in-memory matrix layer can't (that the hooks are registered and read the ZATCA
settings/state at the right moment). They assert only *that* the guard fires or
the QR is attached — branch/message coverage is the matrix layer's job.

No ZATCA HTTP transport is involved: ``on_submit`` only builds the Phase-1 QR
and guards Phase-2; the clearance/reporting call is a separate ("Send to ZATCA")
flow. ``tearDown`` rolls the transaction back and clears the cache (the settings
setters and the Company region read go through caches).
"""

import erpnext
import frappe
from frappe.tests.utils import FrappeTestCase

from optima_zatca.events.tests import helpers


class TestSalesInvoiceLifecycleWiring(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()
        frappe.clear_cache()

    def test_on_submit_blocks_unreported_phase_two_invoice(self):
        # Phase Two + never sent to ZATCA -> the on_submit guard must block submit.
        helpers.set_zatca_main_settings(phase="Phase Two")
        si = helpers.make_sales_invoice(sales_invoice_type="Normal")
        with self.assertRaises(frappe.ValidationError):
            si.submit()

    def test_before_cancel_blocks_finalized_invoice(self):
        # A sent+CLEARED invoice submits (on_submit skips QR because sent_to_zatca=1),
        # then cancel is blocked while the override is off.
        helpers.set_zatca_main_settings(phase="Phase Two", enable_cancel_invoice=0)
        si = helpers.make_sales_invoice(
            sales_invoice_type="Normal",
            sent_to_zatca=1,
            clearance_or_reporting="CLEARED",
            submit=True,
        )
        self.assertEqual(si.docstatus, 1)
        with self.assertRaises(frappe.ValidationError):
            si.cancel()

    def test_on_trash_blocks_finalized_invoice(self):
        # A draft carrying finalized ZATCA state must not be deletable while the
        # override is off; deleting fires on_trash.
        helpers.set_zatca_main_settings(enable_delete_invoice=0)
        si = helpers.make_sales_invoice(
            sales_invoice_type="Normal",
            sent_to_zatca=1,
            clearance_or_reporting="REPORTED",
        )
        with self.assertRaises(frappe.ValidationError):
            si.delete()

    def test_phase_one_submit_generates_qr_on_ksa_site(self):
        company = helpers.get_company()
        helpers.set_zatca_main_settings(phase="Phase One")
        helpers.set_company_zatca_fields(
            company,
            company_name_in_arabic="شركة الاختبار",
            tax_id="300000000000003",
        )
        frappe.clear_cache()

        si = helpers.make_sales_invoice(sales_invoice_type="Normal", submit=True)

        self.assertEqual(si.docstatus, 1)
        if erpnext.get_region(company) == "Saudi Arabia":
            # Full Phase-1 path: a QR image File is attached and its URL stored.
            self.assertTrue(si.ksa_einv_qr)
            self.assertTrue(frappe.db.exists("File", {"file_url": si.ksa_einv_qr}))
        else:
            # Non-KSA company (e.g. the CI test company): on_submit short-circuits
            # on region, so no QR is generated but the submit still succeeds.
            self.assertFalse(si.ksa_einv_qr)
