"""
ZATCA XML Invoice Generation Module

This module handles the creation of ZATCA-compliant XML invoices for Saudi Arabia's
electronic invoicing system (Fatoora).
"""

import re
import copy
import base64
import hashlib
import xml.dom.minidom as mini
from typing import Dict, Tuple, Optional
from pathlib import Path

import frappe
from frappe import _, _dict
from frappe.utils import get_bench_relative_path, flt
from lxml import etree
from bs4 import BeautifulSoup

from optima_zatca.zatca.utils import generate_qr_code, sign_invoice
from optima_zatca.zatca.utils import log_and_throw_error

# XML Namespaces
NAMESPACES = {
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "sig": "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2",
    "sac": "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2",
    "sbc": "urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2",
    "xades": "http://uri.etsi.org/01903/v1.3.2#",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}

# Constants
INVOICE_TYPE_SIMPLIFIED = "Simplified"
INVOICE_TYPE_STANDARD = "Standard"
INVOICE_SUBTYPE_NORMAL = "normal"
INVOICE_SUBTYPE_CREDIT = "credit"
INVOICE_SUBTYPE_DEBIT = "debit"
DEFAULT_TAX_SCHEME = "VAT"
DEFAULT_CURRENCY_CODE = "SAR"
DEFAULT_UNIT_CODE = "PCE"
ENCODING_UTF8 = "utf-8"


class ZatcaXmlGenerator:
    """Generate ZATCA-compliant XML invoices."""
    
    def __init__(self, sales_invoice: _dict):
        """
        Initialize the ZATCA XML generator.
        
        Args:
            sales_invoice: Dictionary containing invoice data
        """
        self.sales_invoice = sales_invoice
        self.tree = None
        self.root = None
        self.hash = None
        self.qr_code = None
        self.generate()
        
    def generate(self) -> Tuple[str, str]:
        """
        Generate the complete ZATCA XML invoice.
        
        Returns:
            Tuple of (invoice_hash, qr_code)
        """
        try:
            self._create_xml_tree()
            self._add_general_data()
            self._add_supplier_information()
            self._add_customer_information()
            self._add_items_data()
            
            # Calculate and sign invoice
            invoice_hash_encoded, invoice_hash = self._calculate_invoice_hash()
            signature_encoded, signing_time = self._sign_invoice(invoice_hash)
            
            # Fill signature information
            self._fill_signed_properties(signing_time)
            signed_properties_hash = self._generate_signed_properties_hash()
            self._fill_ubl_extensions(
                invoice_hash_encoded,
                signature_encoded,
                signed_properties_hash
            )
            
            # Generate QR code and finalize
            self._finalize_invoice(signature_encoded)
            self._save_xml_file()
            
            return self.hash, self.qr_code
            
        except Exception as e:
            log_and_throw_error(
                "ZATCA XML Generation Error",
                _("Error generating ZATCA XML invoice: {0}").format(str(e)),
                frappe.get_traceback()
            )
    
    def _create_xml_tree(self):
        """Create the base XML tree from template."""
        template_file = (
            "simplified_invoice.xml" 
            if self.sales_invoice.get("InvoiceStatus") == INVOICE_TYPE_SIMPLIFIED 
            else "standard_invoice.xml"
        )
        
        template_path = Path(frappe.get_app_path("optima_zatca")) / "zatca/Samples/Standard" / template_file
        self.tree = etree.parse(str(template_path))
        self.root = self.tree.getroot()
    
    def _create_element(self, parent, tag: str, text: str = None, attrib: Dict = None) -> etree.Element:
        """
        Helper method to create XML elements.
        
        Args:
            parent: Parent element
            tag: Tag name with namespace
            text: Element text content
            attrib: Element attributes
            
        Returns:
            Created element
        """
        element = etree.SubElement(parent, tag)
        if text is not None:
            element.text = str(text)
        if attrib:
            for key, value in attrib.items():
                element.set(key, str(value))
        return element
    
    def _add_general_data(self):
        """Add general invoice data."""
        # Set IDs
        id_elements = self.root.findall(".//cbc:ID", namespaces=NAMESPACES)
        if len(id_elements) > 1:
            id_elements[1].text = self.sales_invoice.get("ID")
        
        # Set UUID
        self._set_element_text(".//cbc:UUID", self.sales_invoice.get("UUID"))
        
        # Set dates and times
        self._set_element_text(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueDate",
            self.sales_invoice.get("IssueDate")
        )
        self._set_element_text(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueTime",
            self.sales_invoice.get("IssueTime")
        )
        
        # Set invoice type
        invoice_type = self.root.find(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoiceTypeCode"
        )
        if invoice_type is not None:
            invoice_type.set("name", self.sales_invoice.get("InvoiceTypeCodeName"))
            invoice_type.text = self.sales_invoice.get("InvoiceTypeCode")
        
        # Set currency codes
        self._set_element_text(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}DocumentCurrencyCode",
            self.sales_invoice.get("DocumentCurrencyCode")
        )
        self._set_element_text(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxCurrencyCode",
            self.sales_invoice.get("TaxCurrencyCode")
        )
        
        # Add optional elements
        self._add_purchase_order_reference()
        self._add_billing_reference()
        self._add_invoice_note()
        self._add_document_references()
    
    def _add_purchase_order_reference(self):
        """Add purchase order reference if exists."""
        if not (self.sales_invoice.get("PurchaseOrderID") and 
                self.sales_invoice.get("PurchaseOrderIssueDate")):
            return
            
        tax_currency = self.root.find(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxCurrencyCode"
        )
        if tax_currency is None:
            return
            
        order_ref = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}OrderReference"
        )
        
        self._create_element(
            order_ref,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            self.sales_invoice.get("PurchaseOrderID")
        )
        self._create_element(
            order_ref,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueDate",
            self.sales_invoice.get("PurchaseOrderIssueDate")
        )
        
        order_ref.tail = "\n    "
        etree.indent(order_ref, space="    ", level=1)
        
        parent = tax_currency.getparent()
        parent.insert(parent.index(tax_currency) + 1, order_ref)
    
    def _add_billing_reference(self):
        """Add billing reference for credit/debit notes."""
        if self.sales_invoice.get("InvoiceSubStatus") not in [INVOICE_SUBTYPE_CREDIT, INVOICE_SUBTYPE_DEBIT]:
            return
            
        if not self.sales_invoice.get("ReturnAgainst"):
            return
            
        billing_ref = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}BillingReference"
        )
        invoice_doc_ref = self._create_element(
            billing_ref,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceDocumentReference"
        )
        self._create_element(
            invoice_doc_ref,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            self.sales_invoice.get("ReturnAgainst")
        )
        
        billing_ref.tail = "\n    "
        etree.indent(billing_ref, space="    ", level=1)
        
        # Insert after appropriate element
        tax_currency_elements = self.root.xpath(".//cbc:TaxCurrencyCode[last()]", namespaces=NAMESPACES)
        if tax_currency_elements:
            parent = tax_currency_elements[0].getparent()
            insert_position = parent.index(tax_currency_elements[0]) + 1
            
            # Adjust position if order reference exists
            if self.sales_invoice.get("PurchaseOrderID"):
                insert_position += 1
                
            parent.insert(insert_position, billing_ref)
    
    def _add_invoice_note(self):
        """Add invoice note if exists."""
        note_text = self.sales_invoice.get("Note")
        if not note_text or note_text == "No Remarks":
            return
            
        invoice_type = self.root.find(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoiceTypeCode"
        )
        if invoice_type is None:
            return
            
        invoice_note = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Note"
        )
        invoice_note.text = note_text
        invoice_note.tail = "\n    "
        
        parent = invoice_type.getparent()
        parent.insert(parent.index(invoice_type) + 1, invoice_note)
    
    def _add_document_references(self):
        """Add additional document references."""
        # Invoice counter
        counter_elem = self.root.find(
            ".//cac:AdditionalDocumentReference/cbc:UUID",
            namespaces=NAMESPACES
        )
        if counter_elem is not None:
            counter_elem.text = self.sales_invoice.get("InvoiceCounter")
        
        # Previous invoice hash
        pih_elements = self.root.findall(
            ".//cac:AdditionalDocumentReference/cac:Attachment/cbc:EmbeddedDocumentBinaryObject",
            namespaces=NAMESPACES
        )
        if pih_elements:
            pih_elements[0].text = self.sales_invoice.get("PIH")
    
    def _add_supplier_information(self):
        """Add supplier (seller) information."""
        company = self.sales_invoice.get("company", {})
        
        # Set supplier ID
        self._set_supplier_field(
            "cac:PartyIdentification/cbc:ID",
            company.get("ID"),
            {"schemeID": company.get("schemeID")}
        )
        
        # Set address information
        address_fields = {
            "cac:PostalAddress/cbc:StreetName": company.get("StreetName"),
            "cac:PostalAddress/cbc:BuildingNumber": company.get("BuildingNumber"),
            "cac:PostalAddress/cbc:CitySubdivisionName": company.get("CitySubdivisionName"),
            "cac:PostalAddress/cbc:CityName": company.get("CityName"),
            "cac:PostalAddress/cbc:PostalZone": company.get("PostalZone"),
            "cac:PostalAddress/cac:Country/cbc:IdentificationCode": company.get("IdentificationCode"),
        }
        
        for field_path, value in address_fields.items():
            self._set_supplier_field(field_path, value)
        
        # Add province if exists
        self._add_supplier_province(company)
        
        # Set tax information
        self._set_supplier_field(
            "cac:PartyTaxScheme/cbc:CompanyID",
            company.get("CompanyID")
        )
        
        # Set legal entity name
        self._set_supplier_field(
            "cac:PartyLegalEntity/cbc:RegistrationName",
            company.get("RegistrationName")
        )
    
    def _add_supplier_province(self, company: Dict):
        """Add supplier province if exists."""
        province = company.get("CountrySubentity")
        if not province:
            return
            
        postal_zone = self.root.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:PostalZone",
            namespaces=NAMESPACES
        )
        if postal_zone is None:
            return
            
        address_tag = postal_zone.getparent()
        province_elem = self._create_element(
            address_tag,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CountrySubentity",
            province
        )
        province_elem.tail = "\n                "
        address_tag.insert(address_tag.index(postal_zone) + 1, province_elem)
    
    def _add_customer_information(self):
        """Add customer (buyer) information based on invoice type."""
        if self.sales_invoice.get("InvoiceStatus") == INVOICE_TYPE_SIMPLIFIED:
            self._add_simplified_customer_info()
        else:
            self._add_standard_customer_info()
    
    def _add_simplified_customer_info(self):
        """Add customer information for simplified invoices."""
        customer = self.sales_invoice.get("customer", {})
        if not customer.get("ID"):
            return
            
        customer_party = self.root.find(
            ".//cac:AccountingCustomerParty/cac:Party",
            namespaces=NAMESPACES
        )
        if customer_party is None:
            return
            
        # Add party identification
        party_id = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyIdentification"
        )
        id_elem = self._create_element(
            party_id,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            customer.get("ID"),
            {"schemeID": customer.get("schemeID", "NAT")}
        )
        
        party_id.tail = "\n            "
        etree.indent(party_id, space="    ", level=3)
        
        # Insert before tax scheme
        tax_scheme = customer_party.find(".//cac:PartyTaxScheme", namespaces=NAMESPACES)
        if tax_scheme is not None:
            customer_party.insert(customer_party.index(tax_scheme), party_id)
        else:
            customer_party.append(party_id)
        
        # Add legal entity
        legal_entity = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyLegalEntity"
        )
        self._create_element(
            legal_entity,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RegistrationName",
            customer.get("RegistrationName")
        )
        
        legal_entity.tail = "\n        "
        etree.indent(legal_entity, space="    ", level=3)
        
        if tax_scheme is not None:
            customer_party.insert(customer_party.index(tax_scheme) + 1, legal_entity)
        else:
            customer_party.append(legal_entity)
    
    def _add_standard_customer_info(self):
        """Add customer information for standard invoices."""
        customer = self.sales_invoice.get("customer", {})
        
        # Set customer ID
        self._set_customer_field(
            "cac:PartyIdentification/cbc:ID",
            customer.get("ID"),
            {"schemeID": customer.get("schemeID")}
        )
        
        # Set address information
        address_fields = {
            "cac:PostalAddress/cbc:StreetName": customer.get("StreetName"),
            "cac:PostalAddress/cbc:BuildingNumber": customer.get("BuildingNumber"),
            "cac:PostalAddress/cbc:CitySubdivisionName": customer.get("CitySubdivisionName"),
            "cac:PostalAddress/cbc:CityName": customer.get("CityName"),
            "cac:PostalAddress/cbc:PostalZone": customer.get("PostalZone"),
            "cac:PostalAddress/cac:Country/cbc:IdentificationCode": customer.get("IdentificationCode"),
        }
        
        for field_path, value in address_fields.items():
            self._set_customer_field(field_path, value)
        
        # Add province if exists
        self._add_customer_province(customer)
        
        # Add tax scheme for Saudi customers
        if customer.get("IdentificationCode") == "SA":
            self._add_customer_tax_scheme(customer)
        
        # Set legal entity name
        self._set_customer_field(
            "cac:PartyLegalEntity/cbc:RegistrationName",
            customer.get("RegistrationName")
        )
    
    def _add_customer_province(self, customer: Dict):
        """Add customer province if exists."""
        province = customer.get("CountrySubentity")
        if not province:
            return
            
        postal_zone = self.root.find(
            ".//cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:PostalZone",
            namespaces=NAMESPACES
        )
        if postal_zone is None:
            return
            
        address_tag = postal_zone.getparent()
        province_elem = self._create_element(
            address_tag,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CountrySubentity",
            province
        )
        province_elem.tail = "\n                "
        address_tag.insert(address_tag.index(postal_zone) + 1, province_elem)
    
    def _add_customer_tax_scheme(self, customer: Dict):
        """Add tax scheme for Saudi customers."""
        party = self.root.find(
            ".//cac:AccountingCustomerParty/cac:Party",
            namespaces=NAMESPACES
        )
        if party is None:
            return
            
        postal_address = party.find(".//cac:PostalAddress", namespaces=NAMESPACES)
        if postal_address is None:
            return
            
        tax_scheme = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyTaxScheme"
        )
        
        self._create_element(
            tax_scheme,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CompanyID",
            customer.get("CompanyID")
        )
        
        scheme_elem = self._create_element(
            tax_scheme,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme"
        )
        
        self._create_element(
            scheme_elem,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            DEFAULT_TAX_SCHEME
        )
        
        tax_scheme.tail = "\n            "
        etree.indent(tax_scheme, space="    ", level=3)
        party.insert(party.index(postal_address) + 1, tax_scheme)
    
    def _add_items_data(self):
        """Add invoice items and related data."""
        # Add delivery date for standard normal invoices
        self._add_delivery_date()
        
        # Add payment means
        self._add_payment_means()
        
        # Add allowance charges
        self._add_allowance_charges()
        
        # Add tax totals
        self._add_tax_totals()
        
        # Add invoice lines
        self._add_invoice_lines()
        
        # Add legal monetary totals
        self._add_legal_monetary_totals()
    
    def _add_delivery_date(self):
        """Add delivery date for standard normal invoices."""
        if (self.sales_invoice.get("InvoiceStatus") != INVOICE_TYPE_STANDARD or 
            self.sales_invoice.get("InvoiceSubStatus") != INVOICE_SUBTYPE_NORMAL):
            return
            
        delivery_date = self.sales_invoice.get("ActualDeliveryDate")
        if not delivery_date:
            return
            
        delivery = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Delivery"
        )
        self._create_element(
            delivery,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ActualDeliveryDate",
            delivery_date
        )
        
        delivery.tail = "\n    "
        etree.indent(delivery, space="    ", level=1)
        
        customer = self.root.find(".//cac:AccountingCustomerParty", namespaces=NAMESPACES)
        if customer is not None:
            parent = customer.getparent()
            parent.insert(parent.index(customer) + 1, delivery)
    
    def _add_payment_means(self):
        """Add payment means for credit/debit notes."""
        if self.sales_invoice.get("InvoiceSubStatus") not in [INVOICE_SUBTYPE_CREDIT, INVOICE_SUBTYPE_DEBIT]:
            return
            
        payment_code = self.sales_invoice.get("PaymentMeansCode")
        if not payment_code:
            return
            
        payment_means = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PaymentMeans"
        )
        
        self._create_element(
            payment_means,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PaymentMeansCode",
            payment_code
        )
        
        # Add instruction note
        instruction_note = self.sales_invoice.get("InstructionNote")
        if instruction_note:
            self._create_element(
                payment_means,
                "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InstructionNote",
                instruction_note
            )
        
        # Add payment note if exists
        self._add_payment_note(payment_means)
        
        etree.indent(payment_means, space="    ", level=1)
        payment_means.tail = "\n    "
        
        customer = self.root.find(".//cac:AccountingCustomerParty", namespaces=NAMESPACES)
        if customer is not None:
            parent = customer.getparent()
            parent.insert(parent.index(customer) + 1, payment_means)
    
    def _add_payment_note(self, payment_means: etree.Element):
        """Add payment note to payment means."""
        payment_note_html = self.sales_invoice.get("PaymentNote")
        if not payment_note_html:
            return
            
        # Parse HTML content
        soup = BeautifulSoup(payment_note_html, "html.parser")
        formatted_text = []
        
        for tag in soup.find_all(["p", "ol", "ul", "li", "table", "tr", "th", "td"]):
            if tag.name == "p":
                formatted_text.append(tag.get_text())
            elif tag.name in ["ol", "ul"]:
                for li in tag.find_all("li"):
                    formatted_text.append(f"- {li.get_text()}")
            elif tag.name == "tr":
                cells = [cell.get_text() for cell in tag.find_all(["th", "td"])]
                formatted_text.append(" | ".join(cells))
        
        financial_account = self._create_element(
            payment_means,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PayeeFinancialAccount"
        )
        
        self._create_element(
            financial_account,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PaymentNote",
            "\n".join(formatted_text)
        )
    
    def _add_allowance_charges(self):
        """Add document level allowance charges."""
        customer = self.root.find(".//cac:AccountingCustomerParty", namespaces=NAMESPACES)
        if customer is None:
            return
            
        parent = customer.getparent()
        insert_position = parent.index(customer) + 1
        
        # Adjust position for existing elements
        if self.sales_invoice.get("PaymentMeansCode"):
            insert_position += 1
        if self.sales_invoice.get("ActualDeliveryDate"):
            insert_position += 1
        
        for charge in self.sales_invoice.get("TaxSubtotal", []):
            charge_amount = flt(charge.get("AllowanceChargeAmount", 0.00), 2)
            if charge_amount <= 0:
                continue
                
            allowance_elem = self._create_allowance_charge_element(charge)
            allowance_elem.tail = "\n    "
            etree.indent(allowance_elem, space="    ", level=1)
            parent.insert(insert_position, allowance_elem)
            insert_position += 1
    
    def _create_allowance_charge_element(self, charge: Dict) -> etree.Element:
        """Create an allowance charge element."""
        allowance = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AllowanceCharge"
        )
        
        self._create_element(
            allowance,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ChargeIndicator",
            charge.get("ChargeIndicator")
        )
        
        self._create_element(
            allowance,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}AllowanceChargeReason",
            charge.get("AllowanceChargeReason")
        )
        
        self._create_element(
            allowance,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Amount",
            str(flt(charge.get("AllowanceChargeAmount"), 2)),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
        
        # Add tax category
        tax_category = self._create_element(
            allowance,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxCategory"
        )
        
        self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            charge.get("TaxCategory"),
            {
                "schemeAgencyID": "6",
                "schemeID": charge.get("TaxCategorySchemeID")
            }
        )
        
        self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent",
            charge.get("Percent")
        )
        
        tax_scheme = self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme"
        )
        
        self._create_element(
            tax_scheme,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            DEFAULT_TAX_SCHEME,
            {
                "schemeAgencyID": "6",
                "schemeID": "UN/ECE 5153"
            }
        )
        
        return allowance
    
    def _add_tax_totals(self):
        """Add tax total elements."""
        # Set main tax amount
        tax_amount_elem = self.root.find(".//cac:TaxTotal/cbc:TaxAmount", namespaces=NAMESPACES)
        if tax_amount_elem is not None:
            tax_amount_elem.text = self.sales_invoice.get("TaxTotalTaxAmount")
            tax_amount_elem.set("currencyID", self.sales_invoice.get("company", {}).get("DefaultCurrency"))
        
        # Add tax subtotals
        self._insert_tax_subtotals()
    
    def _insert_tax_subtotals(self):
        """Insert tax subtotal elements."""
        last_tax_total = self.root.xpath(".//cac:TaxTotal[last()]", namespaces=NAMESPACES)
        if not last_tax_total:
            return
            
        parent = last_tax_total[0].getparent()
        insert_position = parent.index(last_tax_total[0]) + 1
        
        # Create main tax total element
        tax_total = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal"
        )
        
        self._create_element(
            tax_total,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount",
            self.sales_invoice.get("TaxAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
        
        # Add subtotals
        for subtotal_data in self.sales_invoice.get("TaxSubtotal", []):
            subtotal = self._create_tax_subtotal_element(subtotal_data)
            tax_total.append(subtotal)
        
        tax_total.tail = "\n    "
        etree.indent(tax_total, space="    ", level=1)
        parent.insert(insert_position, tax_total)
    
    def _create_tax_subtotal_element(self, subtotal_data: Dict) -> etree.Element:
        """Create a tax subtotal element."""
        subtotal = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxSubtotal"
        )
        
        self._create_element(
            subtotal,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxableAmount",
            str(flt(subtotal_data.get("TaxableAmount"), 2)),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
        
        self._create_element(
            subtotal,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount",
            subtotal_data.get("TaxAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
        
        # Add tax category
        tax_category = self._create_element(
            subtotal,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxCategory"
        )
        
        self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            subtotal_data.get("TaxCategory"),
            {
                "schemeAgencyID": "6",
                "schemeID": subtotal_data.get("TaxCategorySchemeID")
            }
        )
        
        self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent",
            subtotal_data.get("Percent")
        )
        
        # Add exemption reason if exists
        if subtotal_data.get("TaxExemptionReasonCode"):
            self._create_element(
                tax_category,
                "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxExemptionReasonCode",
                subtotal_data.get("TaxExemptionReasonCode")
            )
            
            self._create_element(
                tax_category,
                "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxExemptionReason",
                subtotal_data.get("TaxExemptionReason")
            )
        
        # Add tax scheme
        tax_scheme = self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme"
        )
        
        self._create_element(
            tax_scheme,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            subtotal_data.get("TaxSchemeID"),
            {
                "schemeAgencyID": subtotal_data.get("schemeAgencyID"),
                "schemeID": "UN/ECE 5153"
            }
        )
        
        return subtotal
    
    def _add_invoice_lines(self):
        """Add invoice line items."""
        try:
            monetary_total = self.root.xpath(".//cac:LegalMonetaryTotal[last()]", namespaces=NAMESPACES)
            if not monetary_total:
                return
                
            parent = monetary_total[0].getparent()
            items = self.sales_invoice.get("items", [])
            
            for idx, item in enumerate(items, 1):
                if item.get("is_prepayment"):
                    invoice_line = self._create_prepayment_line(item)
                else:
                    invoice_line = self._create_standard_line(item)
                
                invoice_line.tail = "\n    "
                etree.indent(invoice_line, space="    ", level=1)
                monetary_total[0].tail = "\n    "
                
                parent.insert(
                    parent.index(monetary_total[0]) + idx,
                    invoice_line
                )
                
        except Exception as e:
            frappe.log_error(f"Error adding invoice lines: {str(e)}", "ZATCA Invoice Lines")
            raise frappe.ValidationError(_("Error in Invoice Line: {0}").format(str(e)))
    
    def _create_prepayment_line(self, item: Dict) -> etree.Element:
        """Create a prepayment invoice line."""
        invoice_line = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceLine"
        )
        
        # Basic line information
        self._add_basic_line_info(invoice_line, item)
        
        # Document reference for prepayment
        doc_ref = self._create_element(
            invoice_line,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}DocumentReference"
        )
        
        self._create_element(
            doc_ref,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            item.get("PrepaymentID")
        )
        
        self._create_element(
            doc_ref,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}UUID",
            item.get("PrepaymentUUID")
        )
        
        self._create_element(
            doc_ref,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueDate",
            item.get("PrepaymentIssueDate")
        )
        
        self._create_element(
            doc_ref,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueTime",
            item.get("PrepaymentIssueTime")
        )
        
        self._create_element(
            doc_ref,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}DocumentTypeCode",
            item.get("PrepaymentTypeCode")
        )
        
        # Tax information
        self._add_prepayment_tax_info(invoice_line, item)
        
        # Item details
        self._add_item_details(invoice_line, item)
        
        # Price information
        self._add_price_info(invoice_line, item)
        
        return invoice_line
    
    def _create_standard_line(self, item: Dict) -> etree.Element:
        """Create a standard invoice line."""
        invoice_line = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceLine"
        )
        
        # Basic line information
        self._add_basic_line_info(invoice_line, item)
        
        # Tax information
        self._add_standard_tax_info(invoice_line, item)
        
        # Item details
        self._add_item_details(invoice_line, item)
        
        # Price information with allowances
        self._add_price_info_with_allowances(invoice_line, item)
        
        return invoice_line
    
    def _add_basic_line_info(self, invoice_line: etree.Element, item: Dict):
        """Add basic line information."""
        self._create_element(
            invoice_line,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            item.get("ID")
        )
        
        self._create_element(
            invoice_line,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoicedQuantity",
            item.get("InvoicedQuantity"),
            {"unitCode": DEFAULT_UNIT_CODE}
        )
        
        self._create_element(
            invoice_line,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}LineExtensionAmount",
            item.get("LineExtensionAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
    
    def _add_prepayment_tax_info(self, invoice_line: etree.Element, item: Dict):
        """Add tax information for prepayment lines."""
        tax_total = self._create_element(
            invoice_line,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal"
        )
        
        self._create_element(
            tax_total,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount",
            item.get("TaxTotalAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
        
        self._create_element(
            tax_total,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RoundingAmount",
            item.get("RoundingAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
        
        # Tax subtotal
        tax_subtotal = self._create_element(
            tax_total,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxSubtotal"
        )
        
        self._create_element(
            tax_subtotal,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxableAmount",
            item.get("TaxSubtotalTaxableAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
        
        self._create_element(
            tax_subtotal,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount",
            item.get("TaxSubtotalTaxAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
        
        # Tax category
        tax_category = self._create_element(
            tax_subtotal,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxCategory"
        )
        
        self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            item.get("TaxCategory")
        )
        
        self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent",
            item.get("Percent")
        )
        
        tax_scheme = self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme"
        )
        
        self._create_element(
            tax_scheme,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            item.get("TaxCategoryTaxSchemeID")
        )
    
    def _add_standard_tax_info(self, invoice_line: etree.Element, item: Dict):
        """Add tax information for standard lines."""
        tax_total = self._create_element(
            invoice_line,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal"
        )
        
        self._create_element(
            tax_total,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount",
            item.get("TaxAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
        
        self._create_element(
            tax_total,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RoundingAmount",
            item.get("RoundingAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
    
    def _add_item_details(self, invoice_line: etree.Element, item: Dict):
        """Add item details."""
        item_elem = self._create_element(
            invoice_line,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Item"
        )
        
        self._create_element(
            item_elem,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name",
            item.get("Name")
        )
        
        # Tax category
        tax_category = self._create_element(
            item_elem,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}ClassifiedTaxCategory"
        )
        
        self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            item.get("TaxCategory"),
            {"schemeID": "UNCL5305"} if not item.get("is_prepayment") else None
        )
        
        self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent",
            item.get("Percent")
        )
        
        tax_scheme = self._create_element(
            tax_category,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme"
        )
        
        self._create_element(
            tax_scheme,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID",
            item.get("TaxScheme", DEFAULT_TAX_SCHEME)
        )
    
    def _add_price_info(self, invoice_line: etree.Element, item: Dict):
        """Add price information."""
        price = self._create_element(
            invoice_line,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Price"
        )
        
        self._create_element(
            price,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PriceAmount",
            item.get("PriceAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
    
    def _add_price_info_with_allowances(self, invoice_line: etree.Element, item: Dict):
        """Add price information with allowances."""
        price = self._create_element(
            invoice_line,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Price"
        )
        
        self._create_element(
            price,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PriceAmount",
            item.get("PriceAmount"),
            {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
        )
        
        self._create_element(
            price,
            "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}BaseQuantity",
            "1",
            {"unitCode": DEFAULT_UNIT_CODE}
        )
        
        # Add allowance/charge if exists
        if item.get("Amount"):
            allowance = self._create_element(
                price,
                "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AllowanceCharge"
            )
            
            self._create_element(
                allowance,
                "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ChargeIndicator",
                item.get("ChargeIndicator")
            )
            
            self._create_element(
                allowance,
                "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}AllowanceChargeReason",
                "discount"
            )
            
            self._create_element(
                allowance,
                "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Amount",
                item.get("Amount"),
                {"currencyID": self.sales_invoice.get("DocumentCurrencyCode")}
            )
    
    def _add_legal_monetary_totals(self):
        """Add legal monetary total amounts."""
        currency = self.sales_invoice.get("DocumentCurrencyCode")
        
        # Set monetary amounts
        monetary_fields = {
            ".//cac:LegalMonetaryTotal/cbc:LineExtensionAmount": "LineExtensionAmount",
            ".//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount": "TaxExclusiveAmount",
            ".//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount": "TaxInclusiveAmount",
            ".//cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount": "AllowanceTotalAmount",
            ".//cac:LegalMonetaryTotal/cbc:PrepaidAmount": "PrepaidAmount",
            ".//cac:LegalMonetaryTotal/cbc:PayableAmount": "PayableAmount",
        }
        
        for xpath, field_name in monetary_fields.items():
            elem = self.root.find(xpath, namespaces=NAMESPACES)
            if elem is not None:
                elem.text = self.sales_invoice.get(field_name)
                elem.set("currencyID", currency)
    
    def _calculate_invoice_hash(self) -> Tuple[str, str]:
        """Calculate invoice hash according to ZATCA specifications."""
        # Create a copy of the tree for hash calculation
        tree_copy = copy.deepcopy(self.tree)
        root = tree_copy.getroot()
        
        # Remove required elements for hash calculation
        self._remove_element_for_hash(root, './/ext:UBLExtensions')
        self._remove_qr_reference(root)
        self._remove_element_for_hash(root, './/cac:Signature')
        
        # Canonicalize
        canonicalized_xml = etree.tostring(root, encoding=ENCODING_UTF8)
        
        # Format with minidom
        xml_doc = mini.parseString(canonicalized_xml)
        formatted_xml = self._format_xml_for_hash(xml_doc)
        
        # Calculate hash
        invoice_hash = hashlib.sha256(formatted_xml.encode()).hexdigest()
        hash_bytes = bytearray.fromhex(invoice_hash)
        hash_encoded = base64.b64encode(hash_bytes).decode()
        
        return hash_encoded, invoice_hash
    
    def _remove_element_for_hash(self, root: etree.Element, xpath: str):
        """Remove element for hash calculation."""
        element = root.find(xpath, namespaces=NAMESPACES)
        if element is not None:
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
    
    def _remove_qr_reference(self, root: etree.Element):
        """Remove QR code reference for hash calculation."""
        refs = root.findall('.//cac:AdditionalDocumentReference', namespaces=NAMESPACES)
        for ref in refs:
            id_elem = ref.find('.//cbc:ID', namespaces=NAMESPACES)
            if id_elem is not None and id_elem.text == "QR":
                parent = ref.getparent()
                if parent is not None:
                    parent.remove(ref)
    
    def _format_xml_for_hash(self, xml_doc: mini.Document) -> str:
        """Format XML for hash calculation."""
        # Add line breaks before ProfileID
        profile_id = xml_doc.getElementsByTagName("cbc:ProfileID")
        if profile_id:
            parent = profile_id[0].parentNode
            parent.insertBefore(xml_doc.createTextNode("\n    "), profile_id[0])
            parent.insertBefore(xml_doc.createTextNode("\n    "), profile_id[0])
        
        # Handle self-closing tags
        payment_means_code = xml_doc.getElementsByTagName("cbc:PaymentMeansCode")
        if payment_means_code:
            payment_means_code[0].appendChild(xml_doc.createTextNode(""))
        
        return xml_doc.childNodes[0].toprettyxml(indent="", newl="")
    
    def _sign_invoice(self, invoice_hash: str) -> Tuple[str, str]:
        """Sign the invoice hash."""
        return sign_invoice(self.sales_invoice.get("private_key"), invoice_hash)
    
    def _fill_signed_properties(self, signing_time: str):
        """Fill signed properties in the XML."""
        # Certificate digest
        self._set_element_text(
            ".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures"
            "/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties"
            "/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningCertificate"
            "/xades:Cert/xades:CertDigest/ds:DigestValue",
            self.sales_invoice.get("DigestValue")
        )
        
        # Signing time
        self._set_element_text(
            ".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures"
            "/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties"
            "/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningTime",
            signing_time
        )
        
        # Issuer name
        self._set_element_text(
            ".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures"
            "/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties"
            "/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningCertificate"
            "/xades:Cert/xades:IssuerSerial/ds:X509IssuerName",
            self.sales_invoice.get("X509IssuerName")
        )
        
        # Serial number
        self._set_element_text(
            ".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures"
            "/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties"
            "/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningCertificate"
            "/xades:Cert/xades:IssuerSerial/ds:X509SerialNumber",
            self.sales_invoice.get("X509SerialNumber")
        )
    
    def _generate_signed_properties_hash(self) -> str:
        """Generate hash for signed properties."""
        tree_copy = copy.deepcopy(self.tree)
        root = tree_copy.getroot()
        
        # Extract values
        signing_time = self._get_element_text(root, ".//xades:SigningTime")
        digest_value = self._get_element_text(root, ".//xades:CertDigest/ds:DigestValue")
        issuer_name = self._get_element_text(root, ".//ds:X509IssuerName")
        serial_number = self._get_element_text(root, ".//ds:X509SerialNumber")
        
        # Load template
        template_path = Path(frappe.get_app_path("optima_zatca")) / "zatca/Samples/Signed_properities_tag/Signed_properities_tag_hash.xml"
        hash_doc = mini.parse(str(template_path))
        
        # Fill template
        self._set_minidom_element_text(hash_doc, "xades:SigningTime", signing_time)
        self._set_minidom_element_text(hash_doc, "ds:DigestValue", digest_value)
        self._set_minidom_element_text(hash_doc, "ds:X509IssuerName", issuer_name)
        self._set_minidom_element_text(hash_doc, "ds:X509SerialNumber", str(serial_number))
        
        # Generate hash
        xml_string = hash_doc.childNodes[0].toprettyxml(indent="", newl="")
        hashed_value = hashlib.sha256(xml_string.encode()).hexdigest()
        return base64.b64encode(hashed_value.encode()).decode()
    
    def _fill_ubl_extensions(self, invoice_hash: str, signature: str, signed_properties_hash: str):
        """Fill UBL extensions with signature data."""
        # Signature value
        self._set_element_text(
            ".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures"
            "/sac:SignatureInformation/ds:Signature/ds:SignatureValue",
            signature
        )
        
        # Certificate
        self._set_element_text(
            ".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures"
            "/sac:SignatureInformation/ds:Signature/ds:KeyInfo/ds:X509Data/ds:X509Certificate",
            self.sales_invoice.get("Certificate")
        )
        
        # Signed properties hash
        self._set_element_text(
            "./ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures"
            "/sac:SignatureInformation/ds:Signature/ds:SignedInfo"
            "/ds:Reference[@URI='#xadesSignedProperties']/ds:DigestValue",
            signed_properties_hash
        )
        
        # Invoice hash
        self._set_element_text(
            ".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures"
            "/sac:SignatureInformation/ds:Signature/ds:SignedInfo"
            "/ds:Reference[@Id='invoiceSignedData']/ds:DigestValue",
            invoice_hash
        )
        
        self.hash = invoice_hash
    
    def _finalize_invoice(self, signature: str):
        """Finalize invoice with QR code."""
        self.qr_code = generate_qr_code(
            self.sales_invoice.get("company", {}).get("RegistrationName"),
            self.sales_invoice.get("company", {}).get("CompanyID"),
            self.sales_invoice.get("IssueDate"),
            self.sales_invoice.get("IssueTime"),
            invoice_total=self.sales_invoice.get("TaxInclusiveAmount"),
            vat_total=self.sales_invoice.get("TaxAmount"),
            invoice_hash=self.hash,
            invoice_signature=signature,
            public_key_str=self.sales_invoice.get("public_key"),
            signature_ecdsa=self.sales_invoice.get("SignatureInformation")
        )
        
        # Set QR code
        qr_refs = self.root.findall(".//cac:AdditionalDocumentReference", namespaces=NAMESPACES)
        for ref in qr_refs:
            id_elem = ref.find(".//cbc:ID", namespaces=NAMESPACES)
            if id_elem is not None and id_elem.text == "QR":
                qr_elem = ref.find(".//cac:Attachment/cbc:EmbeddedDocumentBinaryObject", namespaces=NAMESPACES)
                if qr_elem is not None:
                    qr_elem.text = self.qr_code
    
    def _save_xml_file(self):
        """Save the XML file to disk."""
        folder_path = Path(get_bench_relative_path(frappe.local.site)) / "public/files/invoices"
        folder_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{self.sales_invoice.get('ID')}_uuid_{self.sales_invoice.get('UUID')}.xml"
        file_path = folder_path / filename
        
        self.tree.write(str(file_path), encoding=ENCODING_UTF8, xml_declaration=True, pretty_print=True)
    
    # Helper methods
    def _set_element_text(self, xpath: str, text: str, attrib: Dict = None):
        """Set text content of an element."""
        elem = self.root.find(xpath, namespaces=NAMESPACES)
        if elem is not None:
            elem.text = str(text) if text is not None else None
            if attrib:
                for key, value in attrib.items():
                    elem.set(key, str(value))
    
    def _get_element_text(self, root: etree.Element, xpath: str) -> Optional[str]:
        """Get text content of an element."""
        elem = root.find(xpath, namespaces=NAMESPACES)
        return elem.text if elem is not None else None
    
    def _set_minidom_element_text(self, doc: mini.Document, tag: str, text: str):
        """Set text content for minidom element."""
        elements = doc.getElementsByTagName(tag)
        if elements:
            elements[0].appendChild(doc.createTextNode(str(text)))
    
    def _set_supplier_field(self, field_path: str, value: str, attrib: Dict = None):
        """Set supplier field value."""
        xpath = f".//cac:AccountingSupplierParty/cac:Party/{field_path}"
        self._set_element_text(xpath, value, attrib)
    
    def _set_customer_field(self, field_path: str, value: str, attrib: Dict = None):
        """Set customer field value."""
        xpath = f".//cac:AccountingCustomerParty/cac:Party/{field_path}"
        self._set_element_text(xpath, value, attrib)


def get_qrcode_from_xml(invoice_xml: str) -> Optional[str]:
    """
    Extract QR code from ZATCA XML invoice.
    
    Args:
        invoice_xml: XML content as string
        
    Returns:
        QR code string or None if not found
    """
    try:
        # Remove XML declaration
        xml_content = re.sub(r'<\?xml.*\?>', '', invoice_xml)
        tree = etree.fromstring(xml_content)
        
        qr_element = tree.find(
            ".//cac:AdditionalDocumentReference[cbc:ID='QR']/cac:Attachment/cbc:EmbeddedDocumentBinaryObject",
            NAMESPACES
        )
        
        return qr_element.text if qr_element is not None else None
        
    except Exception as e:
        log_and_throw_error(operation="Get QR Code from XML", document_name="Unknown", exception=e)
        return None


# Backwards compatibility
ZatcaXml = ZatcaXmlGenerator