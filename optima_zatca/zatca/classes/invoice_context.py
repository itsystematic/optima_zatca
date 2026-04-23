import frappe
from frappe import _
from dataclasses import dataclass
from typing import Any, Dict

from frappe.model.document import Document

from optima_zatca.zatca.utils import log_and_throw_error


@dataclass(frozen=True)
class LoadedInvoiceContext:
    company_settings: Document
    company_address: Dict[str, Any]
    customer_info: Dict[str, Any]
    customer_address: Dict[str, Any]
    customer_country_code: str


class InvoiceContextLoader:
    DEFAULT_COUNTRY_CODE = "SA"

    def __init__(self, sales_invoice: Document):
        self.sales_invoice = sales_invoice

    def load(self) -> LoadedInvoiceContext:
        """Load all related documents needed for invoice processing."""
        try:
            company_settings = self._get_company_settings()
            company_address = self._get_address(self.sales_invoice.get("company_address"))
            customer_info = self._get_customer_info()
            customer_address = self._get_address(self.sales_invoice.get("customer_address"))
            customer_country_code = self._get_country_code(customer_address)
            return LoadedInvoiceContext(
                company_settings=company_settings,
                company_address=company_address,
                customer_info=customer_info,
                customer_address=customer_address,
                customer_country_code=customer_country_code,
            )
        except Exception as e:
            log_and_throw_error(
                operation="Load Related Documents",
                document_name=self.sales_invoice.get("name", "Unknown"),
                exception=e,
            )

    def _get_company_settings(self) -> Document:
        """Get company ZATCA settings."""
        commercial_register = self.sales_invoice.get("commercial_register")
        if not commercial_register:
            frappe.throw(_("Commercial Register is required for ZATCA processing"))

        return frappe.get_doc("Optima Zatca Setting", {"commercial_register": commercial_register})

    def _get_address(self, address_name: str) -> Dict[str, Any]:
        """Get address document safely."""
        if not address_name:
            return {}
        try:
            return frappe.get_doc("Address", address_name)
        except frappe.DoesNotExistError:
            frappe.log_error(f"Address {address_name} not found", "ZATCA Address Error")
            return {}

    def _get_customer_info(self) -> Dict[str, Any]:
        """Get customer information safely."""
        customer_name = self.sales_invoice.get("customer")
        if not customer_name:
            return {}
        try:
            return frappe.get_doc("Customer", customer_name)
        except frappe.DoesNotExistError:
            frappe.log_error(f"Customer {customer_name} not found", "ZATCA Customer Error")
            return {}

    def _get_country_code(self, customer_address: Dict[str, Any]) -> str:
        """Get country code from customer address."""
        try:
            if not customer_address or not customer_address.get("country"):
                return self.DEFAULT_COUNTRY_CODE

            country_name = customer_address.get("country")
            country_code = frappe.db.get_value("Country", country_name, "code")

            if country_code:
                return country_code.upper()

            frappe.log_error(
                f"Country code not found for country: {country_name}",
                "ZATCA Country Code Error",
            )
            return self.DEFAULT_COUNTRY_CODE
        except Exception as e:
            frappe.log_error(
                f"Error getting country code: {str(e)}",
                "ZATCA Country Code Error",
            )
            return self.DEFAULT_COUNTRY_CODE
