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
        }
    ]

	# SQL Query to fetch the data in one command
	data = frappe.db.sql("""
		SELECT
			SUM(CASE WHEN status IN ('Success', 'Warning') THEN 1 ELSE 0 END) AS success,
			SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) AS failed
		FROM `tabOptima Zatca Logs`
	""", as_dict=1)

	# Prepare chart data
	pie_chart = {
        "data": {
            'labels': ["Success", "Failed"],
            'datasets': [
                {
                    'name': 'Status Count',
                    'values': [data[0]['success'], data[0]['failed']]
                }
            ]
        },
        "type": "pie",
        "height": 300,
        "colors": ["#4CAF50", "#F44336"],
        "title": "Status Distribution"
    }
	return columns, data, None, pie_chart