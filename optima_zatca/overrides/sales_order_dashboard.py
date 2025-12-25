from frappe import _


def get_data(data):
    """Override Sales Order dashboard to add prepayment_sales_order link"""
    # Add our custom fieldname for advance sales invoices
    if not data.get('non_standard_fieldnames'):
        data['non_standard_fieldnames'] = {}
    
    # Add prepayment_sales_order to non_standard_fieldnames
    # This tells ERPNext that Sales Invoices can also be linked via prepayment_sales_order field
    data['non_standard_fieldnames']['Sales Invoice'] = 'prepayment_sales_order'
    
    return data
