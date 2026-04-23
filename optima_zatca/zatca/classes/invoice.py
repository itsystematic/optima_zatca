import json

import frappe
from frappe.utils import get_bench_relative_path
from typing import Any, Dict

from optima_zatca.zatca.classes.validate import ZatcaInvoiceValidate
from optima_zatca.zatca.classes.invoice_context import InvoiceContextLoader, LoadedInvoiceContext
from optima_zatca.zatca.classes.invoice_payload_builder import ZatcaInvoicePayloadBuilder
from optima_zatca.zatca.classes.xml import ZatcaXml
from optima_zatca.zatca.utils import log_and_throw_error
from optima_zatca.zatca.xml_transport import encode_invoice_xml_for_api, serialize_invoice_xml
from frappe.model.document import Document


class ZatcaInvoiceData:
    """
    Facade for ZATCA invoice processing used by the submission workflow.
    """

    DEFAULT_COUNTRY_CODE = InvoiceContextLoader.DEFAULT_COUNTRY_CODE
    DEFAULT_TAX_SCHEME = ZatcaInvoicePayloadBuilder.DEFAULT_TAX_SCHEME
    DEFAULT_CURRENCY = ZatcaInvoicePayloadBuilder.DEFAULT_CURRENCY
    PROFILE_ID = ZatcaInvoicePayloadBuilder.PROFILE_ID

    COMPANY_CUSTOMER_TYPE = ZatcaInvoicePayloadBuilder.COMPANY_CUSTOMER_TYPE
    INDIVIDUAL_CUSTOMER_TYPE = ZatcaInvoicePayloadBuilder.INDIVIDUAL_CUSTOMER_TYPE

    ADJUSTMENT_TYPES = ZatcaInvoicePayloadBuilder.ADJUSTMENT_TYPES
    PREPAYMENT_TYPES = ZatcaInvoicePayloadBuilder.PREPAYMENT_TYPES
    INVOICE_TYPE_CODES = ZatcaInvoicePayloadBuilder.INVOICE_TYPE_CODES

    def __init__(self, sales_invoice: Document):
        """Initialize ZATCA invoice data facade."""
        self.sales_invoice = sales_invoice
        self.context = InvoiceContextLoader(sales_invoice).load()
        self.zatca_invoice = frappe._dict()
        self.xml = None

        self._validate_invoice()
        self.process()

    @property
    def company_settings(self) -> Document:
        return self.context.company_settings

    @property
    def company_address(self) -> Dict[str, Any]:
        return self.context.company_address

    @property
    def customer_info(self) -> Dict[str, Any]:
        return self.context.customer_info

    @property
    def customer_address(self) -> Dict[str, Any]:
        return self.context.customer_address

    @property
    def customer_country_code(self) -> str:
        return self.context.customer_country_code

    def process(self) -> "ZatcaInvoiceData":
        """Build invoice payload and generate XML through the stable facade."""
        try:
            payload_builder = ZatcaInvoicePayloadBuilder(self.sales_invoice, self.context)
            self.zatca_invoice = payload_builder.build()
            self.xml = ZatcaXml(self.zatca_invoice)
            return self
        except Exception as e:
            log_and_throw_error(
                operation="Process ZATCA Invoice",
                document_name=self.sales_invoice.get("name", "Unknown"),
                exception=e,
            )

    def _validate_invoice(self) -> None:
        """Validate invoice data before processing."""
        ZatcaInvoiceValidate(
            self.company_settings,
            self.sales_invoice,
            self.company_address,
            self.customer_info,
            self.customer_address,
        )

    def get_submission_request_data(self) -> Dict[str, Any]:
        """Return the request data needed to submit this invoice to ZATCA."""
        return {
            "clearance_status": self.zatca_invoice.get("Clearance-Status"),
            "authorization": self.company_settings.get("authorization"),
            "invoice_hash": self.xml.hash,
            "uuid": self.zatca_invoice.get("UUID"),
            "encoded_invoice": encode_invoice_xml_for_api(self.xml),
            "company_settings": self.company_settings,
            "endpoint": self.zatca_invoice.get("EndPoint"),
        }

    def get_generated_qr_code(self) -> str:
        """Return the QR code generated before the ZATCA response is applied."""
        return self.xml.qr_code

    def get_log_context(self) -> Dict[str, Any]:
        """Return audit-log data without exposing internal storage layout."""
        return {
            "uuid": self.zatca_invoice.get("UUID"),
            "invoice_hash": self.xml.hash,
            "generated_qr_code": self.xml.qr_code,
            "api_endpoint": self.zatca_invoice.get("EndPoint"),
            "environment": self.zatca_invoice.get("Environment"),
            "pih": self.zatca_invoice.get("PIH"),
            "invoice_counter": self.zatca_invoice.get("InvoiceCounter"),
            "xml_content": serialize_invoice_xml(self.xml),
        }

    def get_uuid(self) -> str:
        """Return the invoice UUID used across submission and follow-up flows."""
        return self.zatca_invoice.get("UUID", "")

    def create_json_file(self) -> None:
        """Create JSON file for testing purposes."""
        try:
            import random

            num = random.randint(1, 10000)
            file_path = get_bench_relative_path(frappe.local.site) + f"/sales{num}invoice.json"

            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(self.zatca_invoice, file, ensure_ascii=False, indent=2)
        except Exception as e:
            frappe.log_error(f"Error creating JSON file: {str(e)}", "ZATCA JSON Error")
