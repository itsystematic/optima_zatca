/**
 * Prepayment Module - Optima ZATCA
 * Handles all prepayment invoice logic including:
 * - Prepayment invoice setup and validation
 * - Adjustment calculations and percentage management
 * - Prepayment data fetching and table population
 * - Totals calculation for prepayments and adjustments
 */

frappe.provide("optima_zatca.sales_invoice.prepayment");

// ============================================================================
// CONSTANTS
// ============================================================================

optima_zatca.sales_invoice.prepayment.PREPAYMENT_TYPES = ["Initial Prepayment", "Prepayment"];
optima_zatca.sales_invoice.prepayment.ADJUSTMENT_TYPES = ["Adjustment", "Final Adjustment"];

// ============================================================================
// CORE PREPAYMENT METHODS
// ============================================================================

Object.assign(optima_zatca.sales_invoice.prepayment, {
    
    /**
     * Automatically sets previous prepayment for return invoices
     */
    setPreviousPrepayment: async (frm) => {
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
    },

    /**
     * Check if previous prepayment should be automatically set
     */
    shouldSetPreviousPrepayment: (doc) => {
        return doc.is_return && 
               !doc.previous_prepayment && 
               doc.sales_invoice_type !== "Normal";
    },

    /**
     * Fetch prepayment data from server
     */
    fetchPrepaymentData: (prepaymentInvoice) => {
        return frappe.call({
            method: "optima_zatca.zatca.utils.get_prepayment_details",
            args: { prepayment_invoice: prepaymentInvoice, filters: {} }
        }).then(r => r.message || []);
    },

    /**
     * Populate prepayment child table with fetched data
     */
    populatePrepaymentTable: (frm, data) => {
        frm.clear_table('prepayments_invcoies');
        
        data.forEach(prepayment => {
            const row = frm.add_child('prepayments_invcoies');
            optima_zatca.sales_invoice.prepayment.assignPrepaymentFields(row, prepayment);
        });
        
        frm.refresh_field('prepayments_invcoies');
    },

    /**
     * Assign prepayment fields from data to child table row
     */
    assignPrepaymentFields: (row, prepayment) => {
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
    },

    calculateAllPrepaymentTotals: (frm) => {
        [
            optima_zatca.sales_invoice.prepayment.calculatePrepaymentTotals,
            optima_zatca.sales_invoice.prepayment.calculateAdjustmentTotals,
            optima_zatca.sales_invoice.prepayment.calculateRemainingPercentage,
            optima_zatca.sales_invoice.prepayment.calculateAdjustmentPercentage,
            optima_zatca.sales_invoice.prepayment.calculateDeductedValues
        ].forEach(fn => fn(frm));

        // Runs last because it reads total_grands, which is set synchronously by
        // calculatePrepaymentTotals above — no deferral needed.
        optima_zatca.sales_invoice.prepayment.calculateMaxAdjustmentLimit(frm);
    },

    /**
     * Setup advance payment invoice form
     */
    handleAdvancePaymentInvoice: (frm) => {
        optima_zatca.sales_invoice.prepayment.clearChildTables(frm);
        
        const item_row = frm.add_child("items", {
            item_code: "advance payment",
            qty: 1,
            conversion_factor: 1.0,
            price_list_rate: 0,
        });

        optima_zatca.sales_invoice.prepayment.fetchAdvancePaymentItemDetails(frm, item_row).then(() => {
            frm.set_value("update_stock", 0);
            optima_zatca.sales_invoice.prepayment.refreshFormFields(frm);
        });
    },

    /**
     * Fetch item details for advance payment item
     */
    fetchAdvancePaymentItemDetails: (frm, item_row) => {
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
                    const custom_income_account = r.message.income_account;
                    
                    Object.assign(item_row, r.message);
                    item_row.rate = 0;
                    item_row.price_list_rate = 0;
                    item_row.__preserve_income_account = custom_income_account;
                    
                    optima_zatca.sales_invoice.prepayment.triggerTaxRefresh(frm, item_row);
                    
                    setTimeout(() => {
                        frappe.model.set_value(item_row.doctype, item_row.name, "income_account", custom_income_account);
                        frm.refresh_field("items");
                        resolve();
                    }, 200);
                }
            });
        });
    },

    clearChildTables: (frm) => {
        frm.clear_table("items");
        frm.clear_table("taxes");
        
        frm.set_value("total", 0);
        frm.set_value("net_total", 0);
        frm.set_value("grand_total", 0);
        frm.set_value("outstanding_amount", 0);
        frm.set_value("total_taxes_and_charges", 0);
    },

    refreshFormFields: (frm) => {
        ["items", "taxes", "total", "grand_total"].forEach(field => {
            frm.refresh_field(field);
        });
    },

    triggerTaxRefresh: (frm, item_row) => {
        frm.script_manager.trigger("item_code", item_row.doctype, item_row.name);
    }
});

// ============================================================================
// TOTALS CALCULATION
// ============================================================================

/**
 * Factory function to create total calculators
 */
optima_zatca.sales_invoice.prepayment.createTotalsCalculator = (filterTypes, fieldMapping) => (frm) => {
    const totals = frm.doc.prepayments_invcoies
        .filter(row => filterTypes.includes(row.prepayment_type))
        .reduce((acc, row) => ({
            taxable: acc.taxable + (row.deducted_taxable_amount || 0),
            tax: acc.tax + (row.deducted_tax_amount || 0),
            grand: acc.grand + (row.deducted_grand_total || 0)
        }), { taxable: 0, tax: 0, grand: 0 });

    frm.set_value(fieldMapping(totals));
};


optima_zatca.sales_invoice.prepayment.calculatePrepaymentTotals = 
    optima_zatca.sales_invoice.prepayment.createTotalsCalculator(
        optima_zatca.sales_invoice.prepayment.PREPAYMENT_TYPES,
        (totals) => ({
            "total_taxable_amount": totals.taxable,
            "total_tax_amount": totals.tax,
            "total_grands": totals.grand
        })
    );


optima_zatca.sales_invoice.prepayment.calculateAdjustmentTotals = 
    optima_zatca.sales_invoice.prepayment.createTotalsCalculator(
        optima_zatca.sales_invoice.prepayment.ADJUSTMENT_TYPES,
        (totals) => ({
            "adjustment_taxable_amount": totals.taxable,
            "adjustment_tax_amount": totals.tax,
            "adjustment_grands": totals.grand
        })
    );


optima_zatca.sales_invoice.prepayment.calculateDeductedValues = 
    optima_zatca.sales_invoice.prepayment.createTotalsCalculator(
        optima_zatca.sales_invoice.prepayment.PREPAYMENT_TYPES,
        (totals) => ({
            "deducted_tax_amount": totals.tax,
            "deducted_taxable_amount": totals.taxable,
            "deducted_grand_total": totals.grand
        })
    );

// ============================================================================
// ADJUSTMENT CALCULATION
// ============================================================================

optima_zatca.sales_invoice.prepayment.validateAdjustmentPercentage = (frm) => {
    const adjustmentPercentage = frm.doc.adjustment_percentage || 0;
    
    if (adjustmentPercentage <= 0 && !frm.doc.is_return) {
        frappe.msgprint({
            title: __('Invalid Adjustment Percentage'),
            message: __('Adjustment percentage must be greater than 0'),
            indicator: 'red'
        });
        frm.set_value('adjustment_percentage', 0);
        return false;
    }
    
    return true;
};


optima_zatca.sales_invoice.prepayment.AdjustmentCalculator = {
    calculateFactor(adjustmentPercentage) {
        return (adjustmentPercentage / 100) || 1;
    },

    updatePrepaymentDeductions(frm, factor) {
        const PREPAYMENT_TYPES = optima_zatca.sales_invoice.prepayment.PREPAYMENT_TYPES;
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

// ============================================================================
// PERCENTAGE CALCULATIONS
// ============================================================================

optima_zatca.sales_invoice.prepayment.calculateRemainingPercentage = (frm) => {
    let remainingPercentage;

    if (frm.doc.is_return) {
        remainingPercentage = optima_zatca.sales_invoice.prepayment.getReturnRemainingPercentage(frm);
    } 
    else if (optima_zatca.sales_invoice.prepayment.isNoPrepaymentScenario(frm)) {
        remainingPercentage = 100;
    } 
    else {
        remainingPercentage = optima_zatca.sales_invoice.prepayment.calculateRemainingFromUsedPercentages(frm);
    }
    
    frm.set_value("remaining_percentage", remainingPercentage);
    return remainingPercentage;
};


optima_zatca.sales_invoice.prepayment.getReturnRemainingPercentage = (frm) => {
    if (frm.doc.prepayments_invcoies && frm.doc.prepayments_invcoies.length > 0) {
        return frm.doc.prepayments_invcoies[0].remaining_percentage || 0;
    }
    return 0;
};


optima_zatca.sales_invoice.prepayment.isNoPrepaymentScenario = (frm) => {
    return !frm.doc.previous_prepayment || 
           !frm.doc.prepayments_invcoies || 
           frm.doc.prepayments_invcoies.length === 0;
};

// Remaining % = 100 − Σ(adjustment % already consumed by earlier prepayments in
// the chain). The rows come from get_prepayment_details (the persisted Prepayment
// Invoice records), so this sum is only as precise as the stored percentages —
// keep Prepayment Invoice.adjustment_percentage at 9 dp or the result quantizes
// (see _build_prepayment_payload in zatca/prepayment_invoice.py).
optima_zatca.sales_invoice.prepayment.calculateRemainingFromUsedPercentages = (frm) => {
    const totalUsedPercentage = frm.doc.prepayments_invcoies.reduce((total, row) => {
        return total + (row.adjustment_percentage || 0);
    }, 0);

    const remainingPercentage = 100 - totalUsedPercentage;
    return Math.max(0, remainingPercentage);
};

/**
 * Calculate adjustment percentage.
 *
 * A Final Adjustment settles whatever is left of the prepayment chain, so its
 * percentage is auto-filled to the remaining % (100 − Σ previous adjustments)
 * and locked. A return copies the percentage from the invoice it reverses.
 */
optima_zatca.sales_invoice.prepayment.calculateAdjustmentPercentage = (frm) => {
    if (frm.doc.sales_invoice_type === "Final Adjustment") {
        optima_zatca.sales_invoice.prepayment.updateAndLockAdjustmentPercentage(frm, frm.doc.remaining_percentage || 0);
    }

    if (frm.doc.is_return) {
        if (frm.doc.prepayments_invcoies && frm.doc.prepayments_invcoies.length > 0) {
            const adjustmentPercentage = frm.doc.prepayments_invcoies[0].adjustment_percentage || 0;
            optima_zatca.sales_invoice.prepayment.updateAndLockAdjustmentPercentage(frm, adjustmentPercentage);
        }
    }
};

optima_zatca.sales_invoice.prepayment.updateAndLockAdjustmentPercentage = (frm, percentage) => {
    frm.set_value("adjustment_percentage", percentage);
    frm.events.adjustment_percentage(frm);
    frm.set_df_property("adjustment_percentage", "read_only", true);
};


optima_zatca.sales_invoice.prepayment.calculateMaxAdjustmentLimit = (frm) => {
    const grandTotal = Math.abs(frm.doc.base_grand_total || frm.doc.grand_total) || 0;
    const totalGrands = Math.abs(frm.doc.total_grands) || 0;
    
    const calculatedLimit = totalGrands === 0 ? 0 : (grandTotal * 100) / totalGrands;
    const maxAdjustmentLimit = Math.max(0, Math.min(100, calculatedLimit));
    
    frm.set_value("max_adjustment_limit", maxAdjustmentLimit);
};
