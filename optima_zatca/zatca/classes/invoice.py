import json , uuid , frappe
from frappe import _ , _dict
from datetime import datetime
from frappe.utils import flt
from optima_zatca.zatca.classes.validate import ZatcaInvoiceValidate
from optima_zatca.zatca.classes.xml import ZatcaXml
# from optima_zatca.zatca.classes.base import ZatcaBase


# Modified PIH and ICV => InvoiceCounter

class ZatcaInvoiceData : 
    
    def __init__(self,  sales_invoice :dict ):

        self.zatca_invoice = frappe._dict()
        self.sales_invoice = sales_invoice
        self.company_settings = frappe.get_doc("Optima Zatca Setting", {"commercial_register": sales_invoice.get("commercial_register") })
        self.company_address = frappe.get_doc("Address", sales_invoice.get("company_address")) if sales_invoice.get("company_address")  else {}
        self.customer_info = frappe.get_doc("Customer", sales_invoice.get("customer")) if sales_invoice.get("customer")  else {}
        self.customer_address = frappe.get_doc("Address", sales_invoice.get("customer_address")) if sales_invoice.get("customer_address")  else {}
        self.customer_country_code = "SA"
        self.validate_invoice()

        self.included_in_print_rate = any(map(lambda x : x.get("included_in_print_rate") , self.sales_invoice.get("taxes")))

        self.handle_data_to_xml()
        self.make_xml()
        
        # self.create_json_file()


    def validate_invoice(self) :
        obj = ZatcaInvoiceValidate(
            self.company_settings,
            self.sales_invoice, 
            self.company_address, 
            self.customer_info , 
            self.customer_address
        )

    def make_xml(self) :
        self.xml = ZatcaXml(self.zatca_invoice)
        
    def handle_data_to_xml(self) :
        
        self.add_sales_invoice_basic_data()
        self.add_other_info_about_invoice()
        self.add_details_for_debit_or_credit()
        self.add_company_information()
        self.add_customer_type_company()
        self.add_customer_type_individual()
        self.add_type_of_invoice()
        self.add_global_taxes()
        self.add_sales_invoice_totals()
        self.add_invoice_lines_and_tax_categories()
        self.add_additional_data()
        
    def add_company_information(self) :
        
        self.zatca_invoice.update({
            "company" : _dict({
                "ID" : self.company_settings.get("commercial_register") , 
                "schemeID" : self.company_settings.get("registration_type") ,
                "CompanyID" : self.company_settings.get("organization_identifier"),
                "RegistrationName" : self.company_settings.get("organization_name").strip(),
                "IdentificationCode" : "SA" , # Saudia Arabia 
                "CitySubdivisionName" : self.company_address.get("district") ,
                "BuildingNumber" : self.company_address.get("building_no"),
                "StreetName" : self.company_address.get("address_line1"),
                "PostalZone" : self.company_address.get("pincode"),
                "CityName" : self.company_address.get("city"),
                "CountrySubentity" : self.company_address.get("state") ,
                "TaxSchemeID" : "VAT" ,
                "DefaultCurrency" : "SAR",
            })
        })
    
    
    def add_customer_type_company(self) :
        
        if self.customer_info.get("customer_type") == "Company" :
            self.customer_country_code = ( frappe.db.get_value("Country" ,self.customer_address.get("country") , "code") or "SA" ).upper() 
            self.zatca_invoice.update({
                "customer" : _dict({
                    "ID" : self.customer_info.get("registration_value") , 
                    "schemeID" : self.customer_info.get("registration_type")  , # type of registration tax_id , commercial_register
                    "CompanyID" : self.customer_info.get("tax_id"),
                    "RegistrationName" : self.customer_info.get("customer_name_in_arabic")  or self.customer_info.get("name"),
                    "IdentificationCode" : self.customer_country_code ,
                    "CitySubdivisionName" : self.customer_address.get("district"),
                    "BuildingNumber" : self.customer_address.get("building_no"),
                    "StreetName" : self.customer_address.get("address_line1"),
                    "PostalZone" : self.customer_address.get("pincode"),
                    "CityName" : self.customer_address.get("city" ),
                    "CountrySubentity" : self.customer_address.get("state" ),
                    "TaxSchemeID" : "VAT" ,
                })
            })
        
        
    def add_customer_type_individual(self) :
        
        if self.customer_info.get("customer_type") == "Individual" :

            customer_details = {
                "TaxSchemeID" : "VAT" ,
                "ID" : self.customer_info.get("registration_value") ,
                "schemeID" : self.customer_info.get("registration_type") ,
                "RegistrationName" : self.sales_invoice.get("customer_name")
            }

            if self.customer_address.get("country") :
                self.customer_country_code = ( frappe.db.get_value("Country" ,self.customer_address.get("country") , "code") or "SA" ).upper()


            self.zatca_invoice["customer"] = customer_details


            
            
    def add_details_for_debit_or_credit(self) :
        
        if self.customer_info.get("customer_type") == "Company"  and self.zatca_invoice.get("InvoiceSubStatus") not in ["credit" , "debit"] :
            
            self.zatca_invoice.update({
                "ActualDeliveryDate" : str(self.sales_invoice.get("posting_date")) ,
            })
            
            
    def add_sales_invoice_basic_data(self) :

        TimeFormat = "%H:%M:%S.%f" if "." in str(self.sales_invoice.get("posting_time")) else "%H:%M:%S"
        
        self.zatca_invoice.update({
            "X509SerialNumber" : self.company_settings.get("serial_number509") ,
            "X509IssuerName" : self.company_settings.get("issuer_name") ,
            "DigestValue" : self.company_settings.get("certificate_hash") ,
            "Certificate" : self.company_settings.get("certificate") ,
            'SignatureInformation' : self.company_settings.get("signature"),
            "private_key" : self.company_settings.get("private_key") ,
            "public_key" : self.company_settings.get("public_key").strip() ,
            "ProfileID" : "reporting:1.0" ,
            "ID" : self.sales_invoice.get("name") ,
            "UUID" : str(uuid.uuid4()) ,
            "IssueDate" : str(self.sales_invoice.get("posting_date")) ,
            "IssueTime" :  datetime.strptime(str(self.sales_invoice.get("posting_time")) , TimeFormat ).strftime("%H:%M:%S"),
            "Note" : self.sales_invoice.get("remarks" , "No Remarks"),
            "DocumentCurrencyCode" : self.sales_invoice.get("currency") ,
            "TaxCurrencyCode" : "SAR" ,
            "PaymentNote" : self.sales_invoice.get("terms") ,
        })
        
        
    def add_type_of_invoice(self) :
        
        InvoiceTypeCodeName , InvoiceTypeCode , InvoiceStatus , InvoiceSubStatus , ClearanceStatus = "" , "" , "" , "" , ""

        if self.customer_info.get("customer_type") == "Company" :
            
            InvoiceTypeCodeName , InvoiceStatus  , ClearanceStatus =  "0100000" , "Standard" , "1"
                
        elif self.customer_info.get("customer_type") == "Individual" :
            
            InvoiceTypeCodeName , InvoiceStatus , ClearanceStatus=  "0200000" , "Simplified" , "0"


        if self.customer_country_code != "SA" :
            InvoiceTypeCodeName = "0200100" if self.customer_info.get("customer_type") == "Individual" else "0100100"
            
        if self.sales_invoice.get("is_return") == 1 :
            InvoiceSubStatus = "credit"
            InvoiceTypeCode = "381"
            
        elif self.sales_invoice.get("is_debit_note") == 1 :
            InvoiceSubStatus = "debit"
            InvoiceTypeCode = "383"
            
        else :
            InvoiceSubStatus = "normal"
            InvoiceTypeCode = "388"
            
        if self.company_settings.get("check_pcsid") == 1 and self.company_settings.get("check_csid") == 1:
            
            EndPoint = "clearance"  if InvoiceStatus == "Standard" else "reporting"
            
        elif self.company_settings.get("check_csid") == 1 and self.company_settings.get("check_csr") == 1 :
            
            EndPoint = "complainace_checks"
            
        pih , icv = get_invoice_counter_and_pih(EndPoint ,self.company_settings)
        
        self.zatca_invoice.update({
            "InvoiceTypeCode" : InvoiceTypeCode ,
            "InvoiceTypeCodeName" : InvoiceTypeCodeName ,
            "InvoiceStatus" : InvoiceStatus ,
            "InvoiceSubStatus" : InvoiceSubStatus ,
            "Clearance-Status" : ClearanceStatus ,
            "EndPoint" : EndPoint ,
            "Environment" : self.company_settings.get("api_endpoints"),
            "InvoiceCounter" : str(icv) ,
            "PIH" : str(pih) ,
        })

    def add_other_info_about_invoice(self) :
        
        if self.sales_invoice.get("is_return") == 1  or self.sales_invoice.get("is_debit_note") == 1 :
            
            self.zatca_invoice.update({
                "InstructionNote" : self.sales_invoice.get("reason_for_issuance") ,
                "PaymentMeansCode" : "10" ,
                "ReturnAgainst" : self.sales_invoice.get("return_against"),
            })
            
            
        
    def add_global_taxes(self) :
        # Allow One TAX ONly
        self.zatca_invoice.update({
            "TaxAmount" : "{:.2f}".format(abs(self.sales_invoice.get("total_taxes_and_charges"))),
            "TaxTotalTaxAmount" : "{:.2f}".format(abs(self.sales_invoice.get("base_total_taxes_and_charges"))), #in Qrcode and IF Difference in currency 
            "TaxCategorySchemeID" : "UNCL5305" ,
        })


            
        
    def add_sales_invoice_totals(self) :
        AllowanceTotalAmount = "{:.2f}".format(abs(self.sales_invoice.get("discount_amount" , 0))) if self.sales_invoice.get("discount_amount") else "0.00"
        
        LineExtensionAmount = str(flt(abs(
            self.sales_invoice.get("net_total") + self.sales_invoice.get("discount_amount") 
            if self.included_in_print_rate 
            else self.sales_invoice.get("total")
        ) , 2 ))


        self.zatca_invoice.update({
            "LineExtensionAmount" : LineExtensionAmount ,
            "TaxExclusiveAmount" :  str(flt(abs(self.sales_invoice.get("net_total")) , 2)) ,
            "TaxInclusiveAmount" :  str(flt(abs(self.sales_invoice.get("grand_total") ), 2)) ,
            "AllowanceTotalAmount" :  AllowanceTotalAmount ,
            "PrepaidAmount" :  "0.00" , # Current Zero Until Handle advanced Payment
            "PayableAmount" :  str(flt(abs(self.sales_invoice.get("grand_total") ), 2)) ,
        })

    def add_invoice_lines_and_tax_categories(self) :

        tax_subtotals = {}
        invoice_line = []

        for item in self.sales_invoice.get("items") :

            self.add_invoice_item(item , invoice_line )
            self.add_tax_cateogry(item , tax_subtotals)

        
        self.zatca_invoice['items'] = invoice_line
        self.zatca_invoice["TaxSubtotal"] = list(tax_subtotals.values())



    def add_invoice_item(self, item:dict , invoice_line:list) :

        item_row = {
            "ID" : str(item.get("idx")) ,
            "InvoicedQuantity" : str(abs(item.get("qty"))) ,
            "LineExtensionAmount" : str(flt(abs(item.get("line_extension_amount") )  , 2)) ,
            "TaxAmount" : str(flt(abs(item.get("tax_amount") ) , 2 ))  ,
            "RoundingAmount" : str(flt(abs(item.get("total_amount") ) , 2) ) ,
            "Name" : item.get("item_code") ,
            "TaxCategory" :  item.get("tax_category") or frappe.db.get_value("Item Tax Template" , item.get("item_tax_template") , "tax_category") ,
            "Percent" : str(flt(abs(item.get("tax_rate") ) , 2) )  ,
            "TaxScheme" : "VAT" ,
            "PriceAmount" : str(flt(abs(item.get("price_amount") ), 2 ) ) , 
            
        }    

        if item.get("discount_amount") :
            item_row.update({
                "ChargeIndicator" : "false" ,
                "Amount" : str(flt(abs(item.get("discount_amount"))  , 2))
            })

        invoice_line.append(item_row)


    def add_tax_cateogry(self , item , tax_subtotals) :

        tax_category = item.get("tax_category") or  frappe.db.get_value("Item Tax Template" , item.get("item_tax_template") , "tax_category") 

        if tax_category not in tax_subtotals :
            tax_subtotals[tax_category] = {
                "TaxCategory": tax_category, 
                "Percent": str(abs(item.tax_rate)), 
                "TaxAmount": "0.00" , 
                "TaxableAmount" : abs(item.net_amount) ,
                "TaxCategorySchemeID" : "UNCL5305" ,
                "TaxSchemeID" : "VAT" ,
                "schemeAgencyID" : "6" ,
                "TaxExemptionReasonCode" : "",
                "TaxExemptionReason" : "" ,
                "ChargeIndicator" : "false" ,
                "AllowanceChargeReason" : "discount" ,
                "AllowanceChargeAmount" : abs(item.get("item_discount")),
            }

            if tax_category == "S" :
                tax_subtotals[tax_category]["TaxAmount"] = str(abs(self.sales_invoice.get("total_taxes_and_charges")))

            else :
                tax_subtotals[tax_category]["TaxExemptionReasonCode"] = item.get("tax_exemption")
                tax_subtotals[tax_category]["TaxExemptionReason"] =  frappe.db.get_value("Tax Exemption" , item.get("tax_exemption") , "description").strip()
            
        else :
            tax_subtotals[tax_category]["TaxableAmount"] += abs(item.net_amount)
            tax_subtotals[tax_category]["AllowanceChargeAmount"] += abs(item.get("item_discount"))



    def add_additional_data(self) :
        
        additional_data = {}
        
        if self.sales_invoice.get("po_no") and self.sales_invoice.get("po_date") :
            
            additional_data.update({
                "PurchaseOrderID" : self.sales_invoice.get("po_no") ,
                "PurchaseOrderIssueDate" : self.sales_invoice.get("po_date")
            })


    def create_json_file(self) :
        # For Testing
        from frappe.utils import get_bench_relative_path
        import random 
        num = random.randint(1, 10000)
        with open(get_bench_relative_path(frappe.local.site) + f"/sales{num}invoice.json" , "w") as file :
            file.write(
                json.dumps(self.zatca_invoice , ensure_ascii=False)
            )


def get_invoice_counter_and_pih(endpoint , company_settings:_dict) :

    pih , icv = "idfhpoahfosanldhvusjnaljuidsuhahehah" , 1

    last_doc = frappe.db.sql(""" 
        SELECT 
            icv , hash 
        FROM `tabOptima Zatca Logs` 
        WHERE status IN ( "Success" , "Warning" ) 
            AND reference_doctype = "Sales Invoice" 
            AND company = %(company)s AND commercial_register = %(commercial_register)s 
            AND environment = %(environment)s 
            AND api_endpoint IN %(api_endpoint)s 
            AND icv = (
                SELECT MAX(icv) FROM `tabOptima Zatca Logs`
                WHERE status IN ( "Success" , "Warning" ) 
                    AND reference_doctype = "Sales Invoice" 
                    AND company = %(company)s AND commercial_register = %(commercial_register)s 
                    AND environment = %(environment)s 
                    AND api_endpoint IN %(api_endpoint)s 
            )
        LIMIT 1 """ , {
            "company" : company_settings.company ,
            "commercial_register" : company_settings.commercial_register , 
            "environment" : company_settings.api_endpoints ,
            "api_endpoint" : [endpoint] if endpoint == "complainace_checks" else ["reporting" , "clearance"]
        } , 
    as_dict=1)

    if last_doc :
        if last_doc[0].get("icv") not in  ["" , None] :
            pih , icv = last_doc[0].get("hash") , last_doc[0].get("icv") + 1
            
    return pih , icv

