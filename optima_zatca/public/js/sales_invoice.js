/**
 * Sales Invoice Main Form Controller - Optima ZATCA
 * 
 * This is the main orchestration file that wires together:
 * - Prepayment logic (from prepayment.js)
 * - POS payment overrides (from pos_payments.js)
 * - ZATCA button handlers (from zatca_buttons.js)
 * 
 * Dependencies: All modules must be loaded via hooks.py before this file
 */

frappe.provide("optima_zatca.sales_invoice");

// ============================================================================
// CONVENIENCE ALIASES
// ============================================================================

// Alias for prepayment namespace
const prepayment = optima_zatca.sales_invoice.prepayment;
const PREPAYMENT_TYPES = optima_zatca.sales_invoice.prepayment.PREPAYMENT_TYPES;
const ADJUSTMENT_TYPES = optima_zatca.sales_invoice.prepayment.ADJUSTMENT_TYPES;


// ============================================================================
// MAIN FORM EVENT HANDLERS
// ============================================================================

frappe.ui.form.on("Sales Invoice", {
    async refresh(frm) {
        frm.trigger("add_zatca_button");
        frm.trigger("add_pdfa3_button");
        frm.trigger('remove_send_to_zatca_button');
        frm.trigger("setup_query_filters");
        
        if (prepayment.shouldSetPreviousPrepayment(frm.doc)) {
            await prepayment.setPreviousPrepayment(frm);
        }
    },

    onload(frm) {
        // Clear prepayment_sales_order if not a prepayment invoice type
        if (frm.doc.prepayment_sales_order && 
            !PREPAYMENT_TYPES.includes(frm.doc.sales_invoice_type)) {
            frm.set_value('prepayment_sales_order', '');
        }
    },

    sales_invoice_type(frm) {
        // Handle prepayment vs standard invoice setup
        if (PREPAYMENT_TYPES.includes(frm.doc.sales_invoice_type)) {
            prepayment.handleAdvancePaymentInvoice(frm);
            
            // Disable adding and deleting rows
            frm.fields_dict.items.grid.cannot_add_rows = true;
            frm.fields_dict.items.grid.df.cannot_delete_rows = true;
        } else {
            prepayment.refreshFormFields(frm);

            // Enable adding and deleting rows
            frm.fields_dict.items.grid.cannot_add_rows = false;
            frm.fields_dict.items.grid.df.cannot_delete_rows = false;
        }
        
        // Clear prepayment_sales_order when changing invoice type away from prepayment
        if (frm.doc.prepayment_sales_order && 
            !PREPAYMENT_TYPES.includes(frm.doc.sales_invoice_type)) {
            frm.set_value('prepayment_sales_order', '');
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
            const absPaidAmount = Math.abs(flt(frm.doc.base_paid_amount));
            const absGrandTotal = Math.abs(flt(frm.doc.base_grand_total));
            
            if (absDeductedGrandTotal + absPaidAmount > absGrandTotal) {
                frappe.throw(__("(Deducted Grand Total + Paid Amount) Must Be Less Than Or Equal To The Grand Total "));
            }
        }

        // Validate for non-POS payments in adjustment types
        if (ADJUSTMENT_TYPES.includes(sales_invoice_type) && frm.doc.is_pos == 0) {
            const absDeductedGrandTotal = Math.abs(flt(frm.doc.deducted_grand_total));
            const totalAllocatedAdvance = (frm.doc.advances || []).reduce((sum, row) => sum + flt(row.allocated_amount), 0);
            const absTotalAdvance = Math.abs(flt(totalAllocatedAdvance * frm.doc.conversion_rate));
            const absGrandTotal = Math.abs(flt(frm.doc.base_grand_total));
            
            if (absDeductedGrandTotal + absTotalAdvance > absGrandTotal) {
                frappe.throw(__("Deducted Grand Total + Total Advance Must Be Less Than Or Equal To The Grand Total"));
            }
        }
    },

    setup_query_filters(frm) {
        frm.set_query("tax_exemption", "items", (doc, cdt, cdn) => {
            let row = frappe.get_doc(cdt, cdn);
            return {
                filters: {
                    code: row.tax_category 
                }
            };
        });

        frm.set_query("commercial_register", () => {
            return {
                filters: {
                    company: frm.doc.company
                }
            };
        });

        frm.set_query("previous_prepayment", () => {
            // Get sales order from sales invoice
            let sales_order = null;
            
            // Priority 1: Check prepayment_sales_order field
            if (frm.doc.prepayment_sales_order) {
                sales_order = frm.doc.prepayment_sales_order;
            }
            // Priority 2: Check first item's sales_order field
            else if (frm.doc.items && frm.doc.items.length > 0 && frm.doc.items[0].sales_order) {
                sales_order = frm.doc.items[0].sales_order;
            }
            
            // Build filters
            let filters = {
                is_linked: 0,
                prepayment_type: ["!=", "Final Adjustment"],
                customer: frm.doc.customer,
                currency: frm.doc.currency
            };
            
            // Add sales_order filter only if it exists
            if (sales_order) {
                filters.sales_order = sales_order;
            }
            
            return { filters: filters };
        });
        
        frm.set_query("sales_invoice_type", () => {
            if (frm.doc.prepayment_sales_order) {
                return {
                    filters: {
                        name: ["in", PREPAYMENT_TYPES]
                    }
                };
            }
            return {};
        });
    },

    async commercial_register(frm) {
        let company_address = "";

        if (frm.doc.commercial_register) {
            let commercial_register = await frappe.db.get_value("Commercial Register", frm.doc.commercial_register, ["address"]);
            company_address = commercial_register.message ? commercial_register.message.address : "";
        }
        frm.set_value("company_address", company_address);
    },

    company(frm) {
        if (frm.doc.company) {
            frappe.db.get_value("Commercial Register", {"is_default": 1, "company": frm.doc.company}, "name").then(r => {
                if (r.message.name) {
                    frm.set_value("commercial_register", r.message.name);
                } else {
                    frappe.show_alert({
                        message: __("No default commercial register found for company {0}", [frm.doc.company]),
                        indicator: "yellow"
                    });
                }
            });
        }    
    },

    is_return(frm) {
        if (frm.doc.is_return) {
            frm.set_df_property("return_against", "label", __("Return Against"));
            frm.set_df_property("return_against", "reqd", 1);
        } else {
            frm.set_df_property("return_against", "reqd", 0);
        }
    },

    is_debit_note(frm) {
        if (frm.doc.is_debit_note) {
            frm.set_df_property("return_against", "label", __("Debit Note Against"));
            frm.set_df_property("return_against", "reqd", 1);
        } else {
            frm.set_df_property("return_against", "reqd", 0);
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
            
            const prepaymentData = await prepayment.fetchPrepaymentData(frm.doc.previous_prepayment);
            prepayment.populatePrepaymentTable(frm, prepaymentData);
            prepayment.calculateAllPrepaymentTotals(frm);
            
        } catch (error) {
            frappe.msgprint(__("Error: {0}", [error.message]));
        } finally {
            frappe.dom.unfreeze();
        }
    },

    adjustment_percentage(frm) {
        if (!prepayment.validateAdjustmentPercentage(frm)) {
            return;
        }

        const factor = prepayment.AdjustmentCalculator.calculateFactor(frm.doc.adjustment_percentage);
        prepayment.AdjustmentCalculator.updatePrepaymentDeductions(frm, factor);
        prepayment.calculateDeductedValues(frm);
    }
});

// ============================================================================
// SALES INVOICE ITEM HANDLERS
// ============================================================================

frappe.ui.form.on("Sales Invoice Item", {
    item_tax_template(frm, cdt, cdn) {
        let item = frappe.get_doc(cdt, cdn);

        if (item.item_tax_template) {
            frappe.db.get_value("Item Tax Template", item.item_tax_template, ["tax_category"]).then(r => {
                frappe.model.set_value(cdt, cdn, "tax_category", r.message.tax_category);
            });
        }
    },
    
    income_account(frm, cdt, cdn) {
        // Preserve custom income_account for advance payment items
        let item = frappe.get_doc(cdt, cdn);
        
        if (item.__preserve_income_account && 
            item.item_code === "advance payment" && 
            PREPAYMENT_TYPES.includes(frm.doc.sales_invoice_type)) {
            
            // If income_account was changed by system, restore our custom value
            if (item.income_account !== item.__preserve_income_account) {
                setTimeout(() => {
                    frappe.model.set_value(cdt, cdn, "income_account", item.__preserve_income_account);
                }, 50);
            }
        }
    }
});
