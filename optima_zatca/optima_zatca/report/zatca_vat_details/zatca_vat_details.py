# # Copyright (c) 2024, IT Systematic and contributors
# # For license information, please see license.txt

import frappe 
from frappe import _

def execute(filters=None):
    
    accounts = get_accounts(filters)
    
    if not accounts :
        return [] , []
    
    columns = get_columns()
    data = get_data(filters , accounts)
    final_data  , summary , doctypes  = make_group_by_type(data)
    report_summary  , values = get_report_summary(filters , data , summary )
    charts = prepare_chart_data(doctypes , values)
    # print(final_data)
    
    return columns, final_data, None, charts, report_summary

def get_columns() -> list:
    return [
        {
            "fieldname": "name",
            "label": _("Name"),
            "fieldtype": "Dynamic Link",
            "options": "parenttype",
            "width": 250,
        },
        {
            "fieldname": "posting_date",
            "label": _("Posting Date"),
            "fieldtype": "Date",
            "width": 130,
        },
        {"label": _("Voucher Type"), "fieldname": "parenttype", "width": 180},
        {
            "fieldname": "tax_account",
            "label": _("Tax Account"),
            "fieldtype": "Link",
            "options": "Account",
            "width": 200,
        },
        {
            "fieldname": "tax_id",
            "label": _("Tax ID"),
            "fieldtype": "Data",
            "width": 180,
        },

        {"label": _("Party Type"), "fieldname": "party_type", "width": 150},
        {"label": _("Party"), "fieldname": "party", "width": 200},

        {
            "fieldname": "base_tax_amount",
            "label": _("Tax Amount"),
            "fieldtype": "Currency",
            "width": 150,
        },

    ]


def get_accounts(filters):
    
    if filters.get("company") :
        
        ksa_vat_settings = frappe.db.get_value("Zatca VAT Setting" ,{"company": filters.get("company")} , "name")
        accounts = (
            frappe.db.get_all("Zatca VAT Sales Account" ,{"parent": ksa_vat_settings}, pluck="account") + 
            frappe.db.get_all("Zatca VAT Purchase Account" ,{"parent": ksa_vat_settings}, pluck="account")
        )
        
        return list(set(accounts))


def get_data(filters=None , accounts:list=None) -> list :
    
    if not accounts :
        return []
    
    conditions = ""
    
    if filters.get("company") :
        conditions += "AND gl.company = %(company)s "
        
    if filters.get("from_date") and filters.get("to_date"):
        conditions += "AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s "
        
    if filters.get("tax_account") :
        accounts = [filters.get("tax_account")]
        

    
    sql_query = frappe.db.sql("""
        SELECT 
            gl.voucher_no as name , gl.account as tax_account , gl.debit - gl.credit as base_tax_amount ,
            gl.voucher_type  as parenttype , gl.against_voucher ,
            gl.against_voucher_type , gl.credit , gl.debit , gl.company , gl.posting_date ,
            
            CASE 
                WHEN gl.voucher_type = 'Sales Invoice' THEN t1.customer
                WHEN gl.voucher_type = 'Purchase Invoice' THEN t2.supplier
                ELSE gl.party
            
            END as party ,
            
            CASE 
                WHEN gl.voucher_type = 'Sales Invoice' THEN 'Customer'
                WHEN gl.voucher_type = 'Purchase Invoice' THEN 'Supplier'
                ELSE gl.party_type
            
            END as party_type ,
            
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
            
            END as tax_id  ,
            
            CASE 
                WHEN gl.voucher_type = 'Sales Invoice' THEN t1.base_net_total
                WHEN gl.voucher_type = 'Purchase Invoice' THEN t2.base_net_total
                ELSE 0
            
            END as base_net_amount ,
            
            CASE 
                WHEN gl.voucher_type = 'Sales Invoice' THEN t1.grand_total
                WHEN gl.voucher_type = 'Purchase Invoice' THEN t2.grand_total
                ELSE 0
            
            END as grand_total 
            
        FROM `tabGL Entry` as gl
        
        LEFT JOIN ( 
            SELECT 
            
                si.name , si.company , si.base_net_total , si.grand_total , si.total_taxes_and_charges ,
                si.customer , c.tax_id 
                
            FROM `tabSales Invoice` as si 
            LEFT JOIN `tabCustomer` as c 
                ON c.name = si.customer
            
        ) as t1 ON t1.name = gl.voucher_no AND t1.company = gl.company AND gl.voucher_type = 'Sales Invoice'
        
        
        LEFT JOIN  (
            SELECT 
                pi.name , pi.company , pi.base_net_total , pi.grand_total , pi.total_taxes_and_charges ,
                pi.supplier , s.tax_id 
                
            FROM `tabPurchase Invoice` as pi 
            LEFT JOIN `tabSupplier` as s 
                ON s.name = pi.supplier
        ) t2 ON t2.name = gl.voucher_no AND t2.company = gl.company AND gl.voucher_type = 'Purchase Invoice'
        
        WHERE 
            gl.is_cancelled = 0 
            AND gl.account IN %(accounts)s
            AND gl.voucher_type IN ('Sales Invoice', 'Purchase Invoice')
            {conditions}
            
        ORDER BY gl.voucher_type , gl.posting_date DESC ;
        
    """.format(conditions=conditions),{
        "from_date" : filters.get("from_date"),
        "to_date" : filters.get("to_date") ,
        "company" : filters.get("company") ,
        "accounts" : accounts
    
    } ,as_dict=True)
    
    # print(sql_query)
    return sql_query




def make_group_by_type(data:list[dict] = None) -> list[dict] :
    
    FinalResult = []
    ReportSummary = []
    # types = ["Sales Invoice" , "Purchase Invoice" , "Journal Entry" , "Payment Entry"]
    types = list(set(map(lambda x : x.get("parenttype") , data)))
    
    for type in types :
        filtered_data = list(filter(lambda x : x.get("parenttype") == type , data))
        if filtered_data :
            FilteredValue =  sum(map(lambda x : x.get("base_tax_amount" , 0) , filtered_data))
            FinalResult.append({"name" : "<h5 style='text-align:center; font-weight:bold; color:#9B3922'>{0}</h5>".format(type)})
            FinalResult += filtered_data
            FinalResult.append({
                "name": "<h5 style='font-weight:bold; text-align:center; color:#C80036'>Total</h5>" ,
                "base_tax_amount" : FilteredValue
            })
            FinalResult.append({})
            ReportSummary.append({
                "doctype" : type,
                "total" : FilteredValue
            })
        
    return FinalResult , ReportSummary , types 



def get_report_summary(filters:dict = None , data:list[dict] = None , summary:list[dict] = []) -> list[dict] :
    
    Result = []
    Values = []
    for fields in summary :
        Result.append(
            {
                # "label" : "<h4 style='text-align:center; font-weight:bold;color:#686D76'>{0}</h4>".format(fields.get("doctype")),
                "label" : _(fields.get("doctype")) ,
                "value" : fields.get("total"),
                "type" : "Currency",
                "fieldname" : "base_tax_amount",
                "bold" : True,
                "indicator" : "green" if fields.get("total") >  0 else "red",
                "datatype" : "Currency"
            }
        )
        Values.append(fields.get("total"))
        
    value = sum(map(lambda x : x.get("base_tax_amount" , 0) , data))
    
    Result.append(
        {
            # "label" : "<h4 style='text-align:center; font-weight:bold;color:#686D76'>{0}</h4>".format(_("Balance")) ,
            "label" : _("Total") ,
            "value" : value,
            "type" : "Currency",
            "fieldname" : "base_tax_amount",
            "bold" : True,
            "indicator" : "green" if value >  0 else "red",
            "datatype" : "Currency"
        }
    )
    
    
    return Result , Values




def prepare_chart_data(doctypes, values:list):
    
    # doctypes_values = list(map(lambda x : x.get("total") , values))
    values = list(map(lambda x : abs(x), values))
    return {
        "data": {"labels": doctypes, "datasets": [{"values": values }]},
        "type": "donut",
        "colors": ["#3AA6B9" ,"#FFD0D0" , "#FF9EAA"]
    }
