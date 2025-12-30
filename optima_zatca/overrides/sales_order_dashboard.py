from frappe import _


def get_data(data):
    """Override Sales Order dashboard to add Advance Invoices section"""
    # Add a new transaction section for Advance Invoices
    if not data.get('transactions'):
        data['transactions'] = []
    
    # Add Advance Invoices section
    data['transactions'].append({
        'label': _('Advance Invoices chain'),
        'items': ['Prepayment Invoice']
    })
    
    return data
