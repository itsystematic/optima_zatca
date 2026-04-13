# optima_zatca/optima_zatca/print_format/sales_invoice_controller.py

import frappe
from frappe import _


PAID_STATUSES = {"Paid", "Partly Paid"}
STANDARD_TAX_ID_LENGTH = 15
DEFAULT_VAT_RATE = 15
INVOICE_TYPES = {
    (True, False): {"en": _("Tax Invoice"), "ar": "فاتورة ضريبية"},
    (True, True): {"en": _("Credit Note"), "ar": "اشعار دائن مرتجع"},
    (False, False): {"en": _("Simplified Tax Invoice"), "ar": "فاتورة ضريبية مبسطة"},
    (False, True): {"en": _("Simplified Credit Note"), "ar": "فاتورة مرتجع مبسطة"},
}
BANK_FIELD_MAPPING = {
    "bank_name": "bank_name",
    "branch_no": "bank_branch_no",
    "branch_name": "bank_branch_name",
    "id_number": "bank_id_number",
    "account_number": "bank_account_number",
    "iban": "bank_iban",
}


class SalesInvoicePrintRepository:
    """Wraps Frappe access so print-format logic stays easy to test."""

    def get_customer_data(self, customer_name):
        return frappe.db.get_value(
            "Customer",
            customer_name,
            ["tax_id", "registration_value", "customer_name"],
            as_dict=True,
        ) or frappe._dict()

    def get_company(self, company_name):
        return frappe.get_cached_doc("Company", company_name)

    def get_address(self, address_name):
        if not address_name:
            return frappe._dict()

        try:
            return frappe.get_cached_doc("Address", address_name)
        except frappe.DoesNotExistError:
            return frappe._dict()

    def get_payment_entry_references(self, reference_doctype, reference_name):
        return frappe.get_all(
            "Payment Entry Reference",
            filters={
                "reference_doctype": reference_doctype,
                "reference_name": reference_name,
                "docstatus": 1,
            },
            fields=["parent", "allocated_amount"],
        )

    def get_payment_entries(self, parent_names):
        if not parent_names:
            return []

        return frappe.get_all(
            "Payment Entry",
            filters={"name": ["in", parent_names]},
            fields=[
                "name",
                "posting_date",
                "mode_of_payment",
                "paid_from_account_currency",
                "paid_to_account_currency",
                "payment_type",
            ],
        )

    def get_journal_entry_references(self, reference_doctype, reference_name):
        return frappe.get_all(
            "Journal Entry Account",
            filters={
                "reference_type": reference_doctype,
                "reference_name": reference_name,
                "docstatus": 1,
            },
            fields=[
                "parent",
                "credit_in_account_currency",
                "debit_in_account_currency",
                "account_currency",
            ],
        )

    def get_journal_entries(self, parent_names):
        if not parent_names:
            return []

        return frappe.get_all(
            "Journal Entry",
            filters={"name": ["in", parent_names]},
            fields=["name", "posting_date", "mode_of_payment"],
        )

    def get_bank_details(self, company):
        return frappe._dict(
            {
                field_name: self._read_value(company, source_field)
                for field_name, source_field in BANK_FIELD_MAPPING.items()
            }
        )

    @staticmethod
    def _read_value(source, fieldname):
        if hasattr(source, "get"):
            return source.get(fieldname, "")

        return getattr(source, fieldname, "")


class PaymentDetailsCollector:
    """Collects payment-related rows for the print context."""

    def __init__(self, repository=None):
        self.repository = repository or SalesInvoicePrintRepository()

    def collect(self, reference_doctype, reference_name):
        payments = []
        payments.extend(
            self._build_payment_entry_rows(
                self.repository.get_payment_entry_references(
                    reference_doctype, reference_name
                )
            )
        )
        payments.extend(
            self._build_journal_entry_rows(
                self.repository.get_journal_entry_references(
                    reference_doctype, reference_name
                )
            )
        )
        return payments

    def _build_payment_entry_rows(self, payment_refs):
        if not payment_refs:
            return []

        payment_entries = self.repository.get_payment_entries(
            [reference.parent for reference in payment_refs]
        )
        payment_entries_by_name = {
            payment_entry.name: payment_entry for payment_entry in payment_entries
        }

        return [
            frappe._dict(
                {
                    "name": reference.parent,
                    "posting_date": payment_entry.get("posting_date"),
                    "mode_of_payment": payment_entry.get("mode_of_payment", ""),
                    "allocated_amount": reference.allocated_amount,
                    "currency": self._get_payment_entry_currency(payment_entry),
                    "entry_type": "Payment Entry",
                }
            )
            for reference in payment_refs
            for payment_entry in [payment_entries_by_name.get(reference.parent, frappe._dict())]
        ]

    def _build_journal_entry_rows(self, journal_refs):
        if not journal_refs:
            return []

        journal_entries = self.repository.get_journal_entries(
            [reference.parent for reference in journal_refs]
        )
        journal_entries_by_name = {
            journal_entry.name: journal_entry for journal_entry in journal_entries
        }

        return [
            frappe._dict(
                {
                    "name": reference.parent,
                    "posting_date": journal_entry.get("posting_date"),
                    "mode_of_payment": journal_entry.get("mode_of_payment", ""),
                    "allocated_amount": reference.credit_in_account_currency
                    or reference.debit_in_account_currency,
                    "currency": reference.account_currency,
                    "entry_type": "Journal Entry",
                }
            )
            for reference in journal_refs
            for journal_entry in [journal_entries_by_name.get(reference.parent, frappe._dict())]
        ]

    @staticmethod
    def _get_payment_entry_currency(payment_entry):
        if payment_entry.get("payment_type") == "Receive":
            return payment_entry.get("paid_from_account_currency")

        return payment_entry.get("paid_to_account_currency")


class SalesInvoicePrintContextBuilder:
    """Builds the print-format context with injectable collaborators."""

    def __init__(self, repository=None, payment_collector=None):
        self.repository = repository or SalesInvoicePrintRepository()
        self.payment_collector = payment_collector or PaymentDetailsCollector(
            self.repository
        )

    def build(self, doc):
        customer_data = self.repository.get_customer_data(doc.customer)
        company = self.repository.get_company(doc.company)
        retention_details = self._build_retention_details(doc)

        return frappe._dict(
            {
                "customer_tax_id": customer_data.get("tax_id", ""),
                "customer_cr_number": customer_data.get("registration_value", ""),
                "invoice_type": get_invoice_type(
                    customer_data.get("tax_id"), doc.is_return
                ),
                "company": company,
                "seller_address": self.repository.get_address(doc.company_address),
                "customer_address": self.repository.get_address(doc.customer_address),
                "payments": self._get_payments(doc),
                "bank_details": self.repository.get_bank_details(company),
                "vat_rate": get_vat_rate(doc),
                **retention_details,
            }
        )

    def _get_payments(self, doc):
        if doc.status not in PAID_STATUSES:
            return []

        return self.payment_collector.collect(doc.doctype, doc.name)

    @staticmethod
    def _build_retention_details(doc):
        retention_percentage = getattr(doc, "retention_percentage", 0) or 0
        retention_amount = (doc.retention_amount or 0) if retention_percentage > 0 else 0

        return frappe._dict(
            {
                "retention_percentage": retention_percentage,
                "retention_amount": retention_amount,
                "amount_after_retention": doc.grand_total - retention_amount,
            }
        )


@frappe.whitelist()
def get_context(doc):
    """
    Prepares all data needed for the Sales Invoice print format.
    This moves database queries out of the Jinja template for better performance.
    """
    return SalesInvoicePrintContextBuilder().build(doc)


def get_invoice_type(customer_tax_id, is_return):
    """
    Determines the invoice type based on customer tax ID and return status.
    Returns a dict with English and Arabic titles.
    """
    is_standard = bool(customer_tax_id) and (
        len(str(customer_tax_id)) == STANDARD_TAX_ID_LENGTH
    )
    return frappe._dict(INVOICE_TYPES[(is_standard, bool(is_return))])


def get_address_details(address_name):
    """
    Fetches address details if address exists.
    Returns empty dict if no address.
    """
    return SalesInvoicePrintRepository().get_address(address_name)


def get_payment_details(reference_doctype, reference_name):
    """
    Collects all payment information for the invoice.
    Combines Payment Entry and Journal Entry references.
    """
    return PaymentDetailsCollector().collect(reference_doctype, reference_name)


def get_bank_details(company_name):
    """
    Fetches bank details from company settings or custom doctype.
    """
    repository = SalesInvoicePrintRepository()
    return repository.get_bank_details(repository.get_company(company_name))


def get_vat_rate(doc):
    """
    Gets the VAT rate from the document's tax template.
    """
    for tax in getattr(doc, "taxes", []) or []:
        if "VAT" in (tax.description or "").upper():
            return tax.rate or DEFAULT_VAT_RATE
    return DEFAULT_VAT_RATE
