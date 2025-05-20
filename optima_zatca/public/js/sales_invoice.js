


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
    },

    // Advance Payment ********
    sales_invoice_type(frm) {
        if (frm.doc.sales_invoice_type == "Elementary Advance Payment") {
            handleAdvancePaymentInvoice(frm);
        } else {
            handleStandardInvoice(frm);
        }
    },

    previous_sales_invoice: function(frm) {
        if(!frm.doc.previous_sales_invoice) {
            // Clear the child table if the field is cleared
            frm.clear_table('prepayments_invcoies');
            frm.refresh_field('prepayments_invcoies');
            return;
        }
        
        // Show loading indicator
        frappe.dom.freeze(__('Fetching prepayment details...'));
        
        // Call a server-side method to fetch prepayment data
        frappe.call({
            method: "optima_zatca.zatca.utils.get_prepayment_details",
            args: {
                prepayment_invoice: frm.doc.previous_sales_invoice,
                filters: {
                    // customer: frm.doc.customer,
                    // docstatus: 1,  // Example: Only submitted prepayments
                    // outstanding_amount: [">", 0]  // Example: Only with outstanding amount
                }
            },
            callback: function(r) {
                console.log("Response from server: ", r);
                frm.clear_table('prepayments_invcoies');
                
                if (r.message && r.message.length) {
                    // Add fetched rows to child table
                    r.message.forEach(function(prepayment) {
                        let row = frm.add_child('prepayments_invcoies');

                        row.reference_invoice = prepayment.name;
                        row.tax_amount = prepayment.tax_amount;
                        row.taxable_amount = prepayment.taxable_amount;
                        row.uuid = prepayment.uuid;
                        row.tax_category = prepayment.tax_category;
                        row.percent = prepayment.percent;
                        row.issue_date = prepayment.issue_date;
                        row.issue_time = prepayment.issue_time;
                        
                    });
                }
                
                frm.refresh_field('prepayments_invcoies');
                frappe.dom.unfreeze();
            }
        });
    }

})

// Advance Payment Handler
function handleAdvancePaymentInvoice(frm) {
    clearChildTables(frm);
    
    const item_row = frm.add_child("items", {
        item_code: "advance payment",
        qty: 1,
        conversion_factor: 1.0,
        price_list_rate : 0,
    });

    fetchAdvancePaymentItemDetails(frm, item_row).then(() => {
        frm.set_value("update_stock", 0);
        refreshFormFields(frm);
    });
}

// Standard Invoice Handler
function handleStandardInvoice(frm) {
    clearChildTables(frm);
    resetStockSettings(frm);
    refreshFormFields(frm);
}

// Core Functions
function fetchAdvancePaymentItemDetails(frm, item_row) {
    return new Promise((resolve) => {
        frappe.call({
            method: "erpnext.stock.get_item_details.get_item_details",
            args: {
                doc: frm.doc,
                args: {
                    item_code: "advance payment",
                    set_warehouse: frm.doc.set_warehouse,
                    customer: frm.doc.customer || frm.doc.party_name,
                    quotation_to: frm.doc.quotation_to,
                    supplier: frm.doc.supplier,
                    currency: frm.doc.currency,
                    is_internal_supplier: frm.doc.is_internal_supplier,
                    is_internal_customer: frm.doc.is_internal_customer,
                    conversion_rate: frm.doc.conversion_rate,
                    price_list: frm.doc.selling_price_list || frm.doc.buying_price_list,
                    price_list_currency: frm.doc.price_list_currency,
                    plc_conversion_rate: frm.doc.plc_conversion_rate,
                    company: frm.doc.company,
                    order_type: frm.doc.order_type,
                    is_pos: cint(frm.doc.is_pos),
                    is_return: cint(frm.doc.is_return),
                    is_subcontracted: frm.doc.is_subcontracted,
                    ignore_pricing_rule: frm.doc.ignore_pricing_rule,
                    doctype: frm.doc.doctype,
                    name: frm.doc.name,
                    qty: frm.doc.qty || 1,
                    uom: frm.doc.uom,
                    pos_profile: cint(frm.doc.is_pos) ? frm.doc.pos_profile : "",
                    tax_category: frm.doc.tax_category,
                    child_doctype: frm.doc.doctype + " Item",
                    is_old_subcontracting_flow: frm.doc.is_old_subcontracting_flow,
                }
            },
            callback: (r) => {
                Object.assign(item_row, r.message);
                item_row.rate = 0;
                item_row.price_list_rate = 0;
                triggerTaxRefresh(frm, item_row);
                resolve();
            }
        });
    });
}

function clearChildTables(frm) {
    // Clear data but maintain field structure
    frm.clear_table("items");
    frm.clear_table("taxes");
    
    // Reset calculated fields
    frm.set_value("total", 0);
    frm.set_value("net_total", 0);
    frm.set_value("grand_total", 0);
    frm.set_value("outstanding_amount", 0);
    frm.set_value("total_taxes_and_charges", 0);
}

function resetStockSettings(frm) {
    frm.set_value("update_stock", 1);
}

function refreshFormFields(frm) {
    ["items", "taxes", "total", "grand_total"].forEach(field => {
        frm.refresh_field(field);
    });
}

function triggerTaxRefresh(frm, item_row) {
    frm.script_manager.trigger("item_code", item_row.doctype, item_row.name);
}
// End of Advance Payment ********


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