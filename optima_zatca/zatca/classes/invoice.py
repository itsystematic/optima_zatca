import json
import uuid
import frappe
from frappe import _, _dict
from datetime import datetime
from frappe.utils import flt, get_bench_relative_path
from typing import Dict, List, Tuple, Optional, Any

from optima_zatca.zatca.classes.validate import ZatcaInvoiceValidate
from optima_zatca.zatca.classes.xml import ZatcaXml
from optima_zatca.zatca.utils import log_and_throw_error
from frappe.model.document import Document


class ZatcaInvoiceData:
    """
    Handles ZATCA invoice data processing and XML generation for ERPNext Sales Invoices.
    """
    
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
        "prepayment": "386"
    }

    def __init__(self, sales_invoice: Document):
        """Initialize ZATCA invoice data processor."""
        self.sales_invoice = sales_invoice
        self.zatca_invoice = frappe._dict()
        self.prepayment_idx = 1
        
        # Load related documents
        self._load_related_documents()
        
        # Validate before processing
        self._validate_invoice()
        
        # Process invoice data
        self.process()


    def process(self) -> 'ZatcaInvoiceData':
        """Main processing method for ZATCA invoice data."""
        try:
            self._determine_tax_inclusion()
            self._build_zatca_invoice_data()
            self._generate_xml()
            return self
        except Exception as e:
            log_and_throw_error(
                operation="Process ZATCA Invoice",
                document_name=self.sales_invoice.get("name", "Unknown"),
                exception=e
            )


    def _load_related_documents(self) -> None:
        """Load all related documents needed for processing."""
        try:
            self.company_settings = self._get_company_settings()
            self.company_address = self._get_address(self.sales_invoice.get("company_address"))
            self.customer_info = self._get_customer_info()
            self.customer_address = self._get_address(self.sales_invoice.get("customer_address"))
            self.customer_country_code = self._get_code_from_country()
            
        except Exception as e:
            log_and_throw_error(
                operation="Load Related Documents",
                document_name=self.sales_invoice.get("name", "Unknown"),
                exception=e
            )


    def _get_company_settings(self) -> Document:
        """Get company ZATCA settings."""
        commercial_register = self.sales_invoice.get("commercial_register")
        if not commercial_register:
            frappe.throw(_("Commercial Register is required for ZATCA processing"))
        
        return frappe.get_doc("Optima Zatca Setting", {"commercial_register": commercial_register})

    def _get_address(self, address_name: str) -> Dict:
        """Get address document safely."""
        if not address_name:
            return {}
        try:
            return frappe.get_doc("Address", address_name)
        except frappe.DoesNotExistError:
            frappe.log_error(f"Address {address_name} not found", "ZATCA Address Error")
            return {}

    def _get_customer_info(self) -> Dict:
        """Get customer information safely."""
        customer_name = self.sales_invoice.get("customer")
        if not customer_name:
            return {}
        try:
            return frappe.get_doc("Customer", customer_name)
        except frappe.DoesNotExistError:
            frappe.log_error(f"Customer {customer_name} not found", "ZATCA Customer Error")
            return {}

    def _get_code_from_country(self) -> str:
        """Get country code from customer address."""
        try:
            if not self.customer_address or not self.customer_address.get("country"):
                return self.DEFAULT_COUNTRY_CODE
            
            country_name = self.customer_address.get("country")
            country_code = frappe.db.get_value("Country", country_name, "code")
            
            if country_code:
                return country_code.upper()
            else:
                frappe.log_error(f"Country code not found for country: {country_name}", "ZATCA Country Code Error")
                return self.DEFAULT_COUNTRY_CODE
                
        except Exception as e:
            frappe.log_error(f"Error getting country code: {str(e)}", "ZATCA Country Code Error")
            return self.DEFAULT_COUNTRY_CODE


    def _validate_invoice(self) -> None:
        """Validate invoice data before processing."""
        validator = ZatcaInvoiceValidate(
            self.company_settings,
            self.sales_invoice,
            self.company_address,
            self.customer_info,
            self.customer_address
        )


    def _determine_tax_inclusion(self) -> None:
        """Determine if tax is included in print rate."""
        taxes = self.sales_invoice.get("taxes", [])
        self.included_in_print_rate = any(
            tax.get("included_in_print_rate") for tax in taxes
        )


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
        
        self.zatca_invoice.update({
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
        })

    def _add_company_information(self) -> None:
        """Add company information to ZATCA invoice."""
        self.zatca_invoice["company"] = _dict({
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
        })

    def _add_customer_information(self) -> None:
        """Add customer information based on customer type."""
        customer_type = self.customer_info.get("customer_type")
        
        if customer_type == self.COMPANY_CUSTOMER_TYPE:
            self._add_company_customer()
        elif customer_type == self.INDIVIDUAL_CUSTOMER_TYPE:
            self._add_individual_customer()

    def _add_company_customer(self) -> None:
        """Add company customer information."""
        self.zatca_invoice["customer"] = _dict({
            "ID": self.customer_info.get("registration_value"),
            "schemeID": self.customer_info.get("registration_type"),
            "CompanyID": self.customer_info.get("tax_id"),
            "RegistrationName": (
                self.customer_info.get("customer_name_in_arabic") or 
                self.customer_info.get("name")
            ),
            "IdentificationCode": self.customer_country_code,
            "CitySubdivisionName": self.customer_address.get("district"),
            "BuildingNumber": self.customer_address.get("building_no"),
            "StreetName": self.customer_address.get("address_line1"),
            "PostalZone": self.customer_address.get("pincode"),
            "CityName": self.customer_address.get("city"),
            "CountrySubentity": self.customer_address.get("state"),
            "TaxSchemeID": self.DEFAULT_TAX_SCHEME,
        })

    def _add_individual_customer(self) -> None:
        """Add individual customer information."""
        self.zatca_invoice["customer"] = {
            "TaxSchemeID": self.DEFAULT_TAX_SCHEME,
            "ID": self.customer_info.get("registration_value"),
            "schemeID": self.customer_info.get("registration_type"),
            "RegistrationName": self.sales_invoice.get("customer_name")
        }

    def _add_invoice_type_data(self) -> None:
        """Add invoice type and status information."""
        invoice_type_info = self._determine_invoice_type()
        pih, icv = self._get_invoice_counter_and_pih(invoice_type_info["EndPoint"])
        
        invoice_type_info.update({
            "InvoiceCounter": str(icv),
            "PIH": str(pih),
            "Environment": self.company_settings.get("api_endpoints"),
        })
        
        self.zatca_invoice.update(invoice_type_info)

    def _determine_invoice_type(self) -> Dict[str, str]:
        """Determine invoice type based on various conditions."""
        sales_invoice_type = self.sales_invoice.get("sales_invoice_type")
        customer_type = self.customer_info.get("customer_type")
        is_company = customer_type == self.COMPANY_CUSTOMER_TYPE
        is_return = self.sales_invoice.get("is_return") == 1
        is_debit_note = self.sales_invoice.get("is_debit_note") == 1
        is_foreign = self.customer_country_code != self.DEFAULT_COUNTRY_CODE
        
        # Determine invoice type code name
        if is_foreign and customer_type == self.INDIVIDUAL_CUSTOMER_TYPE:
            type_code_name = "0200100"
        elif is_foreign:
            type_code_name = "0100100"
        elif is_company:
            type_code_name = "0100000"
        else:
            type_code_name = "0200000"
        
        # Determine invoice status and clearance
        invoice_status = "Standard" if is_company else "Simplified"
        clearance_status = "1" if is_company else "0"
        
        # Determine sub status and type code
        if is_return:
            sub_status, type_code = "credit", self.INVOICE_TYPE_CODES["credit"]
        elif is_debit_note:
            sub_status, type_code = "debit", self.INVOICE_TYPE_CODES["debit"]
        else:
            sub_status, type_code = "normal", self.INVOICE_TYPE_CODES["normal"]
        
        # Override for advance payments
        if sales_invoice_type in self.PREPAYMENT_TYPES:
            type_code = self.INVOICE_TYPE_CODES["prepayment"]
        
        # Determine endpoint
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
        elif check_pcsid and check_csid:
            return "reporting"
        elif check_csid and check_csr:
            return "complainace_checks"
        else:
            return ""

    def _add_additional_invoice_info(self) -> None:
        """Add additional invoice information for returns/debits."""
        if self.sales_invoice.get("is_return") == 1 or self.sales_invoice.get("is_debit_note") == 1:
            self.zatca_invoice.update({
                "InstructionNote": self.sales_invoice.get("reason_for_issuance"),
                "PaymentMeansCode": "10",
                "ReturnAgainst": self.sales_invoice.get("return_against"),
            })
        
        # Add delivery date for company customers (non-credit/debit)
        if (self.customer_info.get("customer_type") == self.COMPANY_CUSTOMER_TYPE and 
            self.zatca_invoice.get("InvoiceSubStatus") not in ["credit", "debit"]):
            self.zatca_invoice["ActualDeliveryDate"] = str(self.sales_invoice.get("posting_date"))

    def _add_global_taxes(self) -> None:
        """Add global tax information."""
        self.zatca_invoice.update({
            "TaxAmount": f"{abs(self.sales_invoice.get('total_taxes_and_charges', 0)):.2f}",
            "TaxTotalTaxAmount": f"{abs(self.sales_invoice.get('base_total_taxes_and_charges', 0)):.2f}",
            "TaxCategorySchemeID": "UNCL5305",
        })

    def _add_invoice_totals(self) -> None:
        """Add all invoice total amounts."""
        try:
            totals = self._calculate_all_totals()
            self.zatca_invoice.update(totals)
        except Exception as e:
            log_and_throw_error(
                operation="Calculate Invoice Totals",
                document_name=self.sales_invoice.get("name", "Unknown"),
                exception=e
            )

    def _calculate_all_totals(self) -> Dict[str, str]:
        """Calculate all required totals for the invoice."""
        # Get base amounts
        line_extension = self._get_line_extension_amount()
        tax_exclusive = self._get_tax_exclusive_amount()
        tax_inclusive = self._get_tax_inclusive_amount()
        allowance_total = self._get_allowance_total_amount()
        prepaid = self._get_prepayment_amount()
        rounding = self._get_rounding_amount()
        
        # Calculate payable amount
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
            amount = (self.sales_invoice.get("net_total", 0) + 
                     self.sales_invoice.get("discount_amount", 0))
        else:
            amount = self.sales_invoice.get("total", 0)
        return f"{abs(flt(amount, 2)):.2f}"

    def _get_tax_exclusive_amount(self) -> str:
        """Get tax exclusive amount."""
        return f"{abs(flt(self.sales_invoice.get('net_total', 0), 2)):.2f}"

    def _get_tax_inclusive_amount(self) -> str:
        """Get tax inclusive amount."""
        return f"{abs(flt(self.sales_invoice.get('grand_total', 0), 2)):.2f}"

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
            
            # Process regular items
            items = self.sales_invoice.get("items", [])
            for item in items:
                self._add_invoice_item(item, invoice_lines)
                self._add_tax_category(item, tax_subtotals)
            
            # Process prepayments if applicable
            if self.sales_invoice.get("sales_invoice_type") in self.ADJUSTMENT_TYPES:
                self._add_prepayment_items(invoice_lines)
            
            self.zatca_invoice["items"] = invoice_lines
            self.zatca_invoice["TaxSubtotal"] = list(tax_subtotals.values())
            
        except Exception as e:
            log_and_throw_error(
                operation="Add Invoice Lines and Taxes",
                document_name=self.sales_invoice.get("name", "Unknown"),
                exception=e
            )

    def _add_invoice_item(self, item: Dict, invoice_lines: List) -> None:
        """Add a single invoice item."""
        item_row = {
            "ID": str(item.get("idx")),
            "InvoicedQuantity": str(abs(item.get("qty", 0))),
            "LineExtensionAmount": f"{abs(flt(item.get('line_extension_amount', 0), 2)):.2f}",
            "TaxAmount": f"{abs(flt(item.get('tax_amount', 0), 2)):.2f}",
            "RoundingAmount": f"{abs(flt(item.get('total_amount', 0), 2)):.2f}",
            "Name": item.get("item_name"),
            "TaxCategory": self._get_item_tax_category(item),
            "Percent": f"{abs(flt(item.get('tax_rate', 0), 2)):.2f}",
            "TaxScheme": self.DEFAULT_TAX_SCHEME,
            "PriceAmount": f"{abs(flt(item.get('price_amount', 0), 2)):.2f}",
        }
        
        # Add discount information if present
        if item.get("discount_amount"):
            item_row.update({
                "ChargeIndicator": "false",
                "Amount": f"{abs(flt(item.get('discount_amount', 0), 2)):.2f}"
            })
        
        invoice_lines.append(item_row)

    def _get_item_tax_category(self, item: Dict) -> str:
        """Get tax category for an item."""
        tax_category = item.get("tax_category")
        if not tax_category and item.get("item_tax_template"):
            tax_category = frappe.db.get_value(
                "Item Tax Template", 
                item.get("item_tax_template"), 
                "tax_category"
            )
        return tax_category or ""

    def _add_prepayment_items(self, invoice_lines: List) -> None:
        """Add prepayment items to invoice lines."""
        self.prepayment_idx = len(self.sales_invoice.get("items", [])) + 1
        
        prepayments = [
            p for p in self.sales_invoice.get("prepayments_invcoies", [])
            if (p.get("prepayment_type") in self.PREPAYMENT_TYPES and
                p.get("been_return") == 0 and
                p.get("is_return") == 0)
        ]
        
        for prepayment in prepayments:
            self._add_single_prepayment_item(prepayment, invoice_lines)

    def _add_single_prepayment_item(self, prepayment: Dict, invoice_lines: List) -> None:
        """Add a single prepayment item."""
        try:
            prepayment_row = {
                "is_prepayment": True,
                "ID": str(self.prepayment_idx),
                "InvoicedQuantity": "0.00000",
                "LineExtensionAmount": "0.00",
                "TaxTotalAmount": "0.00",
                "TaxSubtotalTaxableAmount": f"{abs(prepayment.get('deducted_taxable_amount', 0)):.2f}",
                "TaxSubtotalTaxAmount": f"{abs(prepayment.get('deducted_tax_amount', 0)):.2f}",
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
                exception=e
            )

    def _add_tax_category(self, item: Dict, tax_subtotals: Dict) -> None:
        """Add or update tax category in tax subtotals."""
        tax_category = self._get_item_tax_category(item)
        
        if tax_category not in tax_subtotals:
            tax_subtotals[tax_category] = self._create_tax_subtotal_entry(item, tax_category)
        else:
            # Update existing tax category
            tax_subtotals[tax_category]["TaxableAmount"] += abs(item.get("net_amount") or 0)
            tax_subtotals[tax_category]["AllowanceChargeAmount"] += abs(item.get("item_discount") or 0)

    def _create_tax_subtotal_entry(self, item: Dict, tax_category: str) -> Dict:
        """Create a new tax subtotal entry."""
        entry = {
            "TaxCategory": tax_category,
            "Percent": str(abs(item.get("tax_rate") or 0)),
            "TaxAmount": "0.00",
            "TaxableAmount": abs(item.get("net_amount") or 0),
            "TaxCategorySchemeID": "UNCL5305",
            "TaxSchemeID": self.DEFAULT_TAX_SCHEME,
            "schemeAgencyID": "6",
            "TaxExemptionReasonCode": "",
            "TaxExemptionReason": "",
            "ChargeIndicator": "false",
            "AllowanceChargeReason": "discount",
            "AllowanceChargeAmount": abs(item.get("item_discount") or 0),
        }
        
        if tax_category == "S":
            entry["TaxAmount"] = str(abs(self.sales_invoice.get("total_taxes_and_charges", 0)))
        else:
            # Handle tax exemption
            exemption_code = item.get("tax_exemption")
            if exemption_code:
                entry["TaxExemptionReasonCode"] = exemption_code
                exemption_description = frappe.db.get_value(
                    "Tax Exemption", exemption_code, "description"
                )
                entry["TaxExemptionReason"] = (exemption_description or "").strip()
        
        return entry

    def _add_additional_data(self) -> None:
        """Add additional data like purchase order information."""
        additional_data = {}
        
        if self.sales_invoice.get("po_no") and self.sales_invoice.get("po_date"):
            additional_data.update({
                "PurchaseOrderID": self.sales_invoice.get("po_no"),
                "PurchaseOrderIssueDate": self.sales_invoice.get("po_date")
            })
        
        if additional_data:
            self.zatca_invoice.update(additional_data)

    def _generate_xml(self) -> None:
        """Generate XML from ZATCA invoice data."""
        self.xml = ZatcaXml(self.zatca_invoice)

    def _get_invoice_counter_and_pih(self, endpoint: str) -> Tuple[str, int]:
        """Get invoice counter and PIH from database."""
        try:
            return get_invoice_counter_and_pih(endpoint, self.company_settings)
        except Exception as e:
            frappe.log_error(f"Error getting invoice counter: {str(e)}", "ZATCA Counter Error")
            return "idfhpoahfosanldhvusjnaljuidsuhahehah", 1

    def create_json_file(self) -> None:
        """Create JSON file for testing purposes."""
        try:
            import random
            num = random.randint(1, 10000)
            file_path = get_bench_relative_path(frappe.local.site) + f"/sales{num}invoice.json"
            
            with open(file_path, "w", encoding='utf-8') as file:
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