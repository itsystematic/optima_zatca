# Copyright (c) 2025, IT Systematic and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = [
        {
            "fieldname": "success",
            "label": "Success",
            "fieldtype": "Int",
            "width": 150
        },
        {
            "fieldname": "failed",
            "label": "Failed",
            "fieldtype": "Int",
            "width": 150
        },
        {
            "fieldname": "warning",
            "label": "Warning",
            "fieldtype": "Int",
            "width": 150
        },
        {
            "fieldname": "accepted",
            "label": "Accepted",
            "fieldtype": "Int",
            "width": 150
        }
    ]

    data = frappe.db.sql("""
    SELECT
                    
    SUM(CASE WHEN z.status = 'Success' THEN 1 ELSE 0 END) AS success,
    SUM(CASE WHEN z.status = 'Warning' THEN 1 ELSE 0 END) AS warning,
    SUM(CASE WHEN z.status IN ('Success', 'Warning') THEN 1 ELSE 0 END) AS accepted,
    SUM(CASE WHEN z.status = 'Failed' THEN 1 ELSE 0 END) AS failed
                    
    FROM `tabOptima Zatca Logs` z
    INNER JOIN (
        SELECT 
            reference_name, 
            MAX(modified) AS max_modified
        FROM `tabOptima Zatca Logs` 
        GROUP BY reference_name
    ) latest 
        ON z.reference_name = latest.reference_name 
        AND z.modified = latest.max_modified
    """, as_dict=1)

    pie_chart = {
        "data": {
            'labels': ["Failed", "Accepted"],
            'datasets': [
                {
                    'name': 'Status Count',
                    'values': [data[0]['failed'], data[0]['accepted']]
                }
            ]
        },
        "type": "pie",
        "height": 300,
        "colors": ["#4CAF50", "#FF9800", "#F44336"],
        "title": "ZATCA Status Distribution"
    }

    return columns, data, None, pie_chart
