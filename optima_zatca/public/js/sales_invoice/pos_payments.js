/**
 * POS Payments Module - Optima ZATCA
 * Handles POS payment amount calculation override for adjustment invoices
 * 
 * Key Feature:
 * For Adjustment/Final Adjustment invoice types, payment amount should be:
 *   amount = outstanding_amount - deducted_grand_total
 * 
 * This ensures the POS payment reflects the net amount after prepayment deductions.
 */

frappe.provide("optima_zatca.sales_invoice.pos");

// ============================================================================
// POS PAYMENT CALCULATION
// ============================================================================

Object.assign(optima_zatca.sales_invoice.pos, {
    
    /**
     * Calculate target paid amount considering deducted grand total for adjustment types
     */
    getTargetPaidAmount(frm) {
        const ADJUSTMENT_TYPES = optima_zatca.sales_invoice.prepayment.ADJUSTMENT_TYPES;
        
        // For adjustment types: net payable = grand_total - deducted_grand_total
        if (ADJUSTMENT_TYPES.includes(frm.doc.sales_invoice_type)) {
            const net_payable = flt(frm.doc.grand_total || 0) - flt(frm.doc.deducted_grand_total || 0);
            
            // Prevent negative payable for non-returns
            if (!cint(frm.doc.is_return) && net_payable < 0) return 0;
            
            return net_payable;
        }
        
        // Default ERPNext behavior
        return flt(frm.doc.paid_amount || 0) || flt(frm.doc.grand_total || 0);
    },

    /**
     * Recalculate POS payment amounts based on Optima rules
     */
    recalculatePayments(frm) {
        if (!cint(frm.doc.is_pos) || !frm.doc.payments || !frm.doc.payments.length) return;

        // Prevent recursive triggers
        if (frm.__optima_recalc_payments) return;
        frm.__optima_recalc_payments = true;

        try {
            const target = optima_zatca.sales_invoice.pos.getTargetPaidAmount(frm);
            const ADJUSTMENT_TYPES = optima_zatca.sales_invoice.prepayment.ADJUSTMENT_TYPES;

            // Sync paid_amount for adjustment types
            if (ADJUSTMENT_TYPES.includes(frm.doc.sales_invoice_type)) {
                frm.set_value("paid_amount", target);

            // Single payment row: set full amount
                if (frm.doc.payments.length === 1) {
                    const row = frm.doc.payments[0];
                    frappe.model.set_value(row.doctype, row.name, "amount", target);
                    return;
                }
            
                // Multiple rows: distribute proportionally
                optima_zatca.sales_invoice.pos.distributePaymentAmounts(frm, target);
            }
        } finally {
            frm.__optima_recalc_payments = false;
        }
    },

    /**
     * Distribute payment amounts proportionally across multiple rows
     */
    distributePaymentAmounts(frm, target) {
        const current_total = (frm.doc.payments || []).reduce((s, r) => s + flt(r.amount), 0);

        if (current_total > 0) {
            // Proportional distribution
            let running = 0;
            frm.doc.payments.forEach((r, idx) => {
                let next = (flt(r.amount) / current_total) * target;

                // Last row absorbs rounding difference
                if (idx === frm.doc.payments.length - 1) next = target - running;
                running += next;

                frappe.model.set_value(r.doctype, r.name, "amount", next);
            });
        } else {
            // Put all on first row if no amounts set
            const first = frm.doc.payments[0];
            frappe.model.set_value(first.doctype, first.name, "amount", target);
            
            for (const r of frm.doc.payments.slice(1)) {
                frappe.model.set_value(r.doctype, r.name, "amount", 0);
            }
        }
    }
});

// ============================================================================
// EVENT HANDLERS
// ============================================================================

/**
 * Setup event handlers for POS payment recalculation
 */
frappe.ui.form.on("Sales Invoice", {
    deducted_grand_total(frm) {
        optima_zatca.sales_invoice.pos.recalculatePayments(frm);
    },

    adjustment_percentage(frm) {
        optima_zatca.sales_invoice.pos.recalculatePayments(frm);
    },

    grand_total(frm) {
        optima_zatca.sales_invoice.pos.recalculatePayments(frm);
    },

    paid_amount(frm) {
        optima_zatca.sales_invoice.pos.recalculatePayments(frm);
    },

    payments_add(frm) {
        optima_zatca.sales_invoice.pos.recalculatePayments(frm);
    },

    payments_remove(frm) {
        optima_zatca.sales_invoice.pos.recalculatePayments(frm);
    }
});

/**
 * Sales Invoice Payment child table handlers
 */
frappe.ui.form.on("Sales Invoice Payment", {    
    mode_of_payment(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.mode_of_payment) return;

        const ADJUSTMENT_TYPES = optima_zatca.sales_invoice.prepayment.ADJUSTMENT_TYPES;
        let final_amount = flt(frm.doc.outstanding_amount);

        if (ADJUSTMENT_TYPES.includes(frm.doc.sales_invoice_type)) {
            final_amount = flt(frm.doc.outstanding_amount) - flt(frm.doc.deducted_grand_total);
        }

        if (flt(row.amount) !== final_amount) {
            frappe.model.set_value(cdt, cdn, "amount", final_amount);
        }
    }
});
