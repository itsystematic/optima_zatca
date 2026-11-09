// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.listview_settings["Optima Zatca Setting"] = {
	add_fields: ["check_pcsid"],

	environments: {
		production: { label: "Production", theme: "blue" },
		simulation: { label: "Simulation", theme: "violet" },
		sandbox: { label: "Sandbox", theme: "amber" },
	},

	get_indicator(doc) {
		return doc.check_pcsid
			? [__("Connected"), "green", "check_pcsid,=,1"]
			: [__("Not Connected"), "red", "check_pcsid,=,0"];
	},

	formatters: {
		api_endpoints(value) {
			const environment = frappe.listview_settings["Optima Zatca Setting"].environments[value];
			if (!environment) return frappe.utils.escape_html(value || "");
			// "Production" alone is ERPNext's manufacturing term; the onboarding context is ZATCA's.
			return frappe.ui.badge.html({
				label: __(environment.label, null, "onboarding"),
				theme: environment.theme,
				css_class: "filterable",
				attrs: { "data-filter": `api_endpoints,=,${value}` },
			});
		},
	},
};
