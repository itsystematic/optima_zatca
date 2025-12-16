import frappe
from frappe import _

@frappe.whitelist()
def get_tax_accounts(company):
    """Get all tax accounts for the selected company"""
    if not company:
        return []
    
    ksa_vat_settings = frappe.db.get_value("Zatca VAT Setting", {"company": company}, "name")
    
    if not ksa_vat_settings:
        return []
    
    accounts = (
        frappe.db.get_all("Zatca VAT Sales Account", {"parent": ksa_vat_settings}, pluck="account") + 
        frappe.db.get_all("Zatca VAT Purchase Account", {"parent": ksa_vat_settings}, pluck="account")
    )
    
    return list(set(accounts))


@frappe.whitelist()
def get_vat_ledger_data(company=None, from_date=None, to_date=None, tax_account=None):
    """Get VAT ledger data based on filters"""
    
    if not company:
        frappe.throw(_("Company is required"))
    
    if not from_date or not to_date:
        frappe.throw(_("Date range is required"))
    
    # Get accounts
    accounts = get_tax_accounts(company)
    
    if not accounts:
        return {
            "data": [],
            "summary": [],
            "chart_data": {"labels": [], "values": []}
        }
    
    # If specific tax account is selected, filter to that account only
    if tax_account:
        accounts = [tax_account]
    
    # Get data
    data = get_vat_data(company, from_date, to_date, accounts)
    
    # Process data
    final_data, summary, doctypes = make_group_by_type(data)
    report_summary, values = get_report_summary(data, summary)
    chart_data = prepare_chart_data(doctypes, values)
    
    return {
        "data": final_data,
        "summary": report_summary,
        "chart_data": chart_data
    }


def get_vat_data(company, from_date, to_date, accounts):
    """Fetch VAT data from database"""
    
    if not accounts:
        return []
    
    sql_query = frappe.db.sql("""
        SELECT 
            gl.voucher_no as name,
            gl.account as tax_account,
            gl.debit - gl.credit as base_tax_amount,
            gl.voucher_type as parenttype,
            gl.against_voucher,
            gl.against_voucher_type,
            gl.credit,
            gl.debit,
            gl.company,
            gl.posting_date,
            
            CASE 
                WHEN gl.voucher_type = 'Sales Invoice' THEN t1.customer
                WHEN gl.voucher_type = 'Purchase Invoice' THEN t2.supplier
                ELSE gl.party
            END as party,
            
            CASE 
                WHEN gl.voucher_type = 'Sales Invoice' THEN 'Customer'
                WHEN gl.voucher_type = 'Purchase Invoice' THEN 'Supplier'
                ELSE gl.party_type
            END as party_type,
            
            CASE 
                WHEN gl.voucher_type = 'Sales Invoice' THEN t1.tax_id
                WHEN gl.voucher_type = 'Purchase Invoice' THEN t2.tax_id
                WHEN gl.voucher_type = 'Journal Entry' THEN ( 
                    SELECT custom_party_tax_id FROM `tabJournal Entry Account` 
                    WHERE account = gl.account 
                        AND gl.party = party 
                        AND parent = gl.voucher_no 
                    LIMIT 1
                )
                ELSE ""
            END as tax_id,
            
            CASE 
                WHEN gl.voucher_type = 'Sales Invoice' THEN t1.base_net_total
                WHEN gl.voucher_type = 'Purchase Invoice' THEN t2.base_net_total
                ELSE 0
            END as base_net_amount,
            
            CASE 
                WHEN gl.voucher_type = 'Sales Invoice' THEN t1.grand_total
                WHEN gl.voucher_type = 'Purchase Invoice' THEN t2.grand_total
                ELSE 0
            END as grand_total
            
        FROM `tabGL Entry` as gl
        
        LEFT JOIN ( 
            SELECT 
                si.name, si.company, si.base_net_total, si.grand_total, si.total_taxes_and_charges,
                si.customer, c.tax_id 
            FROM `tabSales Invoice` as si 
            LEFT JOIN `tabCustomer` as c 
                ON c.name = si.customer
        ) as t1 ON t1.name = gl.voucher_no AND t1.company = gl.company AND gl.voucher_type = 'Sales Invoice'
        
        LEFT JOIN (
            SELECT 
                pi.name, pi.company, pi.base_net_total, pi.grand_total, pi.total_taxes_and_charges,
                pi.supplier, s.tax_id 
            FROM `tabPurchase Invoice` as pi 
            LEFT JOIN `tabSupplier` as s 
                ON s.name = pi.supplier
        ) t2 ON t2.name = gl.voucher_no AND t2.company = gl.company AND gl.voucher_type = 'Purchase Invoice'
        
        WHERE 
            gl.is_cancelled = 0 
            AND gl.account IN %(accounts)s
            AND gl.voucher_type IN ('Sales Invoice', 'Purchase Invoice')
            AND gl.company = %(company)s
            AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
            
        ORDER BY gl.voucher_type, gl.posting_date DESC
    """, {
        "from_date": from_date,
        "to_date": to_date,
        "company": company,
        "accounts": accounts
    }, as_dict=True)
    
    return sql_query


def make_group_by_type(data):
    """Group data by voucher type"""
    
    final_result = []
    report_summary = []
    types = list(set(map(lambda x: x.get("parenttype"), data)))
    
    for type in types:
        filtered_data = list(filter(lambda x: x.get("parenttype") == type, data))
        if filtered_data:
            filtered_value = sum(map(lambda x: x.get("base_tax_amount", 0), filtered_data))
            final_result.append({
                "name": "<h5 style='text-align:center; font-weight:bold; color:#9B3922'>{0}</h5>".format(type)
            })
            final_result += filtered_data
            final_result.append({
                "name": "<h5 style='font-weight:bold; text-align:center; color:#C80036'>Total</h5>",
                "base_tax_amount": filtered_value
            })
            final_result.append({})
            report_summary.append({
                "doctype": type,
                "total": filtered_value
            })
    
    return final_result, report_summary, types


def get_report_summary(data, summary):
    """Generate report summary"""
    
    result = []
    values = []
    
    for fields in summary:
        result.append({
            "label": _(fields.get("doctype")),
            "value": fields.get("total"),
            "indicator": "green" if fields.get("total") > 0 else "red"
        })
        values.append(fields.get("total"))
    
    total_value = sum(map(lambda x: x.get("base_tax_amount", 0), data))
    
    result.append({
        "label": _("Total"),
        "value": total_value,
        "indicator": "green" if total_value > 0 else "red"
    })
    
    return result, values


def prepare_chart_data(doctypes, values):
    """Prepare chart data"""
    
    values = list(map(lambda x: abs(x), values))
    
    return {
        "labels": doctypes,
        "values": values
    }
