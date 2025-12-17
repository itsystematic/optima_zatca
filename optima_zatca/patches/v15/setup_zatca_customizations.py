"""
Migration patch to setup ZATCA customizations with proper validation.
This patch ensures all custom fields, property setters, and roles are created
without errors on sites that already have some configurations.
"""

import frappe
import json
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


ADDRESS_DOCTYPE_FIELDS = [
    "address_title", "address_type", "section_break_123", "short_address", "address_line1", "city", "pincode",
    "column_break_tshas", "building_no", "address_line2", "district", "address_details", "address_name_in_arabic",
    "county", "state", "country", "column_break0", "email_id", "phone", "fax", "tax_category", "is_primary_address",
    "is_shipping_address", "disabled", "linked_with", "is_your_company_address", "links"
]


def execute():
    """Execute the migration patch."""
    frappe.reload_doc("custom", "doctype", "custom_field")
    frappe.reload_doc("custom", "doctype", "property_setter")
    
    try:
        create_custom_fields_with_validation()
        create_property_setters_with_validation()
        add_zatca_roles()
        frappe.db.commit()
        print("✓ ZATCA customizations setup completed successfully")
    except Exception as e:
        frappe.log_error(f"Error in ZATCA customizations setup: {str(e)}", "ZATCA Migration Patch")
        print(f"✗ Error in ZATCA customizations setup: {str(e)}")


def create_custom_fields_with_validation():
    """Create custom fields with validation to check if they already exist."""
    
    selling_child_table_fields = [
        {
            "fieldname": "tax_category",
            "fieldtype": "Link",
            "label": "Tax Category",
            "insert_after": "item_tax_template",
            "options": "Tax Category",
            "read_only": 1,
            "hidden": 1,
        },
        {
            "fieldname": "price_amount",
            "label": "Price Amount",
            "fieldtype": "Float",
            "insert_after": "tax_category",
            "read_only": 1,
            "hidden": 1,
            "no_copy": 1,
        },
        {
            "fieldname": "line_extension_amount",
            "label": "Line Extension Amount",
            "fieldtype": "Float",
            "insert_after": "price_amount",
            "read_only": 1,
            "hidden": 1,
            "no_copy": 1,
        },
        {
            "fieldname": "item_discount",
            "label": "Item Discount",
            "fieldtype": "Float",
            "insert_after": "line_extension_amount",
            "read_only": 1,
            "hidden": 1,
            "no_copy": 1,
        },
        {
            "fieldname": "tax_rate",
            "fieldtype": "Float",
            "label": "Tax Rate",
            "insert_after": "item_discount",
            "read_only": 1,
            "hidden": 1,
        },
        {
            "fieldname": "tax_amount",
            "fieldtype": "Float",
            "label": "Tax Amount",
            "insert_after": "tax_rate",
            "read_only": 1,
            "hidden": 1,
        },
        {
            "fieldname": "total_amount",
            "fieldtype": "Currency",
            "label": "Total Amount",
            "insert_after": "tax_amount",
            "read_only": 1,
            "hidden": 1,
        },
        {
            "fieldname": "tax_exemption",
            "fieldtype": "Link",
            "label": "Tax Exemption",
            "insert_after": "total_amount",
            "options": "Tax Exemption"
        },
    ]
    
    custom_fields_map = {
        "Company": [
            {
                "fieldname": "company_name_in_arabic",
                "fieldtype": "Data",
                "label": "Company Name In Arabic",
                "insert_after": "company_name",
                "description": "This name must match the company name in the government commercial register."
            },
            {
                "fieldname": "section_break87956",
                "fieldtype": "Section Break",
                "insert_after": "company_name_in_arabic",
            }
        ],
        "Address": [
            {
                "fieldname": "section_break_123",
                "fieldtype": "Section Break",
                "label": "Saudi National Address Components",
                "insert_after": "address_type",
            },
            {
                "fieldname": "short_address",
                "fieldtype": "Data",
                "label": "Short Address",
                "insert_after": "section_break_123",
            },
            {
                "fieldname": "building_no",
                "fieldtype": "Data",
                "label": "Building No",
                "insert_after": "column_break_tshas",
            },
            {
                "fieldname": "column_break_tshas",
                "fieldtype": "Column Break",
                "insert_after": "pincode",
            },
            {
                "fieldname": "district",
                "fieldtype": "Data",
                "label": "District",
                "insert_after": "address_line2",
            },
            {
                "fieldname": "address_name_in_arabic",
                "fieldtype": "Data",
                "label": "Address Name In Arabic",
                "insert_after": "address_details",
            },
        ],
        "Branch": [
            {
                "fieldname": "commercial_register",
                "fieldtype": "Link",
                "label": "Commercial Register",
                "insert_after": "branch",
                "options": "Commercial Register",
                "description": "this field should contain the 10-digit"
            }
        ],
        "Sales Invoice": [
            {
                "fieldname": "commercial_register",
                "fieldtype": "Link",
                "label": "Commercial Register",
                "insert_after": "company",
                "options": "Commercial Register",
                "description": "this field should contain the 10-digit",
                "reqd": 1
            },
            {
                "fieldname": "clearance_or_reporting",
                "fieldtype": "Data",
                "label": "Clearance Or Reporting",
                "insert_after": "column_break_14",
                "read_only": 1,
                "no_copy": 1
            },
            {
                "fieldname": "sales_invoice_type",
                "fieldtype": "Link",
                "label": "Sales Invoice Type",
                "insert_after": "clearance_or_reporting",
                "options": "Sales Invoice Type",
                "default": "Normal",
                "reqd": 1
            },
            {
                "fieldname": "reason_for_issuance",
                "fieldtype": "Small Text",
                "label": "Reason For issuance",
                "insert_after": "is_debit_note",
                "depends_on": "eval: doc.is_return || doc.is_debit_note",
                "mandatory_depends_on": "eval: doc.is_return || doc.is_debit_note"
            },
            {
                "fieldname": "ksa_einv_qr",
                "fieldtype": "Attach Image",
                "label": "KSA E-Invoicing QR",
                "insert_after": "reason_for_issuance",
                "read_only": 1,
                "hidden": 1,
                "no_copy": 1
            },
            {
                "fieldname": "section_break89",
                "fieldtype": "Section Break",
                "insert_after": "ksa_einv_qr",
            },
            {
                "fieldname": "sent_to_zatca",
                "fieldtype": "Check",
                "label": "Sent To Zatca",
                "insert_after": "is_discounted",
                "read_only": 1,
                "no_copy": 1
            },
        ],
        "Sales Invoice Item": selling_child_table_fields,
        "Quotation Item": selling_child_table_fields,
        "Sales Order Item": selling_child_table_fields,
        "Delivery Note Item": selling_child_table_fields,
        "POS Invoice Item": selling_child_table_fields,
        "Customer": [
            {
                "fieldname": "registration_type",
                "fieldtype": "Link",
                "label": "Registration Type",
                "insert_after": "tax_id",
                "options": "Registration Type",
                "mandatory_depends_on": "eval: doc.customer_type == 'Company' ",
                "default": "CRN"
            },
            {
                "fieldname": "registration_value",
                "fieldtype": "Data",
                "label": "Registration Value",
                "insert_after": "registration_type",
                "mandatory_depends_on": "eval: doc.customer_type == 'Company' "
            }
        ],
        "Item Tax Template": [
            {
                "fieldname": "tax_category",
                "fieldtype": "Link",
                "label": "Tax Category",
                "insert_after": "company",
                "options": "Tax Category",
            },
        ]
    }
    
    created_count = 0
    skipped_count = 0
    
    for doctype, fields in custom_fields_map.items():
        for field_dict in fields:
            try:
                # Check if custom field already exists
                if custom_field_exists(doctype, field_dict["fieldname"]):
                    print(f"  ⊙ Custom field {doctype}.{field_dict['fieldname']} already exists - skipping")
                    skipped_count += 1
                    continue
                
                # Create the custom field
                field_dict["dt"] = doctype
                create_custom_field(doctype, field_dict)
                created_count += 1
                print(f"  ✓ Created custom field: {doctype}.{field_dict['fieldname']}")
                
            except Exception as e:
                print(f"  ✗ Error creating field {doctype}.{field_dict['fieldname']}: {str(e)}")
                frappe.log_error(
                    f"Error creating custom field {doctype}.{field_dict['fieldname']}: {str(e)}",
                    "ZATCA Custom Field Creation"
                )
    
    print(f"\nCustom Fields Summary: {created_count} created, {skipped_count} skipped")


def custom_field_exists(doctype, fieldname):
    """Check if a custom field already exists."""
    return frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname})


def create_property_setters_with_validation():
    """Create property setters with validation to check if they already exist."""
    
    property_setters = [
        # Address field relabeling
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
            "fieldname": None,
            "property": "field_order",
            "value": json.dumps(ADDRESS_DOCTYPE_FIELDS),
            "property_type": "Data",
        },
        # Sales Invoice discount settings
        {
            "doctype": "Sales Invoice",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "read_only",
            "value": "1",
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
            "fieldname": "disable_rounded_total",
            "property": "default",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Sales Invoice",
            "doctype_or_field": "DocField",
            "fieldname": "disable_rounded_total",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        # Sales Order discount settings
        {
            "doctype": "Sales Order",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "read_only",
            "value": "1",
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
            "fieldname": "disable_rounded_total",
            "property": "default",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Sales Order",
            "doctype_or_field": "DocField",
            "fieldname": "disable_rounded_total",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        # Quotation discount settings
        {
            "doctype": "Quotation",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "read_only",
            "value": "1",
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
            "fieldname": "disable_rounded_total",
            "property": "default",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Quotation",
            "doctype_or_field": "DocField",
            "fieldname": "disable_rounded_total",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        # Delivery Note discount settings
        {
            "doctype": "Delivery Note",
            "doctype_or_field": "DocField",
            "fieldname": "apply_discount_on",
            "property": "read_only",
            "value": "1",
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
            "fieldname": "disable_rounded_total",
            "property": "default",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Delivery Note",
            "doctype_or_field": "DocField",
            "fieldname": "disable_rounded_total",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        # Hide tax fields
        {
            "doctype": "Sales Invoice",
            "doctype_or_field": "DocField",
            "fieldname": "taxes_and_charges",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Sales Invoice",
            "doctype_or_field": "DocField",
            "fieldname": "tax_category",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Sales Order",
            "doctype_or_field": "DocField",
            "fieldname": "taxes_and_charges",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Sales Order",
            "doctype_or_field": "DocField",
            "fieldname": "tax_category",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Quotation",
            "doctype_or_field": "DocField",
            "fieldname": "taxes_and_charges",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Quotation",
            "doctype_or_field": "DocField",
            "fieldname": "tax_category",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Delivery Note",
            "doctype_or_field": "DocField",
            "fieldname": "taxes_and_charges",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Delivery Note",
            "doctype_or_field": "DocField",
            "fieldname": "tax_category",
            "property": "hidden",
            "value": "1",
            "property_type": "Check",
        },
    ]
    
    created_count = 0
    skipped_count = 0
    
    for setter in property_setters:
        try:
            # Check if property setter already exists
            if property_setter_exists(setter):
                skipped_count += 1
                fieldname_display = setter.get("fieldname") or "DocType"
                print(f"  ⊙ Property setter {setter['doctype']}.{fieldname_display}.{setter['property']} already exists - skipping")
                continue
            
            # Create the property setter
            make_property_setter(setter, ignore_validate=True, validate=False)
            created_count += 1
            fieldname_display = setter.get("fieldname") or "DocType"
            print(f"  ✓ Created property setter: {setter['doctype']}.{fieldname_display}.{setter['property']}")
            
        except Exception as e:
            fieldname_display = setter.get("fieldname") or "DocType"
            print(f"  ✗ Error creating property setter {setter['doctype']}.{fieldname_display}.{setter['property']}: {str(e)}")
            frappe.log_error(
                f"Error creating property setter: {str(e)}\nSetter: {setter}",
                "ZATCA Property Setter Creation"
            )
    
    print(f"\nProperty Setters Summary: {created_count} created, {skipped_count} skipped")


def property_setter_exists(setter):
    """Check if a property setter already exists."""
    filters = {
        "doc_type": setter["doctype"],
        "property": setter["property"],
        "doctype_or_field": setter["doctype_or_field"]
    }
    
    if setter.get("fieldname"):
        filters["field_name"] = setter["fieldname"]
    
    return frappe.db.exists("Property Setter", filters)


def add_zatca_roles():
    """Add ZATCA roles if they don't exist."""
    roles_to_add = ["Zatca Role", "Zatca Manager"]
    created_count = 0
    skipped_count = 0
    
    for role in roles_to_add:
        try:
            if frappe.db.exists("Role", role):
                print(f"  ⊙ Role '{role}' already exists - skipping")
                skipped_count += 1
                continue
            
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role,
            }).insert(ignore_permissions=True)
            
            created_count += 1
            print(f"  ✓ Created role: {role}")
            
        except Exception as e:
            print(f"  ✗ Error creating role '{role}': {str(e)}")
            frappe.log_error(f"Error creating ZATCA role '{role}': {str(e)}", "ZATCA Role Creation")
    
    print(f"\nRoles Summary: {created_count} created, {skipped_count} skipped")
