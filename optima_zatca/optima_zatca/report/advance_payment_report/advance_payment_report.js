// Copyright (c) 2026, IT Systematic and contributors
// For license information, please see license.txt

// Each timespan is a unit and how many of them it starts and ends from today, matching Frappe's own
// get_timespan_date_range: Last 6 Months is the two whole quarters before this one, not 180 days back.
const TIMESPANS = {
	"Last Week": ["week", -1],
	"Last Month": ["month", -1],
	"Last Quarter": ["quarter", -1],
	"Last 6 Months": ["quarter", -2, -1],
	"Last Year": ["year", -1],
	Yesterday: ["day", -1],
	Today: ["day", 0],
	Tomorrow: ["day", 1],
	"This Week": ["week", 0],
	"This Month": ["month", 0],
	"This Quarter": ["quarter", 0],
	"This Year": ["year", 0],
};

function timespan_range(timespan) {
	if (!TIMESPANS[timespan]) return null;
	const [unit, start, end = start] = TIMESPANS[timespan];
	const today = moment(frappe.datetime.get_today());
	return {
		from_date: today.clone().add(start, unit).startOf(unit).format("YYYY-MM-DD"),
		to_date: today.clone().add(end, unit).endOf(unit).format("YYYY-MM-DD"),
	};
}

// A filter's on_change replaces the report's own refresh, so it refreshes here. Each date checks only
// its own bound, so a timespan filling both dates never finds them half-set and clears itself.
function on_date_change(fieldname) {
	return (report) => {
		const range = timespan_range(report.get_filter_value("timespan"));
		if (range && range[fieldname] !== report.get_filter_value(fieldname)) {
			report.set_filter_value("timespan", "");
		}
		report.refresh(true);
	};
}

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
			fieldname: "timespan",
			label: __("Timespan"),
			fieldtype: "Select",
			options: ["", ...Object.keys(TIMESPANS)],
			on_change(report) {
				const range = timespan_range(report.get_filter_value("timespan"));
				if (range) report.set_filter_value(range);
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
			on_change: on_date_change("from_date"),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			on_change: on_date_change("to_date"),
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
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Open", "Closed"],
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
	onload() {
		// The formatter only reaches a cell's content, so row-wide styles are set on the row it sits in.
		// Rows before From Date fade rather than turn grey: a link keeps its own colour, and grey is
		// already the chain row's tint.
		frappe.dom.set_style(
			`.dt-row:has(.advance-chain-row) .dt-cell { background-color: var(--subtle-fg); }
			.advance-chain-row { font-weight: var(--weight-semibold); }
			.dt-row:has(.advance-before-period) .dt-cell__content { opacity: 0.45; }`,
			"advance-payment-report"
		);
	},
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
		if (data.indent === 0) {
			value = `<span class="advance-chain-row">${value}</span>`;
		}
		if (data.out_of_range) {
			value = `<span class="advance-before-period">${value}</span>`;
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
