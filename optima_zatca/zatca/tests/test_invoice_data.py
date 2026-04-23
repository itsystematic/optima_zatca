import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class FakeDoc(dict):
    def __getattr__(self, item):
        return self.get(item)


def _fake_flt(value, precision=None):
    number = float(value or 0)
    if precision is None:
        return number
    return round(number, precision)


def _load_invoice_module():
    frappe_module = types.ModuleType("frappe")
    frappe_module._ = lambda value: value
    frappe_module._dict = lambda value=None: FakeDoc(value or {})
    frappe_module.throw = MagicMock(side_effect=RuntimeError("frappe.throw called"))
    frappe_module.get_doc = MagicMock()
    frappe_module.log_error = MagicMock()
    frappe_module.db = MagicMock()
    frappe_module.local = types.SimpleNamespace(site="test.local")
    frappe_module.DoesNotExistError = type("DoesNotExistError", (Exception,), {})

    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.flt = _fake_flt
    frappe_utils.get_bench_relative_path = MagicMock(return_value="/tmp")

    frappe_document = types.ModuleType("frappe.model.document")
    frappe_document.Document = object

    validate_module = types.ModuleType("optima_zatca.zatca.classes.validate")
    validate_module.ZatcaInvoiceValidate = MagicMock()

    class FakeZatcaXml:
        def __init__(self, payload):
            self.payload = payload
            self.hash = "hash-123"
            self.qr_code = "qr-123"
            self.root = "fake-root"

    xml_module = types.ModuleType("optima_zatca.zatca.classes.xml")
    xml_module.ZatcaXml = FakeZatcaXml

    app_utils_module = types.ModuleType("optima_zatca.zatca.utils")
    app_utils_module.log_and_throw_error = MagicMock()

    xml_transport_module = types.ModuleType("optima_zatca.zatca.xml_transport")
    xml_transport_module.encode_invoice_xml_for_api = MagicMock(return_value="encoded-xml")
    xml_transport_module.serialize_invoice_xml = MagicMock(return_value=b"<xml/>")

    patched_modules = {
        "frappe": frappe_module,
        "frappe.utils": frappe_utils,
        "frappe.model.document": frappe_document,
        "optima_zatca.zatca.classes.validate": validate_module,
        "optima_zatca.zatca.classes.xml": xml_module,
        "optima_zatca.zatca.utils": app_utils_module,
        "optima_zatca.zatca.xml_transport": xml_transport_module,
    }

    sys.modules.pop("optima_zatca.zatca.classes.invoice", None)
    sys.modules.pop("optima_zatca.zatca.classes.invoice_context", None)
    sys.modules.pop("optima_zatca.zatca.classes.invoice_payload_builder", None)
    with patch.dict(sys.modules, patched_modules):
        return importlib.import_module("optima_zatca.zatca.classes.invoice")


class InvoiceDataTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def setUp(self):
        self.invoice_module.frappe.get_doc.reset_mock()
        self.invoice_module.frappe.throw.reset_mock()
        self.invoice_module.frappe.log_error.reset_mock()
        self.invoice_module.frappe.db.reset_mock()
        self.invoice_module.ZatcaInvoiceValidate.reset_mock()
        self.invoice_module.encode_invoice_xml_for_api.reset_mock()
        self.invoice_module.encode_invoice_xml_for_api.return_value = "encoded-xml"
        self.invoice_module.serialize_invoice_xml.reset_mock()
        self.invoice_module.serialize_invoice_xml.return_value = b"<xml/>"


class TestInvoiceContextLoader(InvoiceDataTestCase):
    def test_load_returns_loaded_invoice_context(self):
        sales_invoice = FakeDoc(
            name="SINV-0001",
            commercial_register="CR-1",
            company_address="ADDR-COMPANY",
            customer="Customer A",
            customer_address="ADDR-CUSTOMER",
        )
        company_settings = FakeDoc({"authorization": "Bearer token", "commercial_register": "CR-1"})
        company_address = FakeDoc({"city": "Riyadh"})
        customer_info = FakeDoc({"customer_type": "Company"})
        customer_address = FakeDoc({"country": "Saudi Arabia"})

        def fake_get_doc(doctype, name_or_filters):
            if doctype == "Optima Zatca Setting":
                return company_settings
            if doctype == "Address" and name_or_filters == "ADDR-COMPANY":
                return company_address
            if doctype == "Address" and name_or_filters == "ADDR-CUSTOMER":
                return customer_address
            if doctype == "Customer":
                return customer_info
            raise AssertionError(f"Unexpected get_doc call: {(doctype, name_or_filters)}")

        self.invoice_module.frappe.get_doc.side_effect = fake_get_doc
        self.invoice_module.frappe.db.get_value.return_value = "sa"

        context = self.invoice_module.InvoiceContextLoader(sales_invoice).load()

        self.assertEqual(context.company_settings, company_settings)
        self.assertEqual(context.company_address, company_address)
        self.assertEqual(context.customer_info, customer_info)
        self.assertEqual(context.customer_address, customer_address)
        self.assertEqual(context.customer_country_code, "SA")

    def test_load_defaults_country_code_when_customer_address_missing(self):
        sales_invoice = FakeDoc(
            name="SINV-0002",
            commercial_register="CR-1",
            company_address="ADDR-COMPANY",
            customer="Customer A",
            customer_address=None,
        )
        company_settings = FakeDoc({"authorization": "Bearer token"})
        company_address = FakeDoc({"city": "Riyadh"})
        customer_info = FakeDoc({"customer_type": "Individual"})

        def fake_get_doc(doctype, name_or_filters):
            if doctype == "Optima Zatca Setting":
                return company_settings
            if doctype == "Address" and name_or_filters == "ADDR-COMPANY":
                return company_address
            if doctype == "Customer":
                return customer_info
            raise AssertionError(f"Unexpected get_doc call: {(doctype, name_or_filters)}")

        self.invoice_module.frappe.get_doc.side_effect = fake_get_doc

        context = self.invoice_module.InvoiceContextLoader(sales_invoice).load()

        self.assertEqual(context.customer_country_code, "SA")
        self.invoice_module.frappe.db.get_value.assert_not_called()


class TestZatcaInvoicePayloadBuilder(InvoiceDataTestCase):
    def test_determine_invoice_type_uses_loaded_context(self):
        sales_invoice = FakeDoc(
            sales_invoice_type="Normal",
            is_return=0,
            is_debit_note=0,
        )
        context = self.invoice_module.LoadedInvoiceContext(
            company_settings=FakeDoc({"check_pcsid": 1, "check_csid": 1, "check_csr": 1}),
            company_address={},
            customer_info=FakeDoc({"customer_type": "Company"}),
            customer_address={},
            customer_country_code="SA",
        )

        builder = self.invoice_module.ZatcaInvoicePayloadBuilder(sales_invoice, context)

        result = builder._determine_invoice_type()

        self.assertEqual(result["InvoiceStatus"], "Standard")
        self.assertEqual(result["InvoiceTypeCode"], "388")
        self.assertEqual(result["Clearance-Status"], "1")
        self.assertEqual(result["EndPoint"], "clearance")


class TestZatcaInvoiceDataFacade(InvoiceDataTestCase):
    def test_facade_preserves_workflow_contract_over_new_internal_seams(self):
        sales_invoice = FakeDoc(name="SINV-0003")
        context = self.invoice_module.LoadedInvoiceContext(
            company_settings=FakeDoc({"authorization": "Bearer token"}),
            company_address={},
            customer_info={},
            customer_address={},
            customer_country_code="SA",
        )
        payload = FakeDoc(
            {
                "Clearance-Status": "1",
                "UUID": "uuid-123",
                "EndPoint": "clearance",
                "Environment": "Simulation",
                "PIH": "pih-123",
                "InvoiceCounter": "7",
            }
        )

        with (
            patch.object(self.invoice_module.InvoiceContextLoader, "load", return_value=context),
            patch.object(self.invoice_module.ZatcaInvoicePayloadBuilder, "build", return_value=payload),
        ):
            invoice_data = self.invoice_module.ZatcaInvoiceData(sales_invoice)

        self.assertEqual(invoice_data.company_settings, context.company_settings)
        self.assertEqual(invoice_data.customer_country_code, "SA")
        self.assertEqual(
            invoice_data.get_submission_request_data(),
            {
                "clearance_status": "1",
                "authorization": "Bearer token",
                "invoice_hash": "hash-123",
                "uuid": "uuid-123",
                "encoded_invoice": "encoded-xml",
                "company_settings": context.company_settings,
                "endpoint": "clearance",
            },
        )
        self.assertEqual(invoice_data.get_generated_qr_code(), "qr-123")
        self.assertEqual(
            invoice_data.get_log_context(),
            {
                "uuid": "uuid-123",
                "invoice_hash": "hash-123",
                "generated_qr_code": "qr-123",
                "api_endpoint": "clearance",
                "environment": "Simulation",
                "pih": "pih-123",
                "invoice_counter": "7",
                "xml_content": b"<xml/>",
            },
        )
        self.assertEqual(invoice_data.get_uuid(), "uuid-123")
