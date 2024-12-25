// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on("Optima Zatca Logs", {
	refresh(frm) {
        frm.disable_form() ;
		frm.trigger("add_zatca_button") ;
	},

	add_zatca_button(frm) {
		frm.add_custom_button(__("Show Xml"), function () {
			// const decodedString = atob(base64String);
			let d = new frappe.ui.Dialog({
				title: 'Enter details',
				fields: [
					{
						label: 'Invoice',
						fieldname: 'invoice',
						fieldtype: 'Text',
						default : atob(frm.doc.invoice),
						// read_only: 1
					},

				],
				size: 'extra-large', // small, large, extra-large 
				primary_action_label: 'Skip',
				primary_action(values) {
					// console.log(values);
					d.hide();
				}
			});
			
			d.show();
			
						
		});
	}
});
