
import frappe
import json
from os import listdir
from click import secho
from frappe import get_app_path
from frappe import make_property_setter
from frappe.core.doctype.data_import.data_import import import_doc
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


ADDRESS_DOCTYPE_FIELDS = [
    "address_title", "address_type", "section_break_123", "short_address", "address_line1", "city", "pincode", 
    "column_break_tshas","building_no" , "address_line2", "district", "address_details", "address_name_in_arabic", 
    "county", "state", "country", "column_break0", "email_id", "phone", "fax", "tax_category", "is_primary_address", 
    "is_shipping_address", "disabled", "linked_with", "is_your_company_address", "links"
]

SellingChildTable = [
    {
        "fieldname" : "tax_category" ,
        "fieldtype" : "Link" ,
        "label" : "Tax Category" ,
        "insert_after" : "item_tax_template",
        "options" : "Tax Category",
        "read_only" : 1,
        "hidden" : 1,
    },
    {
        "fieldname" : "price_amount" ,
        "label" : "Price Amount" ,
        "fieldtype" : "Float" ,
        "insert_after" : "tax_category",
        "read_only" : 1,
        "hidden" : 1,
        "no_copy" : 1,
    },
    {
        "fieldname" : "line_extension_amount" ,
        "label" : "Line Extension Amount" ,
        "fieldtype" : "Float" ,
        "insert_after" : "price_amount",
        "read_only" : 1,
        "hidden" : 1,
        "no_copy" : 1,
    },
    {
        "fieldname" : "item_discount" ,
        "label" : "Item Discount" ,
        "fieldtype" : "Float" ,
        "insert_after" : "line_extension_amount",
        "read_only" : 1,
        "hidden" : 1,
        "no_copy" : 1,
    },
    {
        "fieldname" : "tax_rate" ,
        "fieldtype" : "Float" ,
        "label" : "Tax Rate" ,
        "insert_after" : "item_discount",
        "read_only" : 1 ,
        "hidden" : 1,
    },
    {
        "fieldname" : "tax_amount" ,
        "fieldtype" : "Float" ,
        "label" : "Tax Amount" ,
        "insert_after" : "tax_rate",
        "read_only" : 1,
        "hidden" : 1,
    },
    {
        "fieldname" : "total_amount" ,
        "fieldtype" : "Currency" ,
        "label" : "Total Amount" ,
        "insert_after" : "tax_amount",
        "read_only" : 1,
        "hidden" : 1,
    },
    {
        "fieldname" : "tax_exemption" ,
        "fieldtype" : "Link" ,
        "label" : "Tax Exemption" ,
        "insert_after" : "total_amount" ,
        "options" : "Tax Exemption"
    },
]

def after_app_install(app_name) :

    if app_name != "optima_zatca" : return 

    create_additional_fields()
    create_property_setter()
    add_standard_data()
    add_zatca_role()



def add_standard_data() :
    all_files_in_folders = listdir(get_app_path("optima_zatca", "files"))
    secho("Install Doctypes From Files  => {}".format(" , ".join(all_files_in_folders)), fg="blue")
    for file in all_files_in_folders:
        import_doc(get_app_path("optima_zatca", "files/" + f"{file}"))


def create_additional_fields() :
    
    custom_fields = {
        "Company" : [
            {
                "fieldname" : "company_name_in_arabic" ,
                "fieldtype" : "Data" ,
                "label" : "Company Name In Arabic",
                "insert_after" : "",
                "description" : "This name must match the company name in the government commercial register."
            },
            {
                "fieldname" : "section_break87956",
                "fieldtype" : "Section Break",
                "insert_after" : "company_name_in_arabic",
            }
        ],
        "Address" : [
            {
                "fieldname" : "section_break_123" ,
                "fieldtype" : "Section Break",
                "label" : "Saudi National Address Components" ,
                "insert_after" : "address_type",
            },
            {
                "fieldname" : "short_address" ,
                "fieldtype" : "Data" ,
                "label" : "Short Address" ,
                "insert_after" : "section_break_123" ,
            },
            {
                "fieldname" : "building_no" ,
                "fieldtype" : "Data" ,
                "label" : "Building No" ,
                "insert_after" : "column_break_tshas" ,
            },
            {
                "fieldname" : "column_break_tshas" ,
                "fieldtype" : "Column Break" ,
                "insert_after" : "pincode" ,
            },
            {
                "fieldname" : "district" ,
                "fieldtype" : "Data" ,
                "label" : "District" ,
                "insert_after" : "address_line2" ,
            },
            {
                "fieldname" : "address_name_in_arabic" ,
                "fieldtype" : "Data" ,
                "label" : "Address Name In Arabic" ,
                "insert_after" : "address_details" ,
            },
        ],
        "Branch" : [
            {
                "fieldname" : "commercial_register" ,
                "fieldtype" : "Link" ,
                "label" : "Commercial Register" ,
                "insert_after" : "branch",
                "options" : "Commercial Register" ,
                "description" : "this field should contain the 10-digit"
            }
        ],
        #  Zatca Fields Mandatory in Cases
        "Sales Invoice" : [
            {
                "fieldname" : "commercial_register" ,
                "fieldtype" : "Link" ,
                "label" : "Commercial Register" ,
                "insert_after" : "company",
                "options" : "Commercial Register" ,
                "description" : "this field should contain the 10-digit" ,
                "reqd" : 1
            },
            {
                "fieldname" : "clearance_or_reporting",
                "fieldtype" : "Data" ,
                "label" : "Clearance Or Reporting" ,
                "insert_after" : "column_break_14" ,
                "read_only" : 1,
                "no_copy" : 1
            },
            {
                "fieldname" : "reason_for_issuance",
                "fieldtype" : "Small Text" ,
                "label" : "Reason For issuance" ,
                "insert_after" : "is_debit_note" ,
                "depends_on" : "eval: doc.is_return || doc.is_debit_note",
                "mandatory_depends_on" : "eval: doc.is_return || doc.is_debit_note"
            },
            {
                "fieldname" : "ksa_einv_qr" ,
                "fieldtype" : "Attach Image" ,
                "label" : "KSA E-Invoicing QR" ,
                "insert_after" : "",
                "read_only" : 1,
                "hidden" : 1,
                "no_copy" : 1
            },
            {
                "fieldname" : "section_break89",
                "fieldtype" : "Section Break",
                "insert_after" : "ksa_einv_qr" ,
            },
            {
                "fieldname" : "sent_to_zatca" ,
                "fieldtype" : "Check" ,
                "label" : "Sent To Zatca" ,
                "insert_after" : "is_discounted",
                "read_only" : 1 ,
                "no_copy" : 1
            },

        ],
        "Sales Invoice Item" : SellingChildTable ,
        "Quotation Item" : SellingChildTable ,
        "Sales Order Item" : SellingChildTable ,
        "Delivery Note Item" : SellingChildTable ,
        "POS Invoice Item" : SellingChildTable ,
        
        "Customer" : [
            {
                "fieldname" : "registration_type",
                "fieldtype" : "Link" ,
                "label" : "Registration Type" ,
                "insert_after" : "tax_id",
                "options" : "Registration Type",
                "depends_on" : "",
                "mandatory_depends_on" : "eval: doc.customer_type == 'Company' " ,
                "default" : "CRN"
            },
            {
                "fieldname" : "registration_value" ,
                "fieldtype" : "Data" ,
                "label" : "Registration Value" ,
                "insert_after" : "registration_type",
                "depends_on" : "",
                "mandatory_depends_on" : "eval: doc.customer_type == 'Company' " 
            }
        ], 
        "Item Tax Template" : [
            {
                "fieldname" : "tax_category" ,
                "fieldtype" : "Link" ,
                "label" : "Tax Category" ,
                "insert_after" : "company",
                "options" : "Tax Category",
            },
        ]
    }

    create_custom_fields(custom_fields , update=False)



def create_property_setter() :

    property_setter = [
        {
            "doctype": "Address",
            "doctype_or_field": "DocField",
            "fieldname": "address_line1",
            "property": "label",
            "value": "Street",
            "property_type": "Data",
        },
        {
            "doctype": "Address",
            "doctype_or_field": "DocField",
            "fieldname": "address_line2",
            "property": "label",
            "value": "Secondary No",
            "property_type": "Data",
        },
        {
            "doctype": "Address",
            "doctype_or_field": "DocType",
            "fieldname": "address_line3",
            "property": "field_order",
            "value": json.dumps(ADDRESS_DOCTYPE_FIELDS),
            "property_type": "Data",
        },

        # Section Discount , Round Total 
        {
            "doctype": "Sales Invoice",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "read_only",
            "value": 1,
            "property_type": "Check",
        },
        {
            "doctype": "Sales Invoice",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "default",
            "value": "Net Total",
            "property_type": "Data",
        },
        {
            "doctype": "Sales Invoice",
            "doctype_or_field": "DocField",
            "fieldname" : "disable_rounded_total",
            "property": "default",
            "value" : 1,
            "property_type": "Check",
        },
        {
            "doctype": "Sales Invoice",
            "doctype_or_field": "DocField",
            "fieldname" : "disable_rounded_total",
            "property": "hidden",
            "value" : 1,
            "property_type": "Check",
        },
        #  End Section Discount , Round Total
        # Section Discount , Round Total 
        {
            "doctype": "Sales Order",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "read_only",
            "value": 1,
            "property_type": "Check",
        },
        {
            "doctype": "Sales Order",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "default",
            "value": "Net Total",
            "property_type": "Data",
        },
        {
            "doctype": "Sales Order",
            "doctype_or_field": "DocField",
            "fieldname" : "disable_rounded_total",
            "property": "default",
            "value" : 1,
            "property_type": "Check",
        },
        {
            "doctype": "Sales Order",
            "doctype_or_field": "DocField",
            "fieldname" : "disable_rounded_total",
            "property": "hidden",
            "value" : 1,
            "property_type": "Check",
        },
        #  End Section Discount , Round Total
        # Section Discount , Round Total 
        {
            "doctype": "Quotation",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "read_only",
            "value": 1,
            "property_type": "Check",
        },
        {
            "doctype": "Quotation",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "default",
            "value": "Net Total",
            "property_type": "Data",
        },
        {
            "doctype": "Quotation",
            "doctype_or_field": "DocField",
            "fieldname" : "disable_rounded_total",
            "property": "default",
            "value" : 1,
            "property_type": "Check",
        },
        {
            "doctype": "Quotation",
            "doctype_or_field": "DocField",
            "fieldname" : "disable_rounded_total",
            "property": "hidden",
            "value" : 1,
            "property_type": "Check",
        },
        #  End Section Discount , Round Total
        # Section Discount , Round Total 
        {
            "doctype": "Delivery Note",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "read_only",
            "value": 1,
            "property_type": "Check",
        },
        {
            "doctype": "Delivery Note",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "default",
            "value": "Net Total",
            "property_type": "Data",
        },
        {
            "doctype": "Delivery Note",
            "doctype_or_field": "DocField",
            "fieldname" : "disable_rounded_total",
            "property": "default",
            "value" : 1,
            "property_type": "Check",
        },
        {
            "doctype": "Delivery Note",
            "doctype_or_field": "DocField",
            "fieldname" : "disable_rounded_total",
            "property": "hidden",
            "value" : 1,
            "property_type": "Check",
        },
        #  End Section Discount , Round Total
        {
            "doctype": "Sales Invoice",
            "doctype_or_field": "DocField",
            "fieldname" : "taxes_and_charges",
            "property": "hidden",
            "value" : 1,
            "property_type": "Data",
        },
        {
            "doctype": "Sales Invoice",
            "doctype_or_field": "DocField",
            "fieldname" : "tax_category",
            "property": "hidden",
            "value" : 1,
            "property_type": "Data",
        },
        {
            "doctype": "Sales Order",
            "doctype_or_field": "DocField",
            "fieldname" : "taxes_and_charges",
            "property": "hidden",
            "value" : 1,
            "property_type": "Data",
        },
        {
            "doctype": "Sales Order",
            "doctype_or_field": "DocField",
            "fieldname" : "tax_category",
            "property": "hidden",
            "value" : 1,
            "property_type": "Data",
        },
        {
            "doctype": "Quotation",
            "doctype_or_field": "DocField",
            "fieldname" : "taxes_and_charges",
            "property": "hidden",
            "value" : 1,
            "property_type": "Data",
        },
        {
            "doctype": "Quotation",
            "doctype_or_field": "DocField",
            "fieldname" : "tax_category",
            "property": "hidden",
            "value" : 1,
            "property_type": "Data",
        },
        {
            "doctype": "Delivery Note",
            "doctype_or_field": "DocField",
            "fieldname" : "taxes_and_charges",
            "property": "hidden",
            "value" : 1,
            "property_type": "Data",
        },
        {
            "doctype": "Delivery Note",
            "doctype_or_field": "DocField",
            "fieldname" : "tax_category",
            "property": "hidden",
            "value" : 1,
            "property_type": "Data",
        },

    ]

    for setter in property_setter :
        make_property_setter(setter , ignore_validate=False , is_system_generated=True)


def add_zatca_role() :
    if frappe.db.exists("Role" , "Zatca Role") :return
    frappe.get_doc({
        "doctype": "Role",
        "role_name": "Zatca Role",
    }).insert(ignore_permissions=True)  