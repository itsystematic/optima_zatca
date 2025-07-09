// Constants for prepayment logic only
const PREPAYMENT_TYPES = ["Initial Prepayment", "Prepayment"];
const ADJUSTMENT_TYPES = ["Adjustment", "Final Adjustment"];
const ADVANCE_PAYMENT_ITEM = "advance payment";

frappe.ui.form.on("Sales Invoice" , {
    refresh(frm) {
        frm.trigger("add_zatca_button") ;
        frm.trigger('remove_send_to_zatca_button') ;
        frm.trigger("setup_query_filters") ;
        if (frm.doc.is_return && !frm.doc.previous_prepayment){// set previous prepayment only once
            frm.set_value("previous_prepayment", frm.doc.return_against);
            frm.events.previous_prepayment(frm);
        }
        
        // frm.trigger("add_default_commercial_register");
    },

    validate(frm) {
    const { adjustment_percentage, sales_invoice_type } = frm.doc;

    if (sales_invoice_type === "Adjustment" && (adjustment_percentage <= 0 || adjustment_percentage >= 100)) {
        frappe.throw(__("Adjustment percentage must be greater than 0 and less than 100"));
    }

    if (Math.abs(flt(frm.doc.deducted_grand_total)) > Math.abs(flt(frm.doc.grand_total))) {
        frappe.throw(__("Deducted grand total cannot be greater than grand total"));
    }

    // Use absolute values for all calculations
    const abs_grand_total = Math.abs(flt(frm.doc.grand_total));
    const abs_total_grands = Math.abs(flt(frm.doc.total_grands));
    
    // Avoid division by zero
    if (abs_total_grands === 0) {
        frappe.throw(__("Total grands cannot be zero for adjustment percentage calculation"));
        return;
    }

    const max_adjustment_limit = (abs_grand_total * 100) / abs_total_grands;

    if (Math.abs(adjustment_percentage) > max_adjustment_limit) {
        frappe.throw(__(`Adjustment percentage cannot be greater than ${max_adjustment_limit.toFixed(2)}%`));
    }
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

    
        frm.set_query("previous_prepayment", () => {
            return {
                filters: {
                    is_linked: 0,
                    prepayment_type: ["!=", "Final Adjustment"],
                    customer: frm.doc.customer
                }
            }
        });
        

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

    // ========== REFACTORED PREPAYMENT LOGIC ==========
    sales_invoice_type(frm) {
        const isAdvancePayment = PREPAYMENT_TYPES.includes(frm.doc.sales_invoice_type);
        
        if (isAdvancePayment) {
            PrepaymentInvoiceHandler.setup(frm);
        } else {
            StandardInvoiceHandler.setup(frm);
        }
        
        // Toggle grid operations
        frm.fields_dict.items.grid.cannot_add_rows = isAdvancePayment;
        frm.fields_dict.items.grid.df.cannot_delete_rows = isAdvancePayment;
    },

    async previous_prepayment(frm) {
        if (!frm.doc.previous_prepayment) {
            PrepaymentCalculator.clearData(frm);
            return;
        }
        
        try {
            const prepayments = await PrepaymentService.fetchDetails(frm.doc.previous_prepayment);
            PrepaymentCalculator.populateAndCalculate(frm, prepayments);
        } catch (error) {
            frappe.msgprint(__("Error fetching prepayment details: {0}", [error.message]));
        }
    },

    adjustment_percentage(frm) {
        if (!PrepaymentValidator.validateAdjustmentPercentage(frm)) return;
        
        PrepaymentCalculator.updateDeductedAmounts(frm);
        PrepaymentCalculator.calculateDeductedTotals(frm);
    }
})

// ========== PREPAYMENT CLASSES (NEW) ==========

// Prepayment Service
const PrepaymentService = {
    async fetchDetails(prepaymentInvoice) {
        frappe.dom.freeze(__('Fetching prepayment details...'));
        
        try {
            const result = await frappe.call({
                method: "optima_zatca.zatca.utils.get_prepayment_details",
                args: {
                    prepayment_invoice: prepaymentInvoice,
                    filters: {}
                }
            });
            
            return result.message || [];
        } finally {
            frappe.dom.unfreeze();
        }
    }
};

// Prepayment Validator
const PrepaymentValidator = {
    validateAdjustmentPercentage(frm) {
        const percentage = frm.doc.adjustment_percentage || 0;
        
        if (percentage <= 0) {
            frappe.msgprint({
                title: __('Invalid Adjustment Percentage'),
                message: __('Adjustment percentage must be greater than 0'),
                indicator: 'red'
            });
            frm.set_value('adjustment_percentage', 0);
            return false;
        }
        return true;
    }
};

// Prepayment Invoice Handler
const PrepaymentInvoiceHandler = {
    setup(frm) {
        this.clearForm(frm);
        this.addAdvancePaymentItem(frm);
    },

    clearForm(frm) {
        frm.clear_table("items");
        frm.clear_table("taxes");
        frm.set_value({
            total: 0,
            net_total: 0,
            grand_total: 0,
            outstanding_amount: 0,
            total_taxes_and_charges: 0
        });
    },

    async addAdvancePaymentItem(frm) {
        const itemRow = frm.add_child("items", {
            item_code: ADVANCE_PAYMENT_ITEM,
            qty: 1,
            conversion_factor: 1.0,
            price_list_rate: 0,
        });

        try {
            await this.fetchItemDetails(frm, itemRow);
            frm.set_value("update_stock", 0);
            this.refreshFields(frm);
        } catch (error) {
            frappe.msgprint(__("Error setting up advance payment item: {0}", [error.message]));
        }
    },

    fetchItemDetails(frm, itemRow) {
        return new Promise((resolve, reject) => {
            frappe.call({
                method: "erpnext.stock.get_item_details.get_item_details",
                args: {
                    doc: frm.doc,
                    args: this.buildItemArgs(frm)
                },
                callback: (r) => {
                    if (r.message) {
                        Object.assign(itemRow, r.message);
                        itemRow.rate = 0;
                        itemRow.price_list_rate = 0;
                        frm.script_manager.trigger("item_code", itemRow.doctype, itemRow.name);
                        resolve();
                    } else {
                        reject(new Error("Failed to fetch item details"));
                    }
                },
                error: reject
            });
        });
    },

    buildItemArgs(frm) {
        return {
            item_code: ADVANCE_PAYMENT_ITEM,
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
        };
    },

    refreshFields(frm) {
        ["items", "taxes", "total", "grand_total"].forEach(field => {
            frm.refresh_field(field);
        });
    }
};

// Standard Invoice Handler
const StandardInvoiceHandler = {
    setup(frm) {
        frm.clear_table("items");
        frm.clear_table("taxes");
        frm.set_value({
            total: 0,
            net_total: 0,
            grand_total: 0,
            outstanding_amount: 0,
            total_taxes_and_charges: 0,
            update_stock: 1
        });
        this.refreshFields(frm);
    },

    refreshFields(frm) {
        ["items", "taxes", "total", "grand_total"].forEach(field => {
            frm.refresh_field(field);
        });
    }
};

// Prepayment Calculator
const PrepaymentCalculator = {
    clearData(frm) {
        frm.clear_table('prepayments_invcoies');
        frm.refresh_field('prepayments_invcoies');
    },

    populateAndCalculate(frm, prepayments) {
        this.populateData(frm, prepayments);
        this.calculateAll(frm);
    },

    populateData(frm, prepayments) {
        frm.clear_table('prepayments_invcoies');
        
        prepayments.forEach(prepayment => {
            const row = frm.add_child('prepayments_invcoies');
            // Copy all properties
            Object.assign(row, prepayment);
            // Set deducted values initially equal to original values
            row.deducted_tax_amount = prepayment.tax_amount;
            row.deducted_taxable_amount = prepayment.taxable_amount;
            row.deducted_grand_total = prepayment.grand_total;
        });
        
        frm.refresh_field('prepayments_invcoies');
    },

    calculateAll(frm) {
        this.calculatePrepaymentTotals(frm);
        this.calculateAdjustmentTotals(frm);
        this.calculateDeductedTotals(frm);
        this.calculateRemainingPercentage(frm);
        this.calculateAdjustmentPercentage(frm);
        this.calculateMaxAdjustmentLimit(frm);
    },

    updateDeductedAmounts(frm) {
        const factor = (frm.doc.adjustment_percentage || 0) / 100;
        
        frm.doc.prepayments_invcoies.forEach(row => {
            if (!PREPAYMENT_TYPES.includes(row.prepayment_type)) return;
            
            row.deducted_tax_amount = row.tax_amount * factor;
            row.deducted_taxable_amount = row.taxable_amount * factor;
            row.deducted_grand_total = row.grand_total * factor;
        });
    },

    calculatePrepaymentTotals(frm) {
        const totals = this.sumByTypeAndField(frm, PREPAYMENT_TYPES, 'deducted');
        frm.set_value({
            total_taxable_amount: totals.taxable,
            total_tax_amount: totals.tax,
            total_grands: totals.grand
        });
    },

    calculateAdjustmentTotals(frm) {
        const totals = this.sumByTypeAndField(frm, ADJUSTMENT_TYPES, 'deducted');
        frm.set_value({
            adjustment_taxable_amount: totals.taxable,
            adjustment_tax_amount: totals.tax,
            adjustment_grands: totals.grand
        });
    },

    calculateDeductedTotals(frm) {
        const totals = this.sumByTypeAndField(frm, PREPAYMENT_TYPES, 'deducted');
        frm.set_value({
            deducted_tax_amount: totals.tax,
            deducted_taxable_amount: totals.taxable,
            deducted_grand_total: totals.grand
        });
    },

    sumByTypeAndField(frm, types, fieldPrefix = '') {
        const result = { taxable: 0, tax: 0, grand: 0 };
        
        const taxField = fieldPrefix ? `${fieldPrefix}_tax_amount` : 'tax_amount';
        const taxableField = fieldPrefix ? `${fieldPrefix}_taxable_amount` : 'taxable_amount';
        const grandField = fieldPrefix ? `${fieldPrefix}_grand_total` : 'grand_total';

        frm.doc.prepayments_invcoies.forEach(row => {
            if (!types.includes(row.prepayment_type)) return;
            
            result.taxable += flt(row[taxableField]);
            result.tax += flt(row[taxField]);
            result.grand += flt(row[grandField]);
        });

        return result;
    },

    calculateRemainingPercentage(frm) {
        // Handle return case
        if (frm.doc.is_return && frm.doc.prepayments_invcoies.length > 0) {
            const remaining = frm.doc.prepayments_invcoies[0].remaining_percentage || 0;
            frm.set_value("remaining_percentage", remaining);
            return remaining;
        }

        // No prepayment case
        if (!frm.doc.previous_prepayment || !frm.doc.prepayments_invcoies.length) {
            return 100;
        }
        
        // Calculate used percentage
        const totalUsed = frm.doc.prepayments_invcoies.reduce(
            (sum, row) => sum + flt(row.adjustment_percentage), 0
        );
        
        const remaining = Math.max(0, 100 - totalUsed);
        frm.set_value("remaining_percentage", remaining);
        return remaining;
    },

    calculateAdjustmentPercentage(frm) {
        // Final adjustment case
        if (frm.doc.sales_invoice_type === "Final Adjustment") {
            const remaining = this.calculateRemainingPercentage(frm);
            frm.set_value("adjustment_percentage", remaining);
            frm.set_df_property("adjustment_percentage", "read_only", true);
            return;
        }

        // Return case
        if (frm.doc.is_return && frm.doc.prepayments_invcoies.length > 0) {
            const percentage = frm.doc.prepayments_invcoies[0].adjustment_percentage || 0;
            frm.set_value("adjustment_percentage", percentage);
            frm.set_df_property("adjustment_percentage", "read_only", true);
        }
    },

    calculateMaxAdjustmentLimit(frm) {
        const grandTotal = Math.abs(flt(frm.doc.grand_total));
        const totalGrands = Math.abs(flt(frm.doc.total_grands));
        
        if (totalGrands === 0) {
            frm.set_value("max_adjustment_limit", 0);
            return;
        }
        
        const limit = (grandTotal * 100) / totalGrands;
        frm.set_value("max_adjustment_limit", limit);
    }
};

// ========== ORIGINAL FUNCTIONS (LEGACY SUPPORT) ==========
// Keep these for backward compatibility but they now use the new classes

function handleAdvancePaymentInvoice(frm) {
    PrepaymentInvoiceHandler.setup(frm);
}

function handleStandardInvoice(frm) {
    StandardInvoiceHandler.setup(frm);
}

function CalculatePrepaymentTotals(frm) {
    PrepaymentCalculator.calculatePrepaymentTotals(frm);
}

function CalculateAdjustmentTotals(frm) {
    PrepaymentCalculator.calculateAdjustmentTotals(frm);
}

function calculateDeductedValues(frm) {
    PrepaymentCalculator.calculateDeductedTotals(frm);
}

function validateAdjustmentPercentage(frm) {
    return PrepaymentValidator.validateAdjustmentPercentage(frm);
}

function calculateRemainingPercentage(frm) {
    return PrepaymentCalculator.calculateRemainingPercentage(frm);
}

function calculateAdjustmentPercentage(frm) {
    PrepaymentCalculator.calculateAdjustmentPercentage(frm);
}

function calculateMaxAdjustmentLimit(frm) {
    PrepaymentCalculator.calculateMaxAdjustmentLimit(frm);
}

// ========== UNCHANGED LEGACY FUNCTIONS ==========

function fetchAdvancePaymentItemDetails(frm, item_row) {
    return PrepaymentInvoiceHandler.fetchItemDetails(frm, item_row);
}

function clearChildTables(frm) {
    PrepaymentInvoiceHandler.clearForm(frm);
}

function resetStockSettings(frm) {
    frm.set_value("update_stock", 1);
}

function refreshFormFields(frm) {
    PrepaymentInvoiceHandler.refreshFields(frm);
}

function triggerTaxRefresh(frm, item_row) {
    frm.script_manager.trigger("item_code", item_row.doctype, item_row.name);
}

// ========== END REFACTORED PREPAYMENT LOGIC ==========

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