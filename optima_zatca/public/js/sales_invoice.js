// Constants for prepayment logic only
const PREPAYMENT_TYPES = ["Initial Prepayment", "Prepayment"];
const ADJUSTMENT_TYPES = ["Adjustment", "Final Adjustment"];


frappe.ui.form.on("Sales Invoice" , {
    async refresh(frm) {
        frm.trigger("add_zatca_button") ;
        frm.trigger('remove_send_to_zatca_button') ;
        frm.trigger("setup_query_filters") ;
        if (shouldSetPreviousPrepayment(frm.doc)) {
            await setPreviousPrepayment(frm);
        }
        
    },

    validate(frm) {
        if (frm.doc.sales_invoice_type == "Normal") {
            return;
        }
        const { adjustment_percentage, sales_invoice_type } = frm.doc;

        // Validate adjustment type percentage range
        if (
            sales_invoice_type === "Adjustment" &&
            (adjustment_percentage <= 0 || adjustment_percentage >= 100)
        ) {
            frappe.throw(__("Adjustment percentage must be greater than 0 and less than 100"));
        }

        // Validate deducted total against grand total
        if (
            Math.abs(flt(frm.doc.deducted_grand_total)) > Math.abs(flt(frm.doc.base_grand_total || frm.doc.grand_total)) &&
            ADJUSTMENT_TYPES.includes(sales_invoice_type)
        ) {
            frappe.throw(__("Deducted grand total cannot be greater than grand total"));
        }

        // Calculate and validate adjustment percentage limit
        const absGrandTotal = Math.abs(flt(frm.doc.base_grand_total || frm.doc.grand_total));
        const absTotalGrands = Math.abs(flt(frm.doc.total_grands));
        
        // Avoid division by zero
        if (absTotalGrands === 0 &&
            ADJUSTMENT_TYPES.includes(sales_invoice_type)
        ) {
            frappe.throw(__("Total grands cannot be zero for adjustment percentage calculation"));
        }

        const maxAdjustmentLimit = (absGrandTotal * 100) / absTotalGrands;

        if (Math.abs(adjustment_percentage || 0) > maxAdjustmentLimit) {
            frappe.throw(__(`Adjustment percentage cannot be greater than ${maxAdjustmentLimit.toFixed(2)}%`));
        }
                // Validate for POS payments in adjustment types
        if (ADJUSTMENT_TYPES.includes(sales_invoice_type) && frm.doc.is_pos == 1) {
            const absDeductedGrandTotal = Math.abs(flt(frm.doc.deducted_grand_total));
            const absPaidAmount = Math.abs(flt(frm.doc.paid_amount));
            const absGrandTotal = Math.abs(flt(frm.doc.base_grand_total || frm.doc.grand_total));
            
            if (absDeductedGrandTotal + absPaidAmount > absGrandTotal) {
                frappe.throw(__("(Deducted Grand Total + Paid Amount) Must Be Less Than Or Equal To The Grand Total "));
            }
        }

        // Validate for non-POS payments in adjustment types
        if (ADJUSTMENT_TYPES.includes(sales_invoice_type) && frm.doc.is_pos == 0) {
            const absDeductedGrandTotal = Math.abs(flt(frm.doc.deducted_grand_total));
            const absTotalAdvance = Math.abs(flt(frm.doc.total_advance));
            const absGrandTotal = Math.abs(flt(frm.doc.base_grand_total || frm.doc.grand_total));
            
            if (absDeductedGrandTotal + absTotalAdvance > absGrandTotal) {
                frappe.throw(__("Deducted Grand Total + Total Advance Must Be Less Than Or Equal To The Grand Total"));
            }
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
                        // cur_frm.reload_doc();
                        frappe.show_alert({
                            message : __("Invoice sumbitted successfully"),
                            indicator : "green"
                        })

                        frm.reload_doc();
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
                    customer: frm.doc.customer,
                    currency: frm.doc.currency
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

    // Advance Payment ********
    sales_invoice_type(frm) {
        if (["Initial Prepayment", "Prepayment"].includes(frm.doc.sales_invoice_type)) {
            handleAdvancePaymentInvoice(frm);
            
            // Disable adding and deleting rows
            frm.fields_dict.items.grid.cannot_add_rows = true;
            frm.fields_dict.items.grid.df.cannot_delete_rows = true;
        } else {
            handleStandardInvoice(frm);

            // Enable adding and deleting rows
            frm.fields_dict.items.grid.cannot_add_rows = false;
            frm.fields_dict.items.grid.df.cannot_delete_rows = false;
        }
    },

    previous_prepayment: async function(frm) {
        if (!frm.doc.previous_prepayment) {
            frm.clear_table('prepayments_invcoies');
            frm.refresh_field('prepayments_invcoies');
            return;
        }

        try {
            frappe.dom.freeze(__('Fetching prepayment details...'));
            
            const prepaymentData = await fetchPrepaymentData(frm.doc.previous_prepayment);
            populatePrepaymentTable(frm, prepaymentData);
            calculateAllPrepaymentTotals(frm);
            
        } catch (error) {
            frappe.msgprint(__("Error: {0}", [error.message]));
        } finally {
            frappe.dom.unfreeze();
        }
    },

    adjustment_percentage(frm) {
        if (!validateAdjustmentPercentage(frm)) {
            return;
        }

        const factor = AdjustmentCalculator.calculateFactor(frm.doc.adjustment_percentage);
        AdjustmentCalculator.updatePrepaymentDeductions(frm, factor);
        calculateDeductedValues(frm);
    }

})

// Advance Payment Handlers
// ***************************************
const setPreviousPrepayment = async (frm) => {
    try {
        if (!frm.doc.return_against) {
            frappe.throw(__("Please select a return against invoice first."));
            return;
        }
        const prepayment = await frappe.db.get_doc("Prepayment Invoice", frm.doc.return_against);

        if (prepayment?.is_linked) {
            frappe.throw(__("The selected prepayment invoice is already linked or does not exist."));
            return;
        }
        if (prepayment?.name) {
            frm.set_value("previous_prepayment", prepayment.name);
            frm.events.previous_prepayment(frm);
        }
    } catch (error) {
        console.error("Error setting previous prepayment:", error);
    }
};
const shouldSetPreviousPrepayment = (doc) => {
    return doc.is_return && 
            !doc.previous_prepayment && 
            doc.sales_invoice_type !== "Normal";
};
// ***************************************
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
    // clearChildTables(frm);// Jamail and Walla said Noooo
    // resetStockSettings(frm);// but am as fawaz sure they wiil request later(LOOOOOOOL)
    refreshFormFields(frm);
}

// Core Functions
function fetchAdvancePaymentItemDetails(frm, item_row) {
    return new Promise((resolve) => {
        frappe.call({
            method: "optima_zatca.zatca.utils.get_item_details",
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
                    sales_invoice_type: frm.doc.sales_invoice_type,
                }
            },
            callback: (r) => {
                // Store the custom income_account before any processing
                const custom_income_account = r.message.income_account;
                
                Object.assign(item_row, r.message);
                item_row.rate = 0;
                item_row.price_list_rate = 0;
                
                // Mark this row to preserve income_account
                item_row.__preserve_income_account = custom_income_account;
                
                triggerTaxRefresh(frm, item_row);
                
                // Set income_account after refresh cycle
                setTimeout(() => {
                    frappe.model.set_value(item_row.doctype, item_row.name, "income_account", custom_income_account);
                    frm.refresh_field("items");
                    resolve();
                }, 200);
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

// ****************************************
const createTotalsCalculator = (filterTypes, fieldMapping) => (frm) => {
    const totals = frm.doc.prepayments_invcoies
        .filter(row => filterTypes.includes(row.prepayment_type))
        .reduce((acc, row) => ({
            taxable: acc.taxable + (row.deducted_taxable_amount || 0),
            tax: acc.tax + (row.deducted_tax_amount || 0),
            grand: acc.grand + (row.deducted_grand_total || 0)
        }), { taxable: 0, tax: 0, grand: 0 });

    frm.set_value(fieldMapping(totals));
};

// Create specific calculators
const CalculatePrepaymentTotals = createTotalsCalculator(
    PREPAYMENT_TYPES,// ["Initial Prepayment", "Prepayment"],
    (totals) => ({
        "total_taxable_amount": totals.taxable,
        "total_tax_amount": totals.tax,
        "total_grands": totals.grand
    })
);

const CalculateAdjustmentTotals = createTotalsCalculator(
    ADJUSTMENT_TYPES, // ["Adjustment", "Final Adjustment"],
    (totals) => ({
        "adjustment_taxable_amount": totals.taxable,
        "adjustment_tax_amount": totals.tax,
        "adjustment_grands": totals.grand
    })
);

const calculateDeductedValues = createTotalsCalculator(
    PREPAYMENT_TYPES,// ["Initial Prepayment", "Prepayment"],
    (totals) => ({
        "deducted_tax_amount": totals.tax,
        "deducted_taxable_amount": totals.taxable,
        "deducted_grand_total": totals.grand
    })
);

const fetchPrepaymentData = (prepaymentInvoice) => {
    return frappe.call({
        method: "optima_zatca.zatca.utils.get_prepayment_details",
        args: { prepayment_invoice: prepaymentInvoice, filters: {} }
    }).then(r => r.message || []);
};

const populatePrepaymentTable = (frm, data) => {
    frm.clear_table('prepayments_invcoies');
    
    data.forEach(prepayment => {
        const row = frm.add_child('prepayments_invcoies');
        assignPrepaymentFields(row, prepayment);
    });
    
    frm.refresh_field('prepayments_invcoies');
};

const assignPrepaymentFields = (row, prepayment) => {
    const fields = [
        'name', 'tax_amount', 'taxable_amount', 'uuid', 'tax_category', 
        'percent', 'issue_date', 'issue_time', 'grand_total', 'customer', 
        'prepayment_type', 'remaining_percentage', 'adjustment_percentage', 
        'been_return', 'is_linked', 'is_return'
    ];
    
    fields.forEach(field => {
        const targetField = field === 'name' ? 'reference_invoice' : field;
        row[targetField] = prepayment[field];
    });
    
    // Set deducted values
    row.deducted_tax_amount = prepayment.tax_amount;
    row.deducted_taxable_amount = prepayment.taxable_amount;
    row.deducted_grand_total = prepayment.grand_total;
};

const calculateAllPrepaymentTotals = (frm) => {
    [
        CalculatePrepaymentTotals,
        CalculateAdjustmentTotals,
        calculateRemainingPercentage,
        calculateAdjustmentPercentage,
        calculateDeductedValues
    ].forEach(fn => fn(frm));
    
    // Run last since it previous calculations like: total_grands
    setTimeout(() => calculateMaxAdjustmentLimit(frm), 10);
};
// *****************************************
function validateAdjustmentPercentage(frm) {
    const adjustmentPercentage = frm.doc.adjustment_percentage || 0;
    
    if (adjustmentPercentage <= 0 && !frm.doc.is_return) {
        AdjustmentValidationHelper.showError(frm);
        return false;
    }
    
    return true;
}

const AdjustmentValidationHelper = {
    showError(frm) {
        frappe.msgprint({
            title: __('Invalid Adjustment Percentage'),
            message: __('Adjustment percentage must be greater than 0'),
            indicator: 'red'
        });
        frm.set_value('adjustment_percentage', 0);
    }
};

const AdjustmentCalculator = {
    calculateFactor(adjustmentPercentage) {
        return (adjustmentPercentage / 100) || 1;
    },

    updatePrepaymentDeductions(frm, factor) {
        frm.doc.prepayments_invcoies
            .filter(row => PREPAYMENT_TYPES.includes(row.prepayment_type))
            .forEach(row => this.updateRowAmounts(row, factor));
    },

    updateRowAmounts(row, factor) {
        row.deducted_tax_amount = (row.tax_amount || 0) * factor;
        row.deducted_taxable_amount = (row.taxable_amount || 0) * factor;
        row.deducted_grand_total = (row.grand_total || 0) * factor;
    }
};

// *****************************************
function calculateRemainingPercentage(frm) {
    let remainingPercentage;

    // in case of return, fetch the first prepayment invoice remaining percentage
    if (frm.doc.is_return) {
        remainingPercentage = getReturnRemainingPercentage(frm);
    } 
    // If no previous prepayment, return 100%
    else if (isNoPrepaymentScenario(frm)) {
        remainingPercentage = 100;
    } 
    // Calculate remaining percentage from used adjustments
    else {
        remainingPercentage = calculateRemainingFromUsedPercentages(frm);
    }
    
    setRemainingPercentage(frm, remainingPercentage);
    return remainingPercentage;
}

function getReturnRemainingPercentage(frm) {
    if (hasValidPrepaymentInvoices(frm)) {
        return frm.doc.prepayments_invcoies[0].remaining_percentage || 0;
    }
    return 0;
}

function isNoPrepaymentScenario(frm) {
    return !frm.doc.previous_prepayment || 
            !frm.doc.prepayments_invcoies || 
            frm.doc.prepayments_invcoies.length === 0;
}

function calculateRemainingFromUsedPercentages(frm) {
    const totalUsedPercentage = frm.doc.prepayments_invcoies.reduce((total, row) => {
        return total + (row.adjustment_percentage || 0);
    }, 0);
    
    const remainingPercentage = 100 - totalUsedPercentage;
    return Math.max(0, remainingPercentage); // Ensure it's not negative
}

function hasValidPrepaymentInvoices(frm) {
    return frm.doc.prepayments_invcoies && frm.doc.prepayments_invcoies.length > 0;
}

function setRemainingPercentage(frm, percentage) {
    frm.set_value("remaining_percentage", percentage);
}

//*****************************************
function calculateAdjustmentPercentage(frm) {
    // only set automatically if the type is Final Prepayment, all the remaining should be adjusted then
    if (frm.doc.sales_invoice_type === "Final Adjustment") {
        const remainingPercentage = calculateRemainingPercentage(frm);
        updateAndLockAdjustmentPercentage(frm, remainingPercentage);
    }

    // in case of return, fetch the first prepayment invoice adjustment percentage
    if (frm.doc.is_return) {
        if (frm.doc.prepayments_invcoies && frm.doc.prepayments_invcoies.length > 0) {
            const adjustmentPercentage = frm.doc.prepayments_invcoies[0].adjustment_percentage || 0;
            updateAndLockAdjustmentPercentage(frm, adjustmentPercentage);
        }
    }
}

function updateAndLockAdjustmentPercentage(frm, percentage) {
    frm.set_value("adjustment_percentage", percentage);
    frm.events.adjustment_percentage(frm);
    frm.set_df_property("adjustment_percentage", "read_only", true);
}
// *****************************************
function calculateMaxAdjustmentLimit(frm) {

    // Use base_grand_total for multi-currency, fallback to grand_total for single currency
    const grandTotal = Math.abs(frm.doc.base_grand_total || frm.doc.grand_total) || 0;
    const totalGrands = Math.abs(frm.doc.total_grands) || 0;
    
    const calculatedLimit = totalGrands === 0 ? 0 : (grandTotal * 100) / totalGrands;

    const maxAdjustmentLimit = Math.max(0, Math.min(100, calculatedLimit));
    
    frm.set_value("max_adjustment_limit", maxAdjustmentLimit);
    frm.refresh_field("max_adjustment_limit");
}


// End of Advance Payment **********************************************************************************************************************


frappe.ui.form.on("Sales Invoice Item" , {
    item_tax_template(frm ,cdt ,cdn) {
        let item = frappe.get_doc(cdt ,cdn) ;

        if (item.item_tax_template) {
            frappe.db.get_value("Item Tax Template", item.item_tax_template, ["tax_category"]).then(r => {
                frappe.model.set_value(cdt ,cdn , "tax_category" , r.message.tax_category)
            })
        }
    },
    
    income_account(frm, cdt, cdn) {
        // Preserve custom income_account for advance payment items
        let item = frappe.get_doc(cdt, cdn);
        
        if (item.__preserve_income_account && 
            item.item_code === "advance payment" && 
            ["Initial Prepayment", "Prepayment"].includes(frm.doc.sales_invoice_type)) {
            
            // If income_account was changed by system, restore our custom value
            if (item.income_account !== item.__preserve_income_account) {
                setTimeout(() => {
                    frappe.model.set_value(cdt, cdn, "income_account", item.__preserve_income_account);
                }, 50);
            }
        }
    }
})