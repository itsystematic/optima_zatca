// Copyright (c) 2026, IT Systematic and contributors
// For license information, please see license.txt

frappe.query_reports["Advance Payment Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "approach",
			label: __("Approach"),
			fieldtype: "Select",
			options: ["Full Chain", "Prepayment", "Adjustment", "Single Type"],
			default: "Full Chain",
			reqd: 1,
		},
		{
			fieldname: "invoice_type",
			label: __("Invoice Type"),
			fieldtype: "Link",
			options: "Sales Invoice Type",
			depends_on: "eval: doc.approach == 'Single Type'",
			get_query: () => ({ filters: { name: ["!=", "Normal"] } }),
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
		},
		{
			fieldname: "sales_order",
			label: __("Sales Order"),
			fieldtype: "Link",
			options: "Sales Order",
			get_query: () => {
				const filters = { company: frappe.query_report.get_filter_value("company"), docstatus: 1 };
				const customer = frappe.query_report.get_filter_value("customer");
				if (customer) filters.customer = customer;
				return { filters };
			},
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
			get_query: () => ({
				filters: { company: frappe.query_report.get_filter_value("company") },
			}),
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
			get_query: () => ({
				filters: { company: frappe.query_report.get_filter_value("company") },
			}),
		},
		{
			fieldname: "currency",
			label: __("Currency"),
			fieldtype: "Link",
			options: "Currency",
		},
	],
	tree: true,
	name_field: "invoice",
	parent_field: "parent_chain",
	initial_depth: 1,
	formatter(value, row, column, data, default_formatter) {
		if (!data) return default_formatter(value, row, column, data);

		const raw = data[column.fieldname];
		if (["Currency", "Float", "Percent"].includes(column.fieldtype) && raw < 0) {
			value = this.parenthesize(default_formatter(-raw, row, column, data));
		} else {
			value = default_formatter(value, row, column, data);
		}

		if (column.fieldname === "status" && data.status_indicator) {
			value = `<span class="indicator-pill ${data.status_indicator}">${value}</span>`;
		}
		if (column.fieldname === "flags" && data.flags) {
			value = `<span class="text-danger">${value}</span>`;
		}
		if (data.indent === 0) {
			value = `<span style="font-weight: bold">${value}</span>`;
		}
		if (data.out_of_range) {
			value = `<span class="text-muted">${value}</span>`;
		}
		return value;
	},
	// Puts a formatted amount in parentheses inside the alignment wrapper the formatter returns.
	parenthesize(html) {
		const $wrapper = $("<div>").html(html);
		const $target = $wrapper.children().length ? $wrapper.children().last() : $wrapper;
		$target.text(`(${$target.text()})`);
		return $wrapper.html();
	},
};
