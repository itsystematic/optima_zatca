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
        frm.trigger("add_buttons");
    },


    add_buttons(frm) {
        frm.add_custom_button(__("Setup Zatca Phase Two") , () => {
            frappe.confirm('Are you sure you want to proceed?',
                () => {
                    frappe.call({
                        method : "optima_zatca.zatca.setup.add_company_to_zatca" ,
                        args : {
                            name : frm.doc.name
                        }
                    })
                }, () => {
                    // action to perform if No is selected
                })
        } , __("Setup Zatca"));

        if (frm.doc.check_pcsid ) {
            frm.add_custom_button(__("Renew Production Certificate") , () => {
                frappe.confirm('Are you sure you want to proceed?',
                    () => {
                        frappe.call({
                            method : "optima_zatca.zatca.setup.renew_production_certificate" ,
                            args : {
                                setting : frm.doc.name,
                                otp : frm.doc.otp ,
                                authorization : frm.doc.authorization ,
                                csr : frm.doc.csr
                            }
                        })
                    }, () => {
                        // action to perform if No is selected
                    })
            } , __("Setup Zatca"));
        }
    }
});
