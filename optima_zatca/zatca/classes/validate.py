import re
import json
import frappe
from frappe import _ 


class ZatcaInvoiceValidate :

    def __init__(self , company_settings : dict , sales_invoice :dict , company_address :dict , customer_info: dict, customer_address :dict ):
        
        self.company_settings = company_settings
        self.sales_invoice = sales_invoice
        self.company_address = company_address
        self.customer_info = customer_info
        self.customer_address = customer_address
        
        self.validate() 

    def validate(self) :
        
        validate_optima_settings_info(self.company_settings)
        validate_address(self.company_address)
        
        self.validate_sales_invoice_sender()
        self.validate_sales_invoice_fields()
        self.validate_credit_or_debit_invoice()
        self.validate_items_fields()
        self.validate_customer_info()

        
    def validate_sales_invoice_sender(self) :

        if self.sales_invoice.get("sent_to_zatca") == 1 :
            frappe.throw(_("Sales Invoice {0} Already Sent".format(self.sales_invoice.get("name"))))
        
        """ Validate IF Sales Invoice Sent Before Or Not """
        sales_invoice_exists = frappe.db.get_all("Optima Zatca Logs" , {
            "reference_doctype" : "Sales Invoice" ,
            "reference_name" : self.sales_invoice.get("name") ,
            "status" : ["in", ["Success"  "Warning" ] ]
        })
        
        if sales_invoice_exists:
            frappe.throw(_("Sales Invoice {0} Already Sent".format(self.sales_invoice.get("name"))))
            
        
    def validate_sales_invoice_fields(self) :
        fields = ["items" , "taxes" , "customer" , "company" , "company_address" ]
        
        for field in fields :
            if self.sales_invoice.get(field) in ["",None , []] :
                frappe.throw(_("Please Fill the field {0} data in 'Sales Invoice' Doc.").format(
                    frappe.bold(frappe.get_meta("Sales Invoice").get_label(field))
                ))


    def validate_credit_or_debit_invoice(self) :

        if ( 
            ( self.sales_invoice.get("is_return") or self.sales_invoice.get("is_debit_note") ) and not
            (  self.sales_invoice.get("return_against") and self.sales_invoice.get("reason_for_issuance") )
        ):
            frappe.throw(_("Fields Missing in Sales Invoice => {0}").format(
                ( "Return Against " if self.sales_invoice.get("is_return") else "Debit Against " ) + "and " + "Reason for Issuance"
            ))


    def validate_items_fields(self) :

        for item in self.sales_invoice.get("items") :
            global tax_category

            if item.get("item_tax_template") in ["",None] :
                frappe.throw(_("Item Tax Template in Item  {0} Missing in row {1}").format(item.get("item_code") , item.get("idx")))

            tax_category = item.get("tax_category")
            if item.get("tax_cateogry") in ["",None] :
                tax_category = frappe.db.get_value("Item Tax Template" , item.get("item_tax_template") , "tax_category")
                
                if not tax_category :
                    frappe.throw(_("Tax Category in Item Tax Template {0} Not Found").format(item.get("item_tax_template")))

            if tax_category == "S" and item.get("tax_exemption") :
                frappe.throw(_("You Should Delete Tax Exemption in Tax Category S in row {0}").format(item.get("idx")))

            elif tax_category in ["Z" , "O" , "E"] and not item.get("tax_exemption") :
                frappe.throw(_("You Should Add Tax Exemption in Tax Category {0} in row {1}").format(tax_category ,item.get("idx")))


            if item.get("tax_exemption") in ["VATEX-SA-HEA" , "VATEX-SA-EDU"] :

                if self.customer_info.get("registration_value") in ["",None] :
                    frappe.throw(_("You Must Add National Id in Customer"))

                if len(str(self.customer_info.get("registration_value")).strip()) != 10 :
                    frappe.throw(title=_("National Id Required"),msg=_("National Id Must 10 no"))

                
    def validate_customer_info(self) :

        if self.customer_info.get("customer_type") == "Company" :
            self.validate_customer_details()
            self.validate_customer_saudia_arabia()
            validate_address(self.customer_address , "Customer")
            
            
    def validate_customer_details(self ) :
        
        customer_fields = ['name','registration_type'  , "registration_value"]
        
        for field in customer_fields:
            if self.customer_info.get(field) in ["",None] :
                frappe.throw(_("Please Fill the field '{0}' data in 'Customer' Doc.").format(self.customer_info.meta.get_label(field)))
                

    def validate_customer_saudia_arabia(self) :
        if self.customer_address.get("country") :
            country_code = frappe.db.get_value("Country" ,self.customer_address.get("country") , "code")
            if country_code == "SA" :
                validate_tax_id_in_saudia_arabia(self.customer_info.get("tax_id"))
                validate_commercial_register(self.customer_info.get("registration_type"),self.customer_info.get("registration_value"))


def validate_commercial_register(registration_type,registration_value) :

    if registration_value in ["",None] :
        frappe.throw(_("Registration Value is Required in Customer"))
        
    if len(str(registration_value).strip()) != 10  and registration_type == "CRN":
        frappe.throw(_("Commercial Register Must 10 no"))

# Main Function

def validate_optima_settings_info(settings):

    fields = ["organization_identifier" , "organization_unit_name" , "organization_name" , "certificate" , "public_key"]

    for field in fields :
        if settings.get(field) in ["",None] :
            frappe.throw(_("Please Fill the field {0} data in Optima Zatca Setting Doc.").format(settings.meta.get_label(field)))

    validate_tax_id_in_saudia_arabia(settings.get("organization_identifier"))


def validate_address(main_address: frappe._dict , address_type="Company") :
    company_address_fields = ['building_no','district','pincode' , "address_line1" , "city" ]

    for field in company_address_fields:
        if main_address.get(field) in ["",None]:
            frappe.throw(
                _("Please Fill the field {0} data in {1} Address Doc.").format(
                    frappe.bold(field.replace("_", " ").title()), address_type
                )
            )

    if len(main_address.get("address_line1")) > 1000 :
        frappe.throw( _("Seller Street Name exeeded maximum charachter limit '1000'") )

    if len(main_address.get("district")) > 127 :
        frappe.throw(_("Seller Seller district exeeded maximum charachter limit '127' "))

    if len(main_address.get("city")) > 100 :

        frappe.throw(_("Seller Seller district exeeded maximum charachter limit '100' "))

    if len(main_address.get("pincode")) != 5 :
        frappe.throw(_("Postal Code should be 5 digits"))

    if len(main_address.get("building_no")) != 4 :
        frappe.throw(_("Building Number should be 4 digits"))


def validate_tax_id_in_saudia_arabia(tax_id) -> None :
    """
    Tax ID Must Begin 3 and End 3
    Tax ID Must Only Number , Begin 3 , End 3  and Must be 15 Number Long
    
    *args* : (tax_id : str)
    
    """
    if not tax_id :
        frappe.throw(title=_("Invalid Tax ID") , msg=_("Tax ID is Required"))
    
    if isinstance(tax_id , str) :
        tax_id = str(tax_id)
    
    if len(tax_id.strip()) != 15 :
        frappe.throw(title=_("Invalid Tax ID") , msg=_("Tax ID must be at least 15 Number"))
        
    if tax_id[0] not in [3 , "3"] or tax_id[-1] not in [3 , "3"] :
        frappe.throw(title=_("Invalid Tax ID") , msg=_("Tax ID Must Begin 3 and End 3"))
        
    if not bool(re.match(r'^3\d{13}3$' , tax_id))  :
        frappe.throw(title=_("Invalid Tax ID") , msg=_("Tax ID Must Only Number , Begin 3 , End 3  and Must be 15 Number Long"))


def validate_register_data(**kwargs) :

    validate_global_data(kwargs)
    validate_company_exists(kwargs.get("company"))
    validate_tax_id_in_saudia_arabia(kwargs.get("tax_id"))
    
    if isinstance(kwargs.get("commercial_register") , str) :
        list_of_branches = json.loads(kwargs.get("commercial_register"))

    for address in list_of_branches  :
        validate_address(address)


def validate_global_data(kwargs):
    fields = ["company" , "company_name_in_arabic" , "tax_id" , "commercial_register"]

    for field in fields :
        if kwargs.get(field) in ["",None] :
            frappe.throw(_("Missing Field {0}").format(field.replace("_" , " ").title()))

def validate_company_exists(company) :

    if not frappe.db.exists("Company" ,company) :
        frappe.throw(_("Company {0} Not Found").format(company))


def validate_otp(otp) :

    if not isinstance(otp , str) :
        otp = str(otp)

    if len(otp) != 6 :
        frappe.throw(_("OTP Must Be 6 Digits"))
