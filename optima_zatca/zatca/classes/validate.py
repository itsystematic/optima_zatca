import re
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
        
        # self.validate_sales_invoice_sender()
        self.validate_sales_invoice_fields()
        self.validate_items_fields()
        self.validate_customer_info()

        
    def validate_sales_invoice_sender(self) :

        if self.sales_invoice.get("zatca_sent") == 1 :
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

    def validate_items_fields(self) :

        for item in self.sales_invoice.get("items") :

            if item.get("item_tax_template") in ["",None] :
                frappe.throw(_("Item Tax Template in Item  {0} Missing in row {1}").format(item.get("item_code") , item.get("idx")))

            if item.get("tax_cateogry") in ["",None] :
                tax_category = frappe.db.get_value("Item Tax Template" , item.get("item_tax_template") , "tax_category")
                
                if not tax_category :
                    frappe.throw(_("Tax Category in Item Tax Template {0} Not Found").format(item.get("item_tax_template")))


    def validate_taxes_and_charges(self) :

        if len(self.sales_invoice.get("taxes")) != 1 :
            frappe.throw(_("Invoice Must Have Only One VAT"))

                
    def validate_customer_info(self) :

        if self.customer_info.get("customer_type") == "Company" :
            self.validate_customer_details()
            validate_tax_id_in_saudia_arabia(self.customer_info.get("tax_id"))
            validate_address(self.customer_address)
            
            
    def validate_customer_details(self ) :
        
        customer_fields = [ 'tax_id','name','registration_type' , "customer_primary_address" , "registration_value"]
        
        for field in customer_fields:
            if self.customer_info.get(field) in ["",None] :
                frappe.throw(_("Please Fill the field '{0}' data in 'Customer' Doc.").format(self.customer_info.meta.get_label(field)))
                
        commercial_register = self.customer_info.get("registration_value") 
        
        if len(str(commercial_register).strip()) != 10 :
            frappe.throw(_("Commercial Register Must 10 no"))
                


# Main Function 

def validate_optima_settings_info(settings):

    fields = ["organization_identifier" , "organization_unit_name" , "organization_name" , "certificate" , "public_key"]

    for field in fields :
        if settings.get(field) in ["",None] :
            frappe.throw(_("Please Fill the field {0} data in Optima Zatca Setting Doc.").format(settings.meta.get_label(field)))

    validate_tax_id_in_saudia_arabia(settings.get("organization_identifier"))


def validate_address(main_address: frappe._dict):
    company_address_fields = ['building_no','district','pincode' , "address_line1" , "city" ]
    
    for field in company_address_fields:
        if main_address.get(field) in ["",None]:
            frappe.throw(_("Please Fill the field '{0}' data in 'Company Address' Doc.").format(main_address.meta.get_label(field)))
            
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
    
    if isinstance(tax_id , str) :
        tax_id = str(tax_id)
    
    if len(tax_id.strip()) != 15 :
        frappe.throw(title=_("Invalid Tax ID") , msg=_("Tax ID must be at least 15 Number"))
        
    if tax_id[0] not in [3 , "3"] or tax_id[-1] not in [3 , "3"] :
        frappe.throw(title=_("Invalid Tax ID") , msg=_("Tax ID Must Begin 3 and End 3"))
        
    if not bool(re.match(r'^3\d{13}3$' , tax_id))  :
        frappe.throw(title=_("Invalid Tax ID") , msg=_("Tax ID Must Only Number , Begin 3 , End 3  and Must be 15 Number Long"))

