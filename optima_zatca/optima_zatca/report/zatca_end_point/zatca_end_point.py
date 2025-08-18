# Copyright (c) 2025, IT Systematic and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns = [
        {
            "fieldname": "cleared",
			"label": "Cleared",
            "fieldtype": "Int",
            "width": 150
        },
        {
            "fieldname": "reported",
            "label": "Reported",
            "fieldtype": "Int",
            "width": 150
        }
    ]

	# SQL Query to fetch the data in one command
	data = frappe.db.sql("""
		SELECT
			SUM(CASE WHEN api_endpoint IN ('reporting', 'reported') THEN 1 ELSE 0 END) AS reported,
			SUM(CASE WHEN api_endpoint IN ('clearance','cleared') THEN 1 ELSE 0 END) AS cleared
		FROM `tabOptima Zatca Logs`
		WHERE status != 'Failed'
	""", as_dict=1)

	# Prepare chart data
	pie_chart = {
        "data": {
            'labels': ["Reported" ,"Cleared"],
            'datasets': [
                {
                    'name': 'End Point Count',
                    'values': [data[0]['reported'], data[0]['cleared']]
                }
            ]
        },
        "type": "pie",
        "height": 300,
        "colors": ["#4CAF50", "#F44336"],
        "title": "End Point Distribution"
    }
	return columns, data, None, pie_chart
