// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on("Optima Zatca Setting", {
    onload(frm) {
        frappe.realtime.on("zatca", (data) => {
            frappe.show_alert({
                message: __(data.message),
                indicator: data.indicator,
            },7);

            if (data.complete ) {
                frm.reload_doc();
            }
        });
    },

    refresh(frm) {
        frm.add_custom_button(__("Setup Zatca") , () => {
            frappe.call({
                method : "optima_zatca.zatca.setup.add_company_to_zatca" ,
                args : {
                    name : frm.doc.name
                }
            })
        })
    }
});
