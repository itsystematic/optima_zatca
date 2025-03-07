


frappe.ui.form.on("Sales Invoice" , {
    refresh(frm) {
        frm.trigger("add_zatca_button") ;
        frm.trigger('remove_send_to_zatca_button') ;
        frm.trigger("setup_query_filters") ;
        // frm.trigger("add_default_commercial_register");
    },


    add_zatca_button(frm) {
    
        if ( frm.is_new() || frm.doc.sent_to_zatca == 1 || frappe.boot.zatca_phase == "Phase One" ) return ;
        
        frm.add_custom_button(__("Send To Zatca"), function () {

            if (frm.is_dirty()) {
                frappe.throw(__("Please save first."));
            }

            frappe.call({
                method : "optima_zatca.zatca.invoice.send_to_zatca" ,
                args : {
                    sales_invoice_name : frm.doc.name
                },
                is_async : true,
                freeze : true,
                freeze_message : __("Sending Invoice {0} to Zatca", [frm.doc.name]),
                callback(r){
                    if(r.message){
                        cur_frm.reload_doc();
                    }
                }
            })
        }).css({
            "background-color" : "#0b002e",
            "color" : "white"
        })
    } ,
    setup_query_filters(frm) {

        frm.set_query("tax_exemption" , "items" , (doc ,cdt,cdn) => {
            let row = frappe.get_doc(cdt ,cdn) ;
            return {
                filters : {
                    code : row.tax_category 
                }
            }
        })

        frm.set_query("commercial_register" , () => {
            return {
                filters : {
                    company : frm.doc.company
                }
            }
        })
    },

    async commercial_register(frm) {
        let company_address = "";

        if (frm.doc.commercial_register) {
            let commercial_register = await frappe.db.get_value("Commercial Register", frm.doc.commercial_register, ["address"]) ;
            company_address = commercial_register.message ? commercial_register.message.address : "";
        }
        frm.set_value("company_address" , company_address) ;
    },

    company(frm) {
        if(frm.doc.company) {
            frappe.db.get_value("Commercial Register" , {"is_default" : 1 , "company" : frm.doc.company} , "name").then(r => {
                if (r.message.name) {
                    frm.set_value("commercial_register" , r.message.name)
                } else {
                    frappe.show_alert({
                        message : __("No default commercial register found for company {0}" , [frm.doc.company]),
                        indicator : "yellow"
                    })
                }
                
            })
        }    
    },

    // add_default_commercial_register(frm) {
    //     setTimeout(() => {
    //         if(frm.doc.company && !frm.doc.commercial_register && ![1,2].includes(frm.doc.docstatus)) {
    //             frappe.db.get_value("Commercial Register" , {"is_default" : 1 , "company" : frm.doc.company} , "name").then(r => {
    //                 if (r.message.name) {
    //                     frm.set_value("commercial_register" , r.message.name)
    //                 } else {
    //                     frappe.show_alert({
    //                         message : __("No default commercial register found for company {0}" , [frm.doc.company]),
    //                         indicator : "yellow"
    //                     })
    //                 }
                    
    //             })
    //         }    
    //     }, 200);

    // },

    is_return(frm) {
        if (frm.doc.is_return) {
            frm.set_df_property("return_against" , "label" , __("Return Against"));
            frm.set_df_property("return_against" , "reqd" , 1);
        } else {
            frm.set_df_property("return_against" , "reqd" , 0);
        }
    },

    is_debit_note(frm) {
        if (frm.doc.is_debit_note) {
            frm.set_df_property("return_against" , "label" , __("Debit Note Against"));
            frm.set_df_property("return_against" , "reqd" , 1);
        } else {
            frm.set_df_property("return_against" , "reqd" , 0);
        }
    },



    remove_send_to_zatca_button(frm) {
        //Check if user got access
        if (frappe.user.has_role('Zatca Role')) return;
        // Selecting Send To Zatca Button
        const btn = $('[data-label="Send%20To%20Zatca"]')
        // Deleting All Event Listeners
        btn.off()
        btn.hide()
        // Adding Custom Event Listener
        btn.click(() => {
            frappe.msgprint('You have NO Permission for send to Zatca , Please Try to Connect with your Manager')
        })
    }
})


frappe.ui.form.on("Sales Invoice Item" , {
    item_tax_template(frm ,cdt ,cdn) {
        let item = frappe.get_doc(cdt ,cdn) ;

        if (item.item_tax_template) {
            frappe.db.get_value("Item Tax Template", item.item_tax_template, ["tax_category"]).then(r => {
                frappe.model.set_value(cdt ,cdn , "tax_category" , r.message.tax_category)
            })
        }
    }
})