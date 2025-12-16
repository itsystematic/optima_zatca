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
def get_vat_ledger_data(company=None, from_date=None, to_date=None, tax_account=None, party=None):
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
    data = get_vat_data(company, from_date, to_date, accounts, party)
    
    # Process data
    final_data, summary, doctypes = make_group_by_type(data)
    report_summary, values = get_report_summary(data, summary)
    chart_data = prepare_chart_data(doctypes, values)
    
    # Ensure area chart data is always generated
    try:
        area_chart_data = prepare_area_chart_data(data, from_date, to_date)
    except Exception as e:
        frappe.log_error(f"Error preparing area chart data: {str(e)}")
        area_chart_data = {"labels": [], "datasets": []}
    
    return {
        "data": final_data,
        "summary": report_summary,
        "chart_data": chart_data,
        "area_chart_data": area_chart_data
    }


def get_vat_data(company, from_date, to_date, accounts, party=None):
    """Fetch VAT data from database"""
    
    if not accounts:
        return []
    
    party_condition = ""
    if party:
        party_condition = """
            AND (
                (gl.voucher_type = 'Sales Invoice' AND t1.customer LIKE %(party)s)
                OR (gl.voucher_type = 'Purchase Invoice' AND t2.supplier LIKE %(party)s)
                OR gl.party LIKE %(party)s
            )
        """
    
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
            {party_condition}
            
        ORDER BY gl.voucher_type, gl.posting_date DESC
    """.format(party_condition=party_condition), {
        "from_date": from_date,
        "to_date": to_date,
        "company": company,
        "accounts": accounts,
        "party": f"%{party}%" if party else ""
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


def prepare_area_chart_data(data, from_date, to_date):
    """Prepare cumulative area chart data by day with separate lines for Sales and Purchase"""
    from datetime import timedelta
    from frappe.utils import getdate, flt
    
    if not data or not from_date or not to_date:
        return {"labels": [], "datasets": []}
    
    try:
        # Parse dates
        start_date = getdate(from_date)
        end_date = getdate(to_date)
        
        # Create dictionaries to store daily amounts by type
        daily_sales = {}
        daily_purchase = {}
        current_date = start_date
        
        # Initialize all dates with 0
        while current_date <= end_date:
            daily_sales[current_date] = 0.0
            daily_purchase[current_date] = 0.0
            current_date += timedelta(days=1)
        
        # Aggregate amounts by posting date and type
        for row in data:
            try:
                posting_date = getdate(row.get("posting_date"))
                if start_date <= posting_date <= end_date:
                    # Use flt to ensure proper float conversion and handle None
                    amount = flt(row.get("base_tax_amount", 0), 2)
                    voucher_type = row.get("parenttype")
                    
                    if voucher_type == "Sales Invoice":
                        daily_sales[posting_date] = flt(daily_sales[posting_date], 2) + amount
                    elif voucher_type == "Purchase Invoice":
                        daily_purchase[posting_date] = flt(daily_purchase[posting_date], 2) + amount
            except Exception as row_error:
                frappe.log_error(f"Error processing row: {str(row_error)}")
                continue
        
        # Sort dates and calculate cumulative values
        sorted_dates = sorted(daily_sales.keys())
        labels = []
        cumulative_sales = []
        cumulative_purchase = []
        cumulative_total = []
        
        sales_sum = 0.0
        purchase_sum = 0.0
        
        for date in sorted_dates:
            # Use flt to ensure proper float handling
            sales_sum = flt(sales_sum, 2) + flt(daily_sales[date], 2)
            purchase_sum = flt(purchase_sum, 2) + flt(daily_purchase[date], 2)
            
            labels.append(date.strftime("%d %b"))  # Format: "16 Dec"
            cumulative_sales.append(round(sales_sum, 2))
            cumulative_purchase.append(round(purchase_sum, 2))
            cumulative_total.append(round(sales_sum + purchase_sum, 2))
        
        # Ensure we have data
        if not labels:
            return {"labels": [], "datasets": []}
        
        # Validate all values are numbers
        for i, val in enumerate(cumulative_sales):
            if val is None or not isinstance(val, (int, float)):
                cumulative_sales[i] = 0.0
        for i, val in enumerate(cumulative_purchase):
            if val is None or not isinstance(val, (int, float)):
                cumulative_purchase[i] = 0.0
        for i, val in enumerate(cumulative_total):
            if val is None or not isinstance(val, (int, float)):
                cumulative_total[i] = 0.0
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "name": "Sales Invoice",
                    "values": cumulative_sales
                },
                {
                    "name": "Purchase Invoice",
                    "values": cumulative_purchase
                },
                {
                    "name": "Total",
                    "values": cumulative_total
                }
            ]
        }
    except Exception as e:
        frappe.log_error(f"Error in prepare_area_chart_data: {str(e)}")
        return {"labels": [], "datasets": []}
