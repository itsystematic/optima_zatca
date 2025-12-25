# optima_zatca/optima_zatca/print_format/sales_invoice_controller.py

import frappe
from frappe import _

@frappe.whitelist()
def get_context(doc):
    """
    Prepares all data needed for the Sales Invoice print format.
    This moves database queries out of the Jinja template for better performance.
    """
    context = frappe._dict()
    
    # Get customer tax info
    customer_data = frappe.db.get_value(
        'Customer', 
        doc.customer, 
        ['tax_id', 'registration_value', 'customer_name'],
        as_dict=True
    ) or {}
    
    context.customer_tax_id = customer_data.get('tax_id', '')
    context.customer_cr_number = customer_data.get('registration_value', '')
    
    # Determine invoice type
    context.invoice_type = get_invoice_type(
        customer_data.get('tax_id'),
        doc.is_return
    )
    
    # Get company details
    context.company = frappe.get_cached_doc("Company", doc.company)
    
    # Get addresses
    context.seller_address = get_address_details(doc.company_address)
    context.customer_address = get_address_details(doc.customer_address)
    
    # Get payment information
    if doc.status in ['Paid', 'Partly Paid']:
        context.payments = get_payment_details(doc.doctype, doc.name)
    else:
        context.payments = []
    
    # Get bank details from Company or custom settings
    context.bank_details = get_bank_details(doc.company)
    
    # Get VAT rate from Tax Template or settings
    context.vat_rate = get_vat_rate(doc)
    
    return context


def get_invoice_type(customer_tax_id, is_return):
    """
    Determines the invoice type based on customer tax ID and return status.
    Returns a dict with English and Arabic titles.
    """
    is_standard = customer_tax_id and len(str(customer_tax_id)) == 15
    
    invoice_types = {
        (True, False): {
            'en': _('Tax Invoice'),
            'ar': 'فاتورة ضريبية'
        },
        (True, True): {
            'en': _('Credit Note'),
            'ar': 'اشعار دائن مرتجع'
        },
        (False, False): {
            'en': _('Simplified Tax Invoice'),
            'ar': 'فاتورة ضريبية مبسطة'
        },
        (False, True): {
            'en': _('Simplified Credit Note'),
            'ar': 'فاتورة مرتجع مبسطة'
        }
    }
    
    return invoice_types.get((is_standard, bool(is_return)))


def get_address_details(address_name):
    """
    Fetches address details if address exists.
    Returns empty dict if no address.
    """
    if not address_name:
        return frappe._dict()
    
    try:
        return frappe.get_cached_doc('Address', address_name)
    except frappe.DoesNotExistError:
        return frappe._dict()


def get_payment_details(reference_doctype, reference_name):
    """
    Collects all payment information for the invoice.
    Combines Payment Entry and Journal Entry references.
    """
    payments = []
    
    # Get Payment Entry References
    payment_refs = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "docstatus": 1
        },
        fields=["parent", "allocated_amount"]
    )
    
    if payment_refs:
        parent_names = [ref.parent for ref in payment_refs]
        payment_entries = frappe.get_all(
            "Payment Entry",
            filters={"name": ["in", parent_names]},
            fields=["name", "posting_date", "mode_of_payment"]
        )
        
        pe_map = {pe.name: pe for pe in payment_entries}
        
        for ref in payment_refs:
            pe = pe_map.get(ref.parent, {})
            payments.append({
                "name": ref.parent,
                "posting_date": pe.get("posting_date"),
                "mode_of_payment": pe.get("mode_of_payment", ""),
                "allocated_amount": ref.allocated_amount
            })
    
    # Get Journal Entry References
    journal_refs = frappe.get_all(
        "Journal Entry Account",
        filters={
            "reference_type": reference_doctype,
            "reference_name": reference_name,
            "docstatus": 1
        },
        fields=["parent", "credit_in_account_currency", "debit_in_account_currency"]
    )
    
    if journal_refs:
        parent_names = [ref.parent for ref in journal_refs]
        journal_entries = frappe.get_all(
            "Journal Entry",
            filters={"name": ["in", parent_names]},
            fields=["name", "posting_date", "mode_of_payment"]
        )
        
        je_map = {je.name: je for je in journal_entries}
        
        for ref in journal_refs:
            je = je_map.get(ref.parent, {})
            allocated = ref.credit_in_account_currency or ref.debit_in_account_currency
            payments.append({
                "name": ref.parent,
                "posting_date": je.get("posting_date"),
                "mode_of_payment": je.get("mode_of_payment", ""),
                "allocated_amount": allocated
            })
    
    return payments


def get_bank_details(company_name):
    """
    Fetches bank details from company settings or custom doctype.
    """
    # You can create a custom doctype for bank details or use Company fields
    try:
        bank_details = frappe.db.get_value(
            'Company',
            company_name,
            [
                'bank_name',
                'bank_branch_no', 
                'bank_branch_name',
                'bank_id_number',
                'bank_account_number',
                'bank_iban'
            ],
            as_dict=True
        )
    except Exception:
        bank_details = {}
    
    # Fallback to default values if not configured
    return {
        'bank_name': bank_details.get('bank_name', ''),
        'branch_no': bank_details.get('bank_branch_no', ''),
        'branch_name': bank_details.get('bank_branch_name', ''),
        'id_number': bank_details.get('bank_id_number', ''),
        'account_number': bank_details.get('bank_account_number', ''),
        'iban': bank_details.get('bank_iban', '')
    }


def get_vat_rate(doc):
    """
    Gets the VAT rate from the document's tax template.
    """
    for tax in doc.taxes:
        if 'VAT' in (tax.description or '').upper():
            return tax.rate or 15
    return 15