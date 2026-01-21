// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on("Zatca Main Settings", {
	onload(frm) {
        frm.set_query("print_format", function() {
            return {
                filters: {
                    doc_type: "Sales Invoice"
                }
            };
        });
	},
});
