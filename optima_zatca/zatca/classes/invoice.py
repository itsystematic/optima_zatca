import json
import uuid
import frappe
from frappe import _, _dict
from dataclasses import dataclass
from datetime import datetime
from frappe.utils import flt, get_bench_relative_path
from typing import Any, Dict, List, Tuple

from optima_zatca.zatca.classes.validate import ZatcaInvoiceValidate
from optima_zatca.zatca.classes.xml import ZatcaXml
from optima_zatca.zatca.utils import log_and_throw_error
from optima_zatca.zatca.xml_transport import encode_invoice_xml_for_api, serialize_invoice_xml
from frappe.model.document import Document


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


class ZatcaInvoicePayloadBuilder:
    DEFAULT_COUNTRY_CODE = "SA"
    DEFAULT_TAX_SCHEME = "VAT"
    DEFAULT_CURRENCY = "SAR"
    PROFILE_ID = "reporting:1.0"

    COMPANY_CUSTOMER_TYPE = "Company"
    INDIVIDUAL_CUSTOMER_TYPE = "Individual"

    ADJUSTMENT_TYPES = ["Adjustment", "Final Adjustment"]
    PREPAYMENT_TYPES = ["Initial Prepayment", "Prepayment"]

    INVOICE_TYPE_CODES = {
        "normal": "388",
        "credit": "381",
        "debit": "383",
        "prepayment": "386",
    }

    def __init__(self, sales_invoice: Document, context: LoadedInvoiceContext):
        self.sales_invoice = sales_invoice
        self.context = context
        self.zatca_invoice = frappe._dict()
        self.prepayment_idx = 1
        self.included_in_print_rate = False

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

    def build(self) -> _dict:
        """Build the ZATCA invoice payload from loaded invoice context."""
        self._determine_tax_inclusion()
        self._build_zatca_invoice_data()
        return self.zatca_invoice

    def _determine_tax_inclusion(self) -> None:
        """Determine if tax is included in print rate."""
        taxes = self.sales_invoice.get("taxes", [])
        self.included_in_print_rate = any(
            tax.get("included_in_print_rate") for tax in taxes
        )

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float, returning 0 if None."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _validate_and_adjust_tax_amount(self) -> float:
        """
        Validate that net_total + tax = grand_total.
        If there's a rounding difference, adjust the tax amount to ensure ZATCA validation passes.
        This method caches the adjusted tax amount for use across the invoice.

        Returns:
            Adjusted tax amount that ensures: net_total + tax = grand_total
        """
        if hasattr(self, "_adjusted_tax_amount"):
            return self._adjusted_tax_amount

        net_total = flt(self._safe_float(self.sales_invoice.get("net_total")), 2)
        tax_amount = flt(self._safe_float(self.sales_invoice.get("total_taxes_and_charges")), 2)
        grand_total = flt(self._safe_float(self.sales_invoice.get("grand_total")), 2)
        calculated_total = flt(net_total + tax_amount, 2)
        difference = flt(grand_total - calculated_total, 2)

        if abs(difference) > 0:
            adjusted_tax = flt(tax_amount + difference, 2)

            frappe.log_error(
                f"""ZATCA Tax Rounding Adjustment
Invoice: {self.sales_invoice.get('name')}
Net Total: {net_total}
Original Tax: {tax_amount}
Grand Total: {grand_total}
Calculated Total: {calculated_total}
Difference: {difference}
Adjusted Tax: {adjusted_tax}
Formula: {net_total} + {adjusted_tax} = {grand_total}
""",
                "ZATCA Tax Rounding Adjustment",
            )

            self._adjusted_tax_amount = adjusted_tax
            return adjusted_tax

        self._adjusted_tax_amount = tax_amount
        return tax_amount

    def _build_zatca_invoice_data(self) -> None:
        """Build all ZATCA invoice data."""
        self._add_basic_invoice_data()
        self._add_company_information()
        self._add_customer_information()
        self._add_invoice_type_data()
        self._add_additional_invoice_info()
        self._add_global_taxes()
        self._add_invoice_totals()
        self._add_invoice_lines_and_taxes()
        self._add_additional_data()

    def _add_basic_invoice_data(self) -> None:
        """Add basic invoice information."""
        posting_time = str(self.sales_invoice.get("posting_time"))
        time_format = "%H:%M:%S.%f" if "." in posting_time else "%H:%M:%S"
        formatted_time = datetime.strptime(posting_time, time_format).strftime("%H:%M:%S")

        self.zatca_invoice.update(
            {
                "X509SerialNumber": self.company_settings.get("serial_number509"),
                "X509IssuerName": self.company_settings.get("issuer_name"),
                "DigestValue": self.company_settings.get("certificate_hash"),
                "Certificate": self.company_settings.get("certificate"),
                "SignatureInformation": self.company_settings.get("signature"),
                "private_key": self.company_settings.get("private_key"),
                "public_key": self.company_settings.get("public_key", "").strip(),
                "ProfileID": self.PROFILE_ID,
                "ID": self.sales_invoice.get("name"),
                "UUID": str(uuid.uuid4()),
                "IssueDate": str(self.sales_invoice.get("posting_date")),
                "IssueTime": formatted_time,
                "Note": self.sales_invoice.get("remarks", "No Remarks"),
                "DocumentCurrencyCode": self.sales_invoice.get("currency"),
                "TaxCurrencyCode": self.DEFAULT_CURRENCY,
                "PaymentNote": self.sales_invoice.get("terms"),
            }
        )

    def _add_company_information(self) -> None:
        """Add company information to ZATCA invoice."""
        self.zatca_invoice["company"] = _dict(
            {
                "ID": self.company_settings.get("commercial_register"),
                "schemeID": self.company_settings.get("registration_type"),
                "CompanyID": self.company_settings.get("organization_identifier"),
                "RegistrationName": self.company_settings.get("organization_name", "").strip(),
                "IdentificationCode": self.DEFAULT_COUNTRY_CODE,
                "CitySubdivisionName": self.company_address.get("district"),
                "BuildingNumber": self.company_address.get("building_no"),
                "StreetName": self.company_address.get("address_line1"),
                "PostalZone": self.company_address.get("pincode"),
                "CityName": self.company_address.get("city"),
                "CountrySubentity": self.company_address.get("state"),
                "TaxSchemeID": self.DEFAULT_TAX_SCHEME,
                "DefaultCurrency": self.DEFAULT_CURRENCY,
            }
        )

    def _add_customer_information(self) -> None:
        """Add customer information based on customer type."""
        customer_type = self.customer_info.get("customer_type")

        if customer_type == self.COMPANY_CUSTOMER_TYPE:
            self._add_company_customer()
        elif customer_type == self.INDIVIDUAL_CUSTOMER_TYPE:
            self._add_individual_customer()

    def _add_company_customer(self) -> None:
        """Add company customer information."""
        self.zatca_invoice["customer"] = _dict(
            {
                "ID": self.customer_info.get("registration_value"),
                "schemeID": self.customer_info.get("registration_type"),
                "CompanyID": self.customer_info.get("tax_id"),
                "RegistrationName": (
                    self.customer_info.get("customer_name_in_arabic")
                    or self.customer_info.get("name")
                ),
                "IdentificationCode": self.customer_country_code,
                "CitySubdivisionName": self.customer_address.get("district"),
                "BuildingNumber": self.customer_address.get("building_no"),
                "StreetName": self.customer_address.get("address_line1"),
                "PostalZone": self.customer_address.get("pincode"),
                "CityName": self.customer_address.get("city"),
                "CountrySubentity": self.customer_address.get("state"),
                "TaxSchemeID": self.DEFAULT_TAX_SCHEME,
            }
        )

    def _add_individual_customer(self) -> None:
        """Add individual customer information."""
        self.zatca_invoice["customer"] = {
            "TaxSchemeID": self.DEFAULT_TAX_SCHEME,
            "ID": self.customer_info.get("registration_value"),
            "schemeID": self.customer_info.get("registration_type"),
            "RegistrationName": self.sales_invoice.get("customer_name"),
        }

    def _add_invoice_type_data(self) -> None:
        """Add invoice type and status information."""
        invoice_type_info = self._determine_invoice_type()
        pih, icv = self._get_invoice_counter_and_pih(invoice_type_info["EndPoint"])

        invoice_type_info.update(
            {
                "InvoiceCounter": str(icv),
                "PIH": str(pih),
                "Environment": self.company_settings.get("api_endpoints"),
            }
        )

        self.zatca_invoice.update(invoice_type_info)

    def _determine_invoice_type(self) -> Dict[str, str]:
        """Determine invoice type based on various conditions."""
        sales_invoice_type = self.sales_invoice.get("sales_invoice_type")
        customer_type = self.customer_info.get("customer_type")
        is_company = customer_type == self.COMPANY_CUSTOMER_TYPE
        is_return = self.sales_invoice.get("is_return") == 1
        is_debit_note = self.sales_invoice.get("is_debit_note") == 1
        is_foreign = self.customer_country_code != self.DEFAULT_COUNTRY_CODE

        if is_foreign and customer_type == self.INDIVIDUAL_CUSTOMER_TYPE:
            type_code_name = "0200100"
        elif is_foreign:
            type_code_name = "0100100"
        elif is_company:
            type_code_name = "0100000"
        else:
            type_code_name = "0200000"

        invoice_status = "Standard" if is_company else "Simplified"
        clearance_status = "1" if is_company else "0"

        if is_return:
            sub_status, type_code = "credit", self.INVOICE_TYPE_CODES["credit"]
        elif is_debit_note:
            sub_status, type_code = "debit", self.INVOICE_TYPE_CODES["debit"]
        else:
            sub_status, type_code = "normal", self.INVOICE_TYPE_CODES["normal"]

        if sales_invoice_type in self.PREPAYMENT_TYPES:
            type_code = self.INVOICE_TYPE_CODES["prepayment"]

        endpoint = self._determine_endpoint(invoice_status)

        return {
            "InvoiceTypeCode": type_code,
            "InvoiceTypeCodeName": type_code_name,
            "InvoiceStatus": invoice_status,
            "InvoiceSubStatus": sub_status,
            "Clearance-Status": clearance_status,
            "EndPoint": endpoint,
        }

    def _determine_endpoint(self, invoice_status: str) -> str:
        """Determine API endpoint based on company settings."""
        settings = self.company_settings
        check_pcsid = settings.get("check_pcsid") == 1
        check_csid = settings.get("check_csid") == 1
        check_csr = settings.get("check_csr") == 1

        if check_pcsid and check_csid and invoice_status == "Standard":
            return "clearance"
        if check_pcsid and check_csid:
            return "reporting"
        if check_csid and check_csr:
            return "complainace_checks"
        return ""

    def _add_additional_invoice_info(self) -> None:
        """Add additional invoice information for returns/debits."""
        if self.sales_invoice.get("is_return") == 1 or self.sales_invoice.get("is_debit_note") == 1:
            self.zatca_invoice.update(
                {
                    "InstructionNote": self.sales_invoice.get("reason_for_issuance"),
                    "PaymentMeansCode": "10",
                    "ReturnAgainst": self.sales_invoice.get("return_against"),
                }
            )

        if (
            self.customer_info.get("customer_type") == self.COMPANY_CUSTOMER_TYPE
            and self.zatca_invoice.get("InvoiceSubStatus") not in ["credit", "debit"]
        ):
            self.zatca_invoice["ActualDeliveryDate"] = str(self.sales_invoice.get("posting_date"))

    def _add_global_taxes(self) -> None:
        """Add global tax information with rounding validation."""
        tax_amount = self._validate_and_adjust_tax_amount()
        base_tax = self._safe_float(self.sales_invoice.get("base_total_taxes_and_charges"))

        if base_tax != self._safe_float(self.sales_invoice.get("total_taxes_and_charges")):
            original_tax = self._safe_float(self.sales_invoice.get("total_taxes_and_charges"))
            if original_tax != 0:
                adjustment_ratio = tax_amount / original_tax
                base_tax = flt(base_tax * adjustment_ratio, 2)
        else:
            base_tax = tax_amount

        self.zatca_invoice.update(
            {
                "TaxAmount": f"{abs(flt(tax_amount, 2)):.2f}",
                "TaxTotalTaxAmount": f"{abs(flt(base_tax, 2)):.2f}",
                "TaxCategorySchemeID": "UNCL5305",
            }
        )

    def _add_invoice_totals(self) -> None:
        """Add all invoice total amounts."""
        try:
            totals = self._calculate_all_totals()
            self.zatca_invoice.update(totals)
        except Exception as e:
            log_and_throw_error(
                operation="Calculate Invoice Totals",
                document_name=self.sales_invoice.get("name", "Unknown"),
                exception=e,
            )

    def _calculate_all_totals(self) -> Dict[str, str]:
        """Calculate all required totals for the invoice."""
        line_extension = self._get_line_extension_amount()
        tax_exclusive = self._get_tax_exclusive_amount()
        tax_inclusive = self._get_tax_inclusive_amount()
        allowance_total = self._get_allowance_total_amount()
        prepaid = self._get_prepayment_amount()
        rounding = self._get_rounding_amount()
        payable = float(tax_inclusive) - float(prepaid) + float(rounding)

        return {
            "LineExtensionAmount": line_extension,
            "TaxExclusiveAmount": tax_exclusive,
            "TaxInclusiveAmount": tax_inclusive,
            "AllowanceTotalAmount": allowance_total,
            "PrepaidAmount": prepaid,
            "PayableAmount": f"{abs(flt(payable, 2)):.2f}",
        }

    def _get_line_extension_amount(self) -> str:
        """Calculate line extension amount."""
        if self.included_in_print_rate:
            amount = self.sales_invoice.get("net_total", 0) + self.sales_invoice.get("discount_amount", 0)
        else:
            amount = self.sales_invoice.get("total", 0)
        return f"{abs(flt(amount, 2)):.2f}"

    def _get_tax_exclusive_amount(self) -> str:
        """Get tax exclusive amount."""
        return f"{abs(flt(self._safe_float(self.sales_invoice.get('net_total')), 2)):.2f}"

    def _get_tax_inclusive_amount(self) -> str:
        """Get tax inclusive amount."""
        return f"{abs(flt(self._safe_float(self.sales_invoice.get('grand_total')), 2)):.2f}"

    def _get_allowance_total_amount(self) -> str:
        """Get total allowances amount."""
        discount = self.sales_invoice.get("discount_amount", 0)
        return f"{abs(flt(discount, 2)):.2f}"

    def _get_prepayment_amount(self) -> str:
        """Calculate prepayment amount."""
        if self.sales_invoice.get("sales_invoice_type") not in self.ADJUSTMENT_TYPES:
            return "0.00"

        prepayments = self.sales_invoice.get("prepayments_invcoies", [])
        prepayment_sum = sum(
            (p.get("deducted_taxable_amount", 0) + p.get("deducted_tax_amount", 0))
            for p in prepayments
            if p.get("prepayment_type") in self.PREPAYMENT_TYPES
        )
        return f"{abs(prepayment_sum):.2f}"

    def _get_rounding_amount(self) -> str:
        """Get rounding amount (not implemented yet)."""
        return "0.00"

    def _add_invoice_lines_and_taxes(self) -> None:
        """Add invoice lines and tax categories."""
        try:
            tax_subtotals = {}
            invoice_lines = []

            for item in self.sales_invoice.get("items", []):
                self._add_invoice_item(item, invoice_lines)
                self._add_tax_category(item, tax_subtotals)

            if self.sales_invoice.get("sales_invoice_type") in self.ADJUSTMENT_TYPES:
                self._add_prepayment_items(invoice_lines)

            self.zatca_invoice["items"] = invoice_lines
            self.zatca_invoice["TaxSubtotal"] = list(tax_subtotals.values())
        except Exception as e:
            log_and_throw_error(
                operation="Add Invoice Lines and Taxes",
                document_name=self.sales_invoice.get("name", "Unknown"),
                exception=e,
            )

    def _add_invoice_item(self, item: Dict[str, Any], invoice_lines: List[Dict[str, Any]]) -> None:
        """Add a single invoice item."""
        item_row = {
            "ID": str(item.get("idx")),
            "InvoicedQuantity": str(abs(self._safe_float(item.get("qty")))),
            "LineExtensionAmount": f"{abs(flt(self._safe_float(item.get('line_extension_amount')), 2)):.2f}",
            "TaxAmount": f"{abs(flt(self._safe_float(item.get('tax_amount')), 2)):.2f}",
            "RoundingAmount": f"{abs(flt(self._safe_float(item.get('total_amount')), 2)):.2f}",
            "Name": item.get("item_name"),
            "TaxCategory": self._get_item_tax_category(item),
            "Percent": f"{abs(flt(self._safe_float(item.get('tax_rate')), 2)):.2f}",
            "TaxScheme": self.DEFAULT_TAX_SCHEME,
            "PriceAmount": f"{abs(flt(self._safe_float(item.get('price_amount')), 2)):.2f}",
        }

        if item.get("discount_amount"):
            item_row.update(
                {
                    "ChargeIndicator": "false",
                    "Amount": f"{abs(flt(self._safe_float(item.get('discount_amount')), 2)):.2f}",
                }
            )

        invoice_lines.append(item_row)

    def _get_item_tax_category(self, item: Dict[str, Any]) -> str:
        """Get tax category for an item."""
        tax_category = item.get("tax_category")
        if not tax_category and item.get("item_tax_template"):
            tax_category = frappe.db.get_value(
                "Item Tax Template",
                item.get("item_tax_template"),
                "tax_category",
            )
        return tax_category or ""

    def _add_prepayment_items(self, invoice_lines: List[Dict[str, Any]]) -> None:
        """Add prepayment items to invoice lines."""
        self.prepayment_idx = len(self.sales_invoice.get("items", [])) + 1

        prepayments = [
            p
            for p in self.sales_invoice.get("prepayments_invcoies", [])
            if (
                p.get("prepayment_type") in self.PREPAYMENT_TYPES
                and p.get("been_return") == 0
                and p.get("is_return") == 0
            )
        ]

        for prepayment in prepayments:
            self._add_single_prepayment_item(prepayment, invoice_lines)

    def _add_single_prepayment_item(
        self,
        prepayment: Dict[str, Any],
        invoice_lines: List[Dict[str, Any]],
    ) -> None:
        """Add a single prepayment item."""
        try:
            prepayment_row = {
                "is_prepayment": True,
                "ID": str(self.prepayment_idx),
                "InvoicedQuantity": "0.00000",
                "LineExtensionAmount": "0.00",
                "TaxTotalAmount": "0.00",
                "TaxSubtotalTaxableAmount": f"{abs(self._safe_float(prepayment.get('deducted_taxable_amount'))):.2f}",
                "TaxSubtotalTaxAmount": f"{abs(self._safe_float(prepayment.get('deducted_tax_amount'))):.2f}",
                "RoundingAmount": "0",
                "Name": "Advance Payment",
                "TaxCategory": str(prepayment.get("tax_category", "")),
                "Percent": f"{flt(prepayment.get('percent', 0), 2):.2f}",
                "TaxScheme": self.DEFAULT_TAX_SCHEME,
                "PriceAmount": "0.00",
                "PrepaymentID": str(prepayment.get("reference_invoice", "")),
                "PrepaymentUUID": str(prepayment.get("uuid", "")),
                "PrepaymentIssueDate": str(prepayment.get("issue_date", "")),
                "PrepaymentIssueTime": str(prepayment.get("issue_time", "")),
                "PrepaymentTypeCode": self.INVOICE_TYPE_CODES["prepayment"],
                "TaxCategoryTaxSchemeID": self.DEFAULT_TAX_SCHEME,
            }

            self.prepayment_idx += 1
            invoice_lines.append(prepayment_row)
        except Exception as e:
            log_and_throw_error(
                operation="Add Prepayment Item",
                document_name=self.sales_invoice.get("name", "Unknown"),
                exception=e,
            )

    def _add_tax_category(self, item: Dict[str, Any], tax_subtotals: Dict[str, Dict[str, Any]]) -> None:
        """Add or update tax category in tax subtotals."""
        tax_category = self._get_item_tax_category(item)

        if tax_category not in tax_subtotals:
            tax_subtotals[tax_category] = self._create_tax_subtotal_entry(item, tax_category)
        else:
            tax_subtotals[tax_category]["TaxableAmount"] += abs(self._safe_float(item.get("net_amount")))
            tax_subtotals[tax_category]["AllowanceChargeAmount"] += abs(self._safe_float(item.get("item_discount")))

    def _create_tax_subtotal_entry(self, item: Dict[str, Any], tax_category: str) -> Dict[str, Any]:
        """Create a new tax subtotal entry."""
        entry = {
            "TaxCategory": tax_category,
            "Percent": str(abs(self._safe_float(item.get("tax_rate")))),
            "TaxAmount": "0.00",
            "TaxableAmount": abs(self._safe_float(item.get("net_amount"))),
            "TaxCategorySchemeID": "UNCL5305",
            "TaxSchemeID": self.DEFAULT_TAX_SCHEME,
            "schemeAgencyID": "6",
            "TaxExemptionReasonCode": "",
            "TaxExemptionReason": "",
            "ChargeIndicator": "false",
            "AllowanceChargeReason": "discount",
            "AllowanceChargeAmount": abs(self._safe_float(item.get("item_discount"))),
        }

        if tax_category == "S":
            entry["TaxAmount"] = str(abs(flt(self._validate_and_adjust_tax_amount(), 2)))
        else:
            exemption_code = item.get("tax_exemption")
            if exemption_code:
                entry["TaxExemptionReasonCode"] = exemption_code
                exemption_description = frappe.db.get_value(
                    "Tax Exemption",
                    exemption_code,
                    "description",
                )
                entry["TaxExemptionReason"] = (exemption_description or "").strip()

        return entry

    def _add_additional_data(self) -> None:
        """Add additional data like purchase order information."""
        additional_data = {}

        if self.sales_invoice.get("po_no") and self.sales_invoice.get("po_date"):
            additional_data.update(
                {
                    "PurchaseOrderID": self.sales_invoice.get("po_no"),
                    "PurchaseOrderIssueDate": self.sales_invoice.get("po_date"),
                }
            )

        if additional_data:
            self.zatca_invoice.update(additional_data)

    def _get_invoice_counter_and_pih(self, endpoint: str) -> Tuple[str, int]:
        """Get invoice counter and PIH from database."""
        try:
            return get_invoice_counter_and_pih(endpoint, self.company_settings)
        except Exception as e:
            frappe.log_error(f"Error getting invoice counter: {str(e)}", "ZATCA Counter Error")
            return "idfhpoahfosanldhvusjnaljuidsuhahehah", 1


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


def get_invoice_counter_and_pih(endpoint: str, company_settings: _dict) -> Tuple[str, int]:
    """
    Get the next invoice counter and previous invoice hash.
    
    Args:
        endpoint: API endpoint type
        company_settings: Company ZATCA settings
        
    Returns:
        Tuple of (PIH, ICV)
    """
    default_pih = "idfhpoahfosanldhvusjnaljuidsuhahehah"
    default_icv = 1
    
    try:
        # Determine API endpoints to search
        api_endpoints = [endpoint] if endpoint == "complainace_checks" else ["reporting", "clearance"]
        
        # Query for the last successful invoice
        last_doc = frappe.db.sql("""
            SELECT icv, hash 
            FROM `tabOptima Zatca Logs` 
            WHERE status IN ('Success', 'Warning') 
                AND reference_doctype = 'Sales Invoice' 
                AND company = %(company)s 
                AND commercial_register = %(commercial_register)s 
                AND environment = %(environment)s 
                AND api_endpoint IN %(api_endpoint)s 
                AND icv = (
                    SELECT MAX(icv) 
                    FROM `tabOptima Zatca Logs`
                    WHERE status IN ('Success', 'Warning') 
                        AND reference_doctype = 'Sales Invoice' 
                        AND company = %(company)s 
                        AND commercial_register = %(commercial_register)s 
                        AND environment = %(environment)s 
                        AND api_endpoint IN %(api_endpoint)s 
                )
            LIMIT 1
        """, {
            "company": company_settings.company,
            "commercial_register": company_settings.commercial_register,
            "environment": company_settings.api_endpoints,
            "api_endpoint": api_endpoints
        }, as_dict=True)
        
        if last_doc and last_doc[0].get("icv") not in ["", None]:
            pih = last_doc[0].get("hash") or default_pih
            icv = (last_doc[0].get("icv") or 0) + 1
            return pih, icv
            
        return default_pih, default_icv
        
    except Exception as e:
        frappe.log_error(f"Error getting invoice counter: {str(e)}", "ZATCA Counter Error")
        return default_pih, default_icv
