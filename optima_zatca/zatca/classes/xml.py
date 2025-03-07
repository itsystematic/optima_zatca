import os
import re
import copy
import time
import base64
import frappe
import hashlib
from lxml import etree
from frappe import _ , _dict
from optima_zatca.zatca.utils import generate_qr_code
from bs4 import BeautifulSoup
import xml.dom.minidom as mini
from frappe.utils import  get_bench_relative_path , flt
from optima_zatca.zatca.utils import sign_invoice



NameSpace = {
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "sig": "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2",
    "sac": "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2",
    "sbc": "urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2",
    "xades": "http://uri.etsi.org/01903/v1.3.2#",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}

class ZatcaXml :
    
    def __init__(self, sales_invoice:_dict = {} ):
        self.sales_invoice = sales_invoice
        self.create_zatca_xml()
        
        
    def create_zatca_xml(self) :
        
        self.create_xml_tree()
        self.add_general_data()
        self.add_supplier_information()
        self.add_customer_information()
        # self.add_allowance_charges()
        # self.add_legal_mandatory_data()
        self.add_items_data()
        
        invoice_hash_encoded, inovice_hash = calculate_invoice_hash(copy.deepcopy(self.tree))

        signature_encoded, signing_time = sign_invoice( self.sales_invoice.get("private_key") , inovice_hash )

        self.__fill_signed_properities_tag(signing_time)
        
        signed_properities_hash_encoded = generate_signed_properities_tag_hash(copy.deepcopy(self.tree) )
        
        self.__fill_ubl_ext(
            invoice_hash_encoded=invoice_hash_encoded,
            signature_encoded=signature_encoded,
            signed_properities_hash_encoded=signed_properities_hash_encoded,
        )

        self.__final_invoice(signature_encoded)

        create_xml_file(self.tree , self.sales_invoice.get("ID") , self.sales_invoice.get("UUID"))
        
    def create_xml_tree(self) :

        place = "simplified_invoice.xml" if self.sales_invoice.get("InvoiceStatus") == "Simplified" else "standard_invoice.xml"
        self.tree = etree.parse("{0}/zatca/Samples/Standard/{1}".format(
            frappe.get_app_path("optima_zatca") ,
            place
        ))
        self.root = self.tree.getroot()
        
    def add_general_data(self) :
        
        index_count = 1
        
        id = self.root.findall(
            ".//cbc:ID",
            namespaces={
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
            },
        )
        
        id[1].text = self.sales_invoice.get("ID")
        
        uuid_element = self.root.find(
            ".//cbc:UUID",
            namespaces={
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
            },
        )

        uuid_element.text = self.sales_invoice.get("UUID")

        # fill data in <cbc:IssueDate></cbc:IssueDate>
        issue_date = self.root.find("{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueDate")
        issue_date.text = self.sales_invoice.get("IssueDate")
        
        # fill data in <cbc:IssueTime></cbc:IssueTime> + removing fractures in seconds
        issue_time = self.root.find("{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueTime")
        issue_time.text  = self.sales_invoice.get("IssueTime")

        # fill invoice type (code and name)
        
        invoice_type = self.root.find("{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoiceTypeCode")
        invoice_type.set("name", self.sales_invoice.get("InvoiceTypeCodeName"))
        invoice_type.text = self.sales_invoice.get("InvoiceTypeCode")

        # fill data in <cbc:DocumentCurrencyCode></cbc:DocumentCurrencyCode> && <cbc:TaxCurrencyCode></cbc:TaxCurrencyCode>
        
        document_currency_code = self.root.find("{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}DocumentCurrencyCode")
        document_currency_code.text = self.sales_invoice.get("DocumentCurrencyCode")

        tax_currency_code = self.root.find("{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxCurrencyCode")
        tax_currency_code.text = self.sales_invoice.get("TaxCurrencyCode")
        # tax_currency_code.text = self.sales_invoice.get("TaxCurrencyCode") or self.sales_invoice.get("DocumentCurrencyCode")


        if self.sales_invoice.get("PurchaseOrderID") and self.sales_invoice.get("PurchaseOrderIssueDate") :
            order_ref = etree.Element("{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}OrderReference")
            order_id = etree.SubElement(order_ref,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
            order_date = etree.SubElement(order_ref,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueDate")
            
            order_id.text = self.sales_invoice.get("PurchaseOrderID")
            order_date.text = self.sales_invoice.get("PurchaseOrderIssueDate")
            order_ref.tail = "\n    "
            etree.indent(order_ref, space="    ", level=1)
                
            tax_currency_code.getparent().insert(tax_currency_code.getparent().index(tax_currency_code) + index_count, order_ref )
            index_count += 1

        if self.sales_invoice.get("InvoiceSubStatus") in ["credit" , "debit"] :
            
            billing_ref = etree.Element("{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}BillingReference")
            invoice_doc_Ref = etree.SubElement(billing_ref , "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceDocumentReference")
            invoice_doc_id = etree.SubElement(invoice_doc_Ref , "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID" )
            invoice_doc_id.text = self.sales_invoice.get("ReturnAgainst")
            billing_ref.tail = "\n    "
            etree.indent(billing_ref, space="    ", level=1)

            # Get the index of the location of insertion
            tax_Currency_code_index = self.root.xpath( ".//cbc:TaxCurrencyCode[last()]", namespaces=NameSpace )
            # insert the new tag
            tax_Currency_code_index[0].getparent().insert(
                tax_Currency_code_index[0].getparent().index(tax_Currency_code_index[0])
                + index_count,
                billing_ref,
            )
            index_count += 1

        if self.sales_invoice.get("Note") and self.sales_invoice.get("Note") != "No Remarks" :
            invoice_note = etree.Element("{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Note")
            invoice_note.text = self.sales_invoice.get("Note")
            invoice_note.tail = "\n    "
            invoice_type.getparent().insert(invoice_type.getparent().index(invoice_type) + 1, invoice_note )


        # fill data <cac:AdditionalDocumentReference> <cbc:UUID></cbc:UUID> </cac:AdditionalDocumentReference> Data for number of invoices sent
        invoice_counter = self.root.find(
            ".//cac:AdditionalDocumentReference/cbc:UUID",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )

        invoice_counter.text = self.sales_invoice.get("InvoiceCounter")

        # fill data <cac:AdditionalDocumentReference> <cbc:UUID></cbc:UUID> </cac:AdditionalDocumentReference> Data for the last invoice hash
        prev_invoice_hash = self.root.findall(
            ".//cac:AdditionalDocumentReference/cac:Attachment/cbc:EmbeddedDocumentBinaryObject",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )[0]

        # prev_invoice_hash.text = self.sales_invoice.get("company").get("PIH")
        prev_invoice_hash.text = self.sales_invoice.get("PIH")
        
        
    def add_supplier_information(self) :
        
        seller_crn = self.root.find(".//cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )
        
        seller_crn.text = self.sales_invoice.get("company").get("ID")
        seller_crn.set("schemeID", self.sales_invoice.get("company").get("schemeID"))

        # Fill Seller Street Name From Comapny Address address_line1
        seller_street_name = self.root.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:StreetName",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )
        
        seller_street_name.text = self.sales_invoice.get("company").get("StreetName")

        # Fill Seller Building Number From Comapny Address building_no
        seller_building_number = self.root.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:BuildingNumber",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )
        seller_building_number.text = self.sales_invoice.get("company").get("BuildingNumber")

        # Plot Identification is optional
        # seller_plot_identification = self.root.find(".//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:PlotIdentification", namespaces={'cac':'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2', 'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'})
        # if seller_plot_identification is not None:
        #     seller_plot_identification.text = frappe.get_doc("Address", self.sales_invoice_data.get("company_address")).plot_id_no

        # Fill Seller Distrct From Comapny Address district , Note : if district is null put the city name instead
        seller_city_subdivision = self.root.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:CitySubdivisionName",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )

        seller_city_subdivision.text = self.sales_invoice.get("company").get("CitySubdivisionName")

        # Fill Seller City Name Or Registed Address
        seller_city_name = self.root.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:CityName",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )

        seller_city_name.text = self.sales_invoice.get("company").get("CityName")

        # Seller Postal Code , I think its 5 digit number.
        seller_postal_zone = self.root.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:PostalZone",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )
        seller_postal_zone.text = self.sales_invoice.get("company").get("PostalZone")
        
        if self.sales_invoice.get("company").get("CountrySubentity") not in [ "", None] :
            
            seller_address_tag = self.root.find(
                ".//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress",
                namespaces=NameSpace,
            )
            seller_province = etree.SubElement(seller_address_tag, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CountrySubentity")

            seller_province.text = self.sales_invoice.get("company").get("CountrySubentity")
            # handling spaces for hashing
            seller_province.tail = "\n                "

            # Insert the element after postal code
            seller_address_tag.insert(seller_address_tag.index(seller_postal_zone) + 1, seller_province )

        # Fill The Data for the Seller Country Code , must be uppercase
        seller_country_code = self.root.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )
        seller_country_code.text = self.sales_invoice.get("company").get("IdentificationCode")

        # Seller Vat Number (Tax id) and if Group Tax id if exists (tin) , Note TIN Exists if 11th digit of tax id  is not 1.

        seller_vat = self.root.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )
        seller_vat.text = self.sales_invoice.get("company").get("CompanyID")

        # Fill Seller name data (Comapny Name)
        seller_name = self.root.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            },
        )
        seller_name.text = self.sales_invoice.get("company").get("RegistrationName")


    def add_customer_information(self):
        """
        Add customer information
        """
        if self.sales_invoice.get("InvoiceStatus") ==  "Simplified" :
            
            if self.sales_invoice.get("customer").get("ID") not in [ "", None] :
                
                # find parent tag to insert customer name and nat
                customer_party = self.root.find(".//cac:AccountingCustomerParty/cac:Party", namespaces=NameSpace )
                # find index to insert nat tag
                customer_tax_scheme = self.root.find(".//cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme",namespaces=NameSpace)
                # create the identifier element
                party_identification = etree.SubElement(customer_party,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyIdentification")
                buyer_nat = etree.SubElement(party_identification, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID" )
                buyer_nat.text = self.sales_invoice.get("customer").get("ID")
                buyer_nat.set("schemeID", self.sales_invoice.get("customer").get("schemeID" , "NAT"))
                party_identification.tail = "\n            "
                etree.indent(party_identification, space="    ", level=3)

                customer_party.insert(customer_party.index(customer_tax_scheme), party_identification)
                party_legal_entity = etree.SubElement( customer_party, "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyLegalEntity")
                buyer_name = etree.SubElement(party_legal_entity,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RegistrationName" )
                buyer_name.text = self.sales_invoice.get("customer").get("RegistrationName")

                party_legal_entity.tail = "\n        "

                etree.indent(party_legal_entity, space="    ", level=3)

                customer_party.insert( customer_party.index(customer_tax_scheme) + 1, party_legal_entity)
        else:
            # fill data in <cbc:ID></cbc:ID> , buyer id or nat or crn
            buyer_crn = self.root.find(".//cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID",
                namespaces={
                    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                },
            )
            buyer_crn.text = self.sales_invoice.get("customer").get("ID")
            buyer_crn.set("schemeID", self.sales_invoice.get("customer").get("schemeID"))

            # Fill buyer Street name From Buyer/customer address
            buyer_street_name = self.root.find(
                ".//cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:StreetName",
                namespaces={
                    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                },
            )
            buyer_street_name.text = self.sales_invoice.get("customer").get("StreetName")

            # fill Buyer Building number
            buyer_building_number = self.root.find(
                ".//cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:BuildingNumber",
                namespaces={
                    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                },
            )
            buyer_building_number.text = self.sales_invoice.get("customer").get("BuildingNumber")
            
            buyer_city_subdivision = self.root.find(
                ".//cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:CitySubdivisionName",
                namespaces={
                    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                },
            )

            buyer_city_subdivision.text = self.sales_invoice.get("customer").get("CitySubdivisionName")

            # Buyer City Name
            buyer_city_name = self.root.find(
                ".//cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:CityName",
                namespaces={
                    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                },
            )
            
            buyer_city_name.text = self.sales_invoice.get("customer").get("CityName")

            # Buyer Postal Code
            buyer_postal_zone = self.root.find(
                ".//cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cbc:PostalZone",
                namespaces={
                    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                },
            )
            buyer_postal_zone.text = self.sales_invoice.get("customer").get("PostalZone")
            
            if self.sales_invoice.get("customer").get("CountrySubentity") :
                buyer_address_tag = self.root.find(".//cac:AccountingCustomerParty/cac:Party/cac:PostalAddress", namespaces=NameSpace,)
                buyer_province = etree.SubElement(  buyer_address_tag,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CountrySubentity")
                buyer_province.text = self.sales_invoice.get("customer").get("CountrySubentity")
                buyer_province.tail = "\n                "

                # Insert the element after buyer postal code
                buyer_address_tag.insert(buyer_address_tag.index(buyer_postal_zone) + 1, buyer_province )

            # Buyer Country Code In Uppercase
            buyer_country_code = self.root.find(
                ".//cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode",
                namespaces={
                    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                },
            )
            buyer_country_code.text = self.sales_invoice.get("customer").get("IdentificationCode")


            if self.sales_invoice.get("customer").get("IdentificationCode") == "SA":
                party = self.root.find('.//cac:AccountingCustomerParty/cac:Party', namespaces=NameSpace)
                postal_address = self.root.find(".//cac:AccountingCustomerParty/cac:Party/cac:PostalAddress", namespaces=NameSpace)

                party_tax_scheme = etree.SubElement(party, "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyTaxScheme")
                company_id = etree.SubElement(party_tax_scheme, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CompanyID")
                company_id.text = self.sales_invoice.get("customer").get("CompanyID")
                tax_scheme = etree.SubElement(party_tax_scheme, "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme")
                tax_scheme_id = etree.SubElement(tax_scheme, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
                tax_scheme_id.text = "VAT"
                party_tax_scheme.tail = "\n            "
                etree.indent(party_tax_scheme, space="    ", level=3)
                party.insert(party.index(postal_address) + 1, party_tax_scheme)

            # Buyer Name
            buyer_name = self.root.find(
                ".//cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName",
                namespaces={
                    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                },
            )

            buyer_name.text = self.sales_invoice.get("customer").get("RegistrationName")
            
            
    def add_items_data(self) :
        
        if self.sales_invoice.get("InvoiceStatus") == "Standard" and self.sales_invoice.get("InvoiceSubStatus") == "normal" :
            parent_delivery_date = etree.Element("{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Delivery")
            delivery_date = etree.SubElement(parent_delivery_date,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ActualDeliveryDate")
            delivery_date.text = self.sales_invoice.get('ActualDeliveryDate')
            parent_delivery_date.tail = "\n    "
            etree.indent(parent_delivery_date, space="    ", level=1)
                
            customer = self.root.find(".//cac:AccountingCustomerParty", namespaces=NameSpace)
            self.root.insert(self.root.index(customer) + 1, parent_delivery_date)

        # Create Payment means tag if invoice subtype is credit or debit or if payment terms is not empty , note payment terms require payment code .
        # In credit and debit the instruction note is required , note: instruction note require payment code.

        if self.sales_invoice.get("InvoiceSubStatus") in ["debit" , "credit"] :
            # main tag for payment.
            payment_means = etree.Element("{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PaymentMeans")
            # PaymentMeansCode
            payment_means_code = etree.SubElement(payment_means,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PaymentMeansCode")
            payment_means_code.text = self.sales_invoice.get("PaymentMeansCode")

            # check if the subtype is debit or credit to make instruction note (reason for debit or credit)
            instruction_note = etree.SubElement(payment_means,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InstructionNote")
            instruction_note.text = self.sales_invoice.get("InstructionNote")

            # if the payment terms exists then make its tags
            if self.sales_invoice.get("PaymentNote") not in ["", None]:
                payment_terms_parent = etree.SubElement(payment_means,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PayeeFinancialAccount")
                payment_terms = etree.SubElement(payment_terms_parent,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PaymentNote")
                # parse the html editor to take data from invoice
                soup = BeautifulSoup(self.sales_invoice.get("PaymentNote"), "html.parser")
                formatted_text = []
                in_table = False
                for tag in soup.find_all(
                    ["p", "ol", "ul", "li", "table", "tr", "th", "td"]
                ):
                    if tag.name == "p":
                        formatted_text.append(tag.get_text())
                    elif tag.name == "ol":
                        for li in tag.find_all("li"):
                            formatted_text.append(f"- {li.get_text()}")
                    elif tag.name == "ul":
                        for li in tag.find_all("li"):
                            formatted_text.append(f"- {li.get_text()}")
                    elif tag.name == "table":
                        in_table = True
                    elif in_table and tag.name == "tr":
                        row_text = []
                        for cell in tag.find_all(["th", "td"]):
                            row_text.append(cell.get_text())
                        formatted_text.append(" | ".join(row_text))
                    elif in_table and tag.name == "table":
                        in_table = False

                # Set the text of the payment_terms element
                payment_terms.text = "\n".join(formatted_text)

            # Handle spaces and indentation for hashing.
            etree.indent(payment_means, space="    ", level=1)
            # find previous element to get index for insertion
            customer = self.root.find(".//cac:AccountingCustomerParty", namespaces=NameSpace)
            # handle spaces for hashing
            payment_means.tail = "\n    "
            # insert after delivary tag
            self.root.insert(self.root.index(customer) + 1, payment_means)

        # Allowance & Charge on total document (document level)
        # indicator
        # "An indicator that this AllowanceCharge describes a discount.
        # The value of this tag indicating discount (Allowance) must be ""false""."

        ##reason
        customer = self.root.find(".//cac:AccountingCustomerParty", namespaces=NameSpace)
        place = 1

        if self.sales_invoice.get("PaymentMeansCode") :
            place += 1

        if self.sales_invoice.get("ActualDeliveryDate") :
            place += 1

        for allowance_charge in self.sales_invoice.get("TaxSubtotal" , []) :

            if allowance_charge.get("AllowanceChargeAmount" , 0.00) > 0 :
                parent_allowance_charge = etree.Element("{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AllowanceCharge")
                parent_allowance_charge.tail = "\n    "
                charge_indicator = etree.SubElement(parent_allowance_charge,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ChargeIndicator")
                charge_indicator.text =  allowance_charge.get("ChargeIndicator")

                allowance_charge_reason = etree.SubElement(parent_allowance_charge , "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}AllowanceChargeReason")
                allowance_charge_reason.text = allowance_charge.get("AllowanceChargeReason")

                allowance_charge_amount = etree.SubElement(parent_allowance_charge , "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Amount")
                allowance_charge_amount.text = str(flt(allowance_charge.get("AllowanceChargeAmount") , 2))
                allowance_charge_amount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))

                allowance_charge_tax_category = etree.SubElement(parent_allowance_charge , "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxCategory")

                tax_category_id = etree.SubElement(allowance_charge_tax_category , "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
                tax_category_id.text = allowance_charge.get("TaxCategory")
                tax_category_id.set("schemeAgencyID" , "6")
                tax_category_id.set("schemeID", allowance_charge.get("TaxCategorySchemeID"))

                tax_category_percent = etree.SubElement(allowance_charge_tax_category , "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent")
                tax_category_percent.text = allowance_charge.get("Percent")

                tax_scheme = etree.SubElement(allowance_charge_tax_category , "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme")
                tax_scheme_id = etree.SubElement(tax_scheme , "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
                tax_scheme_id.text = "VAT"
                tax_scheme_id.set("schemeAgencyID" , "6")
                tax_scheme_id.set("schemeID" , "UN/ECE 5153")
                
                etree.indent(parent_allowance_charge, space="    ", level=1)

                customer.getparent().insert(
                    customer
                    .getparent()
                    .index(customer) + place ,
                    parent_allowance_charge,
                )

        # tax total amount in company currency (We deal mainly with ksa) , rhera is two tax total amounts one in invoice currency and one in company curreny
        tax_total_tax_amount = self.root.find(".//cac:TaxTotal/cbc:TaxAmount", namespaces=NameSpace)
        tax_total_tax_amount.text = self.sales_invoice.get("TaxTotalTaxAmount")
        tax_total_tax_amount.set("currencyID", self.sales_invoice.get("company").get("DefaultCurrency"))

        # Create all tax breakdowns function
        self.insert_tax_total_elements_after_existing()

        # Create item or invoice lines
        self.add_invoice_items()

        # legal monetary total tag
        ## line extension amount (sum of net amounts without vat or document discounts)
        Line_extension_amount = self.root.find(".//cac:LegalMonetaryTotal/cbc:LineExtensionAmount", namespaces=NameSpace)
        Line_extension_amount.text = self.sales_invoice.get("LineExtensionAmount")
        Line_extension_amount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))

        ## taxt exclusive amount (total without vat with document discounts)
        TaxExclusiveAmount = self.root.find(".//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount", namespaces=NameSpace)
        TaxExclusiveAmount.text = self.sales_invoice.get("TaxExclusiveAmount")
        TaxExclusiveAmount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))

        ## taxt inclusive amount (total with vat and discounts)
        TaxInclusiveAmount = self.root.find(".//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount", namespaces=NameSpace)
        TaxInclusiveAmount.text = self.sales_invoice.get("TaxInclusiveAmount")
        TaxInclusiveAmount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))

        ## allowance total amount

        AllowanceTotalAmount = self.root.find(".//cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount", namespaces=NameSpace)
        AllowanceTotalAmount.text = self.sales_invoice.get("AllowanceTotalAmount")
        AllowanceTotalAmount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))

        ## prepaid amount if exists
        PrepaidAmount = self.root.find(".//cac:LegalMonetaryTotal/cbc:PrepaidAmount", namespaces=NameSpace)
        PrepaidAmount.text = self.sales_invoice.get("PrepaidAmount")
        PrepaidAmount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))

        ## payable amount (I'm using grand to solve some bug , but the outstanding is correct as well)
        PayableAmount = self.root.find(".//cac:LegalMonetaryTotal/cbc:PayableAmount", namespaces=NameSpace)
        PayableAmount.text = self.sales_invoice.get("PayableAmount")
        PayableAmount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))
            
            
    def insert_tax_total_elements_after_existing(self):
        # "Sum of all taxable amounts subject to a specific VAT category code and VAT category rate (if the VAT category rate is applicable).

        TaxTotal_After_Existing = self.root.xpath(".//cac:TaxTotal[last()]", namespaces=NameSpace)

        tax_total = etree.Element("{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal")
        tax_amount = etree.SubElement(tax_total,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount")
        tax_amount.text = self.sales_invoice.get("TaxAmount")
        tax_amount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))
        tax_total.tail = "\n    "
        # main tax subtotal tag

        for sub_total_element in self.sales_invoice.get("TaxSubtotal") :
            
            tax_subtotal = etree.SubElement(tax_total,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxSubtotal")

            # taxable amount for this tax (items net price (that has the tax cat) - document level discount (with same tax cat) + charge (with same tax cat)
            taxable_amount = etree.SubElement(tax_subtotal,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxableAmount")
            taxable_amount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))
            taxable_amount.text = str(flt(sub_total_element.get("TaxableAmount") , 2 ))

            # tax amount
            tax_category_amount = etree.SubElement(tax_subtotal,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount")
            tax_category_amount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))
            tax_category_amount.text = sub_total_element.get("TaxAmount")
            # tax_category_amount.tail = "   "

            # tax cat and scheme tag
            tax_scheme = etree.SubElement(tax_subtotal,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxCategory")

            # tax category (one from [E, Z, S, O])
            tax_scheme_id = etree.SubElement(tax_scheme,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
            tax_scheme_id.set("schemeAgencyID", "6")
            tax_scheme_id.set("schemeID", sub_total_element.get("TaxCategorySchemeID"))
            tax_scheme_id.text = sub_total_element.get("TaxCategory")

            # tax rate
            tax_scheme_percent = etree.SubElement(tax_scheme,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent")
            tax_scheme_percent.text = sub_total_element.get("Percent")

            if sub_total_element.get("TaxExemptionReasonCode") not in ["" , None] :
                
                tax_exemption_reason_code = etree.SubElement(tax_scheme , "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxExemptionReasonCode")
                tax_exemption_reason_code.text = sub_total_element.get("TaxExemptionReasonCode")

                tax_exemption_reason = etree.SubElement(tax_scheme , "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxExemptionReason")
                tax_exemption_reason.text = sub_total_element.get("TaxExemptionReason")

            # Tax scheme id is "VAT" for default
            tax_scheme_type = etree.SubElement(tax_scheme,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme")

            tax_scheme_type_id = etree.SubElement(tax_scheme_type,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
            tax_scheme_type_id.set("schemeAgencyID", sub_total_element.get("schemeAgencyID"))
            tax_scheme_type_id.set("schemeID", "UN/ECE 5153")
            tax_scheme_type_id.text = sub_total_element.get("TaxSchemeID")

            # indent the elements
            etree.indent(tax_total, space="    ", level=1)

            TaxTotal_After_Existing[0].getparent().insert(
                TaxTotal_After_Existing[0]
                .getparent()
                .index(TaxTotal_After_Existing[0]) + 1,
                tax_total,
            )

        
    def add_invoice_items(self):

        item_list = self.sales_invoice.get("items")

        # Find the position to insert new invoice line  elements (after the legal monetary total)
        last_existing_legal_monetary_total = self.root.xpath(".//cac:LegalMonetaryTotal[last()]", namespaces=NameSpace)
            # Iterate through the item list
        for i, item in enumerate(item_list):
            invoice_line = etree.Element("{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceLine")
            # check if item is the last then handle the spaces and indentation for hashing
            invoice_line.tail = "\n    "

            # create item idx
            item_id = etree.SubElement(invoice_line,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
            item_id.text = item.get("ID")

            item_quantity = etree.SubElement(invoice_line,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoicedQuantity")
            item_quantity.set("unitCode", "PCE")
            item_quantity.text = item.get("InvoicedQuantity")

            # item net amount
            item_total_amount = etree.SubElement(invoice_line,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}LineExtensionAmount")
            item_total_amount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))
            item_total_amount.text = item.get("LineExtensionAmount")

            # item taxes
            item_tax_total = etree.SubElement(invoice_line,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal")

            item_tax_amount = etree.SubElement(item_tax_total,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount")
            item_tax_amount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))

            item_tax_amount.text = item.get("TaxAmount")

            # item total with taxes
            item_rounding_amount = etree.SubElement(item_tax_total, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RoundingAmount")
            item_rounding_amount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))
            item_rounding_amount.text = item.get("RoundingAmount")

            # create item tag
            item_item = etree.SubElement(invoice_line,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Item")

            # fill item name
            item_name = etree.SubElement(item_item,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name")
            item_name.text = item.get("Name")

            # item tax cat info
            tax_scheme = etree.SubElement(item_item,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}ClassifiedTaxCategory")

            # tax category from child table element
            tax_scheme_id = etree.SubElement(tax_scheme,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
            tax_scheme_id.text = item.get("TaxCategory")
            tax_scheme_id.set("schemeID", "UNCL5305")

            # tax percent from item tax template
            tax_scheme_percent = etree.SubElement(tax_scheme,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent")
            tax_scheme_percent.text = item.get("Percent")
            # create tax scheme tag
            tax_scheme_type = etree.SubElement(tax_scheme,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme")

            # tax scheme id , by default "VAT"
            tax_scheme_type_id = etree.SubElement(tax_scheme_type,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
            tax_scheme_type_id.text = item.get("TaxScheme")

            # create price tag
            item_price = etree.SubElement(invoice_line,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Price")

            # item price
            item_unit_price = etree.SubElement(item_price,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PriceAmount")
            item_unit_price.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))
            item_unit_price.text = item.get("PriceAmount")

            item_base_qauntity = etree.SubElement(item_price,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}BaseQuantity")
            item_base_qauntity.set("unitCode", "PCE")
            item_base_qauntity.text = "1"

            if item.get("Amount") :
            # charge or allowance on item price not item net line (discount for now)
                item_price_allowance = etree.SubElement(item_price,"{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AllowanceCharge")

                # discount or charge indicator (false for discount , true for charge)
                item_price_allowance_indicator = etree.SubElement(item_price_allowance,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ChargeIndicator")
                item_price_allowance_indicator.text = item.get("ChargeIndicator")

                # discount or charge reason , for now not important , important in charge
                item_price_allowance_reason = etree.SubElement(item_price_allowance, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}AllowanceChargeReason")
                item_price_allowance_reason.text = "discount"

                # item price discount amount
                item_price_allowance_amount = etree.SubElement(item_price_allowance,"{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Amount")
                item_price_allowance_amount.set("currencyID", self.sales_invoice.get("DocumentCurrencyCode"))
                item_price_allowance_amount.text = item.get("Amount")

            # indent the elements
            etree.indent(invoice_line, space="    ", level=1)

            # handle spaces for hashes
            last_existing_legal_monetary_total[0].tail = "\n    "
            # Insert the invoice line element after the legal monetary tag
            last_existing_legal_monetary_total[0].getparent().insert(
                last_existing_legal_monetary_total[0]
                .getparent()
                .index(last_existing_legal_monetary_total[0])
                + int(item.get("ID")),
                invoice_line,
            )
            
    
    def __fill_signed_properities_tag(
        self, signing_time,
    ) -> None:
        # invoice namespaces if needed , use the class nsmap instead
        # read certificate tag from sample file
        certificate = self.root.find(".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningCertificate/xades:Cert/xades:CertDigest/ds:DigestValue",
            namespaces=NameSpace,
        )
        certificate.text = self.sales_invoice.get("DigestValue")

        # signing time
        timestamp = self.root.find(
            ".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningTime",
            namespaces=NameSpace,
        )
        timestamp.text = signing_time

        # certificate issuer
        issuer = self.root.find(
            ".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningCertificate/xades:Cert/xades:IssuerSerial/ds:X509IssuerName",
            namespaces=NameSpace,
        )
        issuer.text = self.sales_invoice.get("X509IssuerName")

        # certificate serial number , remember to cast to string
        serial = self.root.find(
            ".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties//xades:SignedSignatureProperties/xades:SigningCertificate/xades:Cert/xades:IssuerSerial/ds:X509SerialNumber",
            namespaces=NameSpace,
        )
        serial.text = self.sales_invoice.get("X509SerialNumber")
        
        
    def __fill_ubl_ext( self, invoice_hash_encoded, signature_encoded, signed_properities_hash_encoded):
        
        # encoded signature data
        signature = self.root.find(".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignatureValue", namespaces=NameSpace)
        signature.text = signature_encoded

        # encoded certificate
        certificate = self.root.find(".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:KeyInfo/ds:X509Data/ds:X509Certificate",namespaces=NameSpace)
        certificate.text = self.sales_invoice.get("Certificate")

        # encoded signed propertities tag hash
        signed_properities = self.root.find("./ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference[@URI='#xadesSignedProperties']/ds:DigestValue",namespaces=NameSpace)
        signed_properities.text = signed_properities_hash_encoded

        # encoded incoive hash
        invoice_hash = self.root.find(".//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference[@Id='invoiceSignedData']/ds:DigestValue",namespaces=NameSpace)
        invoice_hash.text = invoice_hash_encoded
        # Add Global Value 
        self.hash = invoice_hash_encoded
        
        

    def __final_invoice(self , signature_encoded) -> None:
        # find qr in additonal document reference

        self.qr_code = generate_qr_code(
            self.sales_invoice.get("company").get("RegistrationName"),
            self.sales_invoice.get("company").get("CompanyID"),
            self.sales_invoice.get("IssueDate"),
            self.sales_invoice.get("IssueTime") ,
            invoice_total=self.sales_invoice.get("TaxInclusiveAmount"),
            vat_total=self.sales_invoice.get("TaxAmount"),
            invoice_hash= self.hash ,
            invoice_signature=signature_encoded ,
            public_key_str=self.sales_invoice.get("public_key"),
            signature_ecdsa = self.sales_invoice.get("SignatureInformation")
        )

        qr = self.root.findall(
            ".//cac:AdditionalDocumentReference", namespaces=NameSpace
        )
        for element in qr:
            id_element = element.find(
                ".//cbc:ID",
                namespaces={
                    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                },
            )
            if id_element is not None and id_element.text == "QR":
                element.find(".//cac:Attachment/cbc:EmbeddedDocumentBinaryObject",namespaces=NameSpace).text = self.qr_code


def calculate_invoice_hash(tree):
    """
    Step 1: Remove the <ext:UBLExtensions/> block
    Step 2: Remove the <cac:AdditionalDocumentReference/> block where <cbc:ID/> = "QR"
    Step 3: Remove the <cac:Signature/> block
    Step 4: Remove the XML version declaration (e.g., <?xml version='1.0' encoding='UTF-8'?>)
    Step 5: Canonicalize the Invoice using the C14N11 standard Only comments (Remove comments)
    Step 6:Generate Invoice Hash to use in sign
    Step 7:Convert Hexa String  to Byte
    Step 8:Encode Byte
    """
    # Important note : if the hash is not quite right then use python minidom and loop over all nodes in the sample file to know what is required in hash
    # spaces and linebreaks can mess hash easily
    
    # get the root from the tree
    root = tree.getroot()
    
    # Step 1: Remove the <ext:UBLExtensions/> block
    ubl_extensions = root.find('.//ext:UBLExtensions', namespaces={'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'})
    if ubl_extensions is not None:
        ubl_extensions.getparent().remove(ubl_extensions)
    
    # Step 2: Remove the <cac:AdditionalDocumentReference/> block where <cbc:ID/> = "QR"
    additional_doc_refs = root.findall('.//cac:AdditionalDocumentReference', namespaces={'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'})
    for doc_ref in additional_doc_refs:
        id_element = doc_ref.find('.//cbc:ID', namespaces={'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'})
        if id_element is not None and id_element.text == "QR":
            doc_ref.getparent().remove(doc_ref)

    # Step 3: Remove the <cac:Signature/> block
    signature = root.find('.//cac:Signature', namespaces={'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'})
    if signature is not None:
        signature.getparent().remove(signature)

    # Step 4: Remove the XML version declaration (e.g., <?xml version='1.0' encoding='UTF-8'?>)
    xml_declaration = tree.find('.//xml')
    if xml_declaration is not None:
        root.remove(xml_declaration)

    # Step 5: Canonicalize the Invoice using the C14N11 standard Only comments 
    canonicalized_xml = etree.tostring(root,encoding="utf-8")
    
    # use minidom to handle spaces and linebreaks
    xmlparse = mini.parseString(canonicalized_xml)
    
    #get the profile id tag to add 2 line breaks before it
    profile_id = xmlparse.getElementsByTagName("cbc:ProfileID")[0]

    # Create a new line element with an empty line
    new_line = xmlparse.createTextNode("\n    ")
    new_line2 = xmlparse.createTextNode("\n    ")

    # Insert the new line before the ProfileID element
    profile_id.parentNode.insertBefore(new_line, profile_id)
    profile_id.parentNode.insertBefore(new_line2, profile_id)
    
    # handle issue of self closing tag for payment means code
    payment_means_code = xmlparse.getElementsByTagName("cbc:PaymentMeansCode")
    if payment_means_code:
        # print(payment_means_code)
        payment_means_code[0].appendChild(xmlparse.createTextNode(""))
    
    #handle xml and use make sure to make indent and newl = "" to remove the default 2 lines spaces
    formatted_xml = xmlparse.childNodes[0].toprettyxml(indent="" , newl="")

    # Generate Invoice Hash to use in sign
    invoice_hash = hashlib.sha256(formatted_xml.encode()).hexdigest() # Hexa String 
    
    # Convert Hexa String  to Byte
    BYTE_ARRAY = bytearray.fromhex(invoice_hash)
    
    #  Encode Byte
    digest_value = base64.b64encode(BYTE_ARRAY).decode()

    return digest_value , invoice_hash


def generate_signed_properities_tag_hash(tree):
    # get root from tree
    root = tree.getroot()

    # name spaces if needed
    namespaces = {
        'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
        'sig': 'urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2',
        'sac': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2',
        'sbc': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2',
        'xades': 'http://uri.etsi.org/01903/v1.3.2#',
        'ds': 'http://www.w3.org/2000/09/xmldsig#'
    }

    #signing time 
    SigningTime = root.find(".//xades:SigningTime",namespaces=namespaces)
    if SigningTime is not None:
            Custom_time = SigningTime.text
    
    # certificate encoded
    DigestValue = root.find(".//xades:CertDigest/ds:DigestValue",namespaces=namespaces)
    if DigestValue is not None:
            Custom_digest = DigestValue.text
    
    # issuer name
    X509IssuerName = root.find(".//ds:X509IssuerName",namespaces=namespaces)
    if X509IssuerName is not None:
            Custom_issuer = X509IssuerName.text
    
    # serial number 
    X509SerialNumber = root.find(".//ds:X509SerialNumber",namespaces=namespaces)
    if X509SerialNumber is not None:
            Custom_serial = X509SerialNumber.text
    
    # parse hash file from parts folder its spaces and indentations are handled for hash
    hash_file = mini.parse(f'{frappe.get_app_path("optima_zatca")}/zatca/Samples/Signed_properities_tag/Signed_properities_tag_hash.xml')
    
    SigningTime = hash_file.getElementsByTagName("xades:SigningTime")[0]
    if SigningTime is not None:
            SigningTime.appendChild(hash_file.createTextNode(Custom_time))
    
    DigestValue = hash_file.getElementsByTagName("ds:DigestValue")[0]
    if DigestValue is not None:
            DigestValue.appendChild(hash_file.createTextNode(Custom_digest))
    
    X509IssuerName = hash_file.getElementsByTagName("ds:X509IssuerName")[0]
    if X509IssuerName is not None:
            X509IssuerName.appendChild(hash_file.createTextNode(Custom_issuer))
    
    X509SerialNumber_text = hash_file.getElementsByTagName("ds:X509SerialNumber")[0]
    if X509SerialNumber is not None:
            X509SerialNumber_text.appendChild(hash_file.createTextNode(str(Custom_serial)))

    # file to string to hash
    xml_string  = hash_file.childNodes[0].toprettyxml(indent="" , newl="")

    # hash the tag
    hashed_value = hashlib.sha256(xml_string.encode()).hexdigest()

    # encode the hash hex
    digest_value = base64.b64encode(hashed_value.encode()).decode()
    
    return digest_value



def create_xml_file(tree,invoice_id ,uuid):

    folder_path = get_bench_relative_path(frappe.local.site) + "/public/files/invoices"
    # Check if the folder exists, and create it if not
    
    if not os.path.exists(folder_path):
        
        os.makedirs(folder_path)
        time.sleep(4)
    # write the file
    field = invoice_id + "_uuid_" + uuid +  ".xml"
    tree.write(f"{folder_path}/{field}", encoding="utf-8")


def get_qrcode_from_xml(invoice) :
    xml = re.sub(r'<\?xml.*\?>', '', invoice)
    tree = etree.fromstring(xml)
    qr_element = tree.find(".//cac:AdditionalDocumentReference[cbc:ID='QR']/cac:Attachment/cbc:EmbeddedDocumentBinaryObject", NameSpace)
    return qr_element.text if qr_element is not None  else None
