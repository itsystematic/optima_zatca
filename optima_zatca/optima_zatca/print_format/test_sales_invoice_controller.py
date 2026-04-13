import importlib
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock


class FrappeDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as error:
            raise AttributeError(key) from error

    def __setattr__(self, key, value):
        self[key] = value


def _make_dict(*args, **kwargs):
    return FrappeDict(*args, **kwargs)


def _load_module():
    frappe_module = types.ModuleType("frappe")

    def _whitelist(*args, **kwargs):
        def _decorator(function):
            return function

        return _decorator

    frappe_module.whitelist = _whitelist
    frappe_module._ = lambda message: message
    frappe_module._dict = _make_dict
    frappe_module.get_all = MagicMock()
    frappe_module.get_cached_doc = MagicMock()
    frappe_module.db = SimpleNamespace(get_value=MagicMock())
    frappe_module.DoesNotExistError = type("DoesNotExistError", (Exception,), {})

    sys.modules.pop(
        "optima_zatca.optima_zatca.print_format.sales_invoice_controller", None
    )
    sys.modules["frappe"] = frappe_module
    return importlib.import_module(
        "optima_zatca.optima_zatca.print_format.sales_invoice_controller"
    )


class TestSalesInvoicePrintContextBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()

    def test_builds_context_with_injected_collaborators(self):
        repository = MagicMock()
        repository.get_customer_data.return_value = FrappeDict(
            tax_id="123456789012345", registration_value="CR-001"
        )
        repository.get_company.return_value = FrappeDict(company_name="Optima")
        repository.get_address.side_effect = [
            FrappeDict(city="Riyadh"),
            FrappeDict(city="Jeddah"),
        ]
        repository.get_bank_details.return_value = FrappeDict(bank_name="Main Bank")

        payment_collector = MagicMock()
        payment_collector.collect.return_value = [FrappeDict(name="PE-0001")]

        builder = self.module.SalesInvoicePrintContextBuilder(
            repository=repository,
            payment_collector=payment_collector,
        )
        doc = SimpleNamespace(
            customer="CUST-001",
            is_return=0,
            company="Optima",
            company_address="ADDR-COMPANY",
            customer_address="ADDR-CUSTOMER",
            status="Paid",
            doctype="Sales Invoice",
            name="SINV-0001",
            taxes=[SimpleNamespace(description="VAT 15%", rate=15)],
            retention_percentage=10,
            retention_amount=50,
            grand_total=500,
            outstanding_amount=500,
        )

        context = builder.build(doc)

        self.assertEqual(context.customer_tax_id, "123456789012345")
        self.assertEqual(context.customer_cr_number, "CR-001")
        self.assertEqual(context.invoice_type.en, "Tax Invoice")
        self.assertEqual(context.company.company_name, "Optima")
        self.assertEqual(context.seller_address.city, "Riyadh")
        self.assertEqual(context.customer_address.city, "Jeddah")
        self.assertEqual(context.payments[0].name, "PE-0001")
        self.assertEqual(context.bank_details.bank_name, "Main Bank")
        self.assertEqual(context.vat_rate, 15)
        self.assertEqual(context.retention_amount, 50)
        self.assertEqual(context.amount_after_retention, 450)
        self.assertEqual(context.display_amounts.paid_amount, 0)
        self.assertEqual(context.display_amounts.outstanding_amount, 500)
        self.assertEqual(context.display_amounts.base_paid_amount, 0)
        self.assertEqual(context.display_amounts.base_outstanding_amount, 500)
        payment_collector.collect.assert_called_once_with("Sales Invoice", "SINV-0001")

    def test_skips_payment_lookup_for_unpaid_documents(self):
        repository = MagicMock()
        repository.get_customer_data.return_value = FrappeDict()
        repository.get_company.return_value = FrappeDict(company_name="Optima")
        repository.get_address.side_effect = [FrappeDict(), FrappeDict()]
        repository.get_bank_details.return_value = FrappeDict()

        payment_collector = MagicMock()
        builder = self.module.SalesInvoicePrintContextBuilder(
            repository=repository,
            payment_collector=payment_collector,
        )
        doc = SimpleNamespace(
            customer="CUST-001",
            is_return=1,
            company="Optima",
            company_address=None,
            customer_address=None,
            status="Unpaid",
            doctype="Sales Invoice",
            name="SINV-0002",
            taxes=[],
            retention_percentage=0,
            retention_amount=0,
            grand_total=350,
            outstanding_amount=350,
        )

        context = builder.build(doc)

        self.assertEqual(context.payments, [])
        self.assertEqual(context.invoice_type.en, "Simplified Credit Note")
        self.assertEqual(context.amount_after_retention, 350)
        self.assertEqual(context.display_amounts.outstanding_amount, 350)
        payment_collector.collect.assert_not_called()

    def test_converts_outstanding_amount_from_party_account_currency(self):
        repository = MagicMock()
        repository.get_customer_data.return_value = FrappeDict()
        repository.get_company.return_value = FrappeDict(
            company_name="Optima",
            default_currency="SAR",
        )
        repository.get_address.side_effect = [FrappeDict(), FrappeDict()]
        repository.get_bank_details.return_value = FrappeDict()

        builder = self.module.SalesInvoicePrintContextBuilder(repository=repository)
        doc = SimpleNamespace(
            customer="CUST-001",
            is_return=0,
            company="Optima",
            company_address=None,
            customer_address=None,
            status="Unpaid",
            doctype="Sales Invoice",
            name="SINV-0003",
            currency="USD",
            party_account_currency="SAR",
            conversion_rate=3.75,
            taxes=[],
            retention_percentage=0,
            retention_amount=0,
            grand_total=2109.10,
            base_grand_total=7909.12,
            outstanding_amount=7909.12,
        )

        context = builder.build(doc)

        self.assertAlmostEqual(context.display_amounts.paid_amount, 0, places=2)
        self.assertAlmostEqual(context.display_amounts.outstanding_amount, 2109.10, places=2)
        self.assertAlmostEqual(context.display_amounts.base_paid_amount, 0, places=2)
        self.assertAlmostEqual(
            context.display_amounts.base_outstanding_amount, 7909.12, places=2
        )


class TestPaymentDetailsCollector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()

    def test_collects_payment_and_journal_entries(self):
        repository = MagicMock()
        repository.get_payment_entry_references.return_value = [
            FrappeDict(parent="PE-0001", allocated_amount=100),
            FrappeDict(parent="PE-0002", allocated_amount=50),
        ]
        repository.get_payment_entries.return_value = [
            FrappeDict(
                name="PE-0001",
                posting_date="2026-01-01",
                mode_of_payment="Cash",
                paid_from_account_currency="SAR",
                paid_to_account_currency="USD",
                payment_type="Receive",
            ),
            FrappeDict(
                name="PE-0002",
                posting_date="2026-01-02",
                mode_of_payment="Bank Transfer",
                paid_from_account_currency="EUR",
                paid_to_account_currency="USD",
                payment_type="Pay",
            ),
        ]
        repository.get_journal_entry_references.return_value = [
            FrappeDict(
                parent="JE-0001",
                credit_in_account_currency=0,
                debit_in_account_currency=75,
                account_currency="SAR",
            )
        ]
        repository.get_journal_entries.return_value = [
            FrappeDict(
                name="JE-0001",
                posting_date="2026-01-03",
                mode_of_payment="Adjustment",
            )
        ]

        payments = self.module.PaymentDetailsCollector(repository).collect(
            "Sales Invoice", "SINV-0001"
        )

        self.assertEqual(len(payments), 3)
        self.assertEqual(payments[0].currency, "SAR")
        self.assertEqual(payments[1].currency, "USD")
        self.assertEqual(payments[2].allocated_amount, 75)
        self.assertEqual(payments[2].entry_type, "Journal Entry")


class TestSalesInvoiceControllerHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()

    def setUp(self):
        self.module.frappe.get_cached_doc.reset_mock()
        self.module.frappe.get_cached_doc.side_effect = None

    def test_get_address_details_returns_empty_dict_when_address_is_missing(self):
        self.assertEqual(self.module.get_address_details(None), {})

    def test_get_address_details_returns_empty_dict_when_address_does_not_exist(self):
        self.module.frappe.get_cached_doc.side_effect = self.module.frappe.DoesNotExistError

        result = self.module.get_address_details("ADDR-404")

        self.assertEqual(result, {})

    def test_get_bank_details_maps_company_fields_to_template_keys(self):
        self.module.frappe.get_cached_doc.return_value = FrappeDict(
            bank_name="Main Bank",
            bank_branch_no="001",
            bank_branch_name="Riyadh Branch",
            bank_id_number="ID-10",
            bank_account_number="ACC-20",
            bank_iban="SA0000000000000000000000",
        )

        result = self.module.get_bank_details("Optima")

        self.assertEqual(
            result,
            {
                "bank_name": "Main Bank",
                "branch_no": "001",
                "branch_name": "Riyadh Branch",
                "id_number": "ID-10",
                "account_number": "ACC-20",
                "iban": "SA0000000000000000000000",
            },
        )

    def test_get_bank_details_returns_empty_values_when_fields_are_missing(self):
        self.module.frappe.get_cached_doc.return_value = FrappeDict(company_name="Optima")

        result = self.module.get_bank_details("Optima")

        self.assertEqual(
            result,
            {
                "bank_name": "",
                "branch_no": "",
                "branch_name": "",
                "id_number": "",
                "account_number": "",
                "iban": "",
            },
        )

    def test_get_vat_rate_falls_back_to_default(self):
        doc = SimpleNamespace(taxes=[SimpleNamespace(description="Service Tax", rate=5)])

        self.assertEqual(self.module.get_vat_rate(doc), 15)
