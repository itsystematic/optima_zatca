/**
 * ZATCA Buttons Module - Optima ZATCA
 * Handles ZATCA-related button functionality:
 * - Send to ZATCA button (Phase Two compliance)
 * - Generate PDF/A-3 button (for invoices sent to ZATCA)
 * - Button visibility and permission management
 */

frappe.provide("optima_zatca.sales_invoice.zatca");

// ============================================================================
// ZATCA SUBMISSION
// ============================================================================

Object.assign(optima_zatca.sales_invoice.zatca, {
    
    /**
     * Add "Send To Zatca" button to form
     */
    addZatcaButton(frm) {
        if (frm.is_new() || frm.doc.sent_to_zatca == 1 || frappe.boot.zatca_phase == "Phase One") return;
        
        frm.add_custom_button(__("Send To Zatca"), function () {
            if (frm.is_dirty()) {
                frappe.throw(__("Please save first."));
            }

            frappe.call({
                method: "optima_zatca.zatca.invoice.send_to_zatca",
                args: {
                    sales_invoice_name: frm.doc.name
                },
                is_async: true,
                freeze: true,
                freeze_message: __("Sending Invoice {0} to Zatca", [frm.doc.name]),
                callback(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __("Invoice sumbitted successfully"),
                            indicator: "green"
                        });
                        frm.reload_doc();
                    }
                }
            });
        }).css({
            "background-color": "#0b002e",
            "color": "white"
        });
    },

    /**
     * Add "Generate PDF/A-3" button to form
     */
    addPdfA3Button(frm) {
        // Show button only when invoice was sent to ZATCA
        if (frm.is_new() || !frm.doc.sent_to_zatca) return;
        
        frm.page.add_menu_item(__("Generate PDF/A-3"), function () {
            if (frm.is_dirty()) {
                frappe.throw(__("Please save the document first."));
            }

            frappe.dom.freeze(__("Generating PDF/A-3..."));

            frappe.call({
                method: "optima_zatca.zatca.pdfa3.generate_pdfa3_for_invoice",
                args: {
                    sales_invoice_name: frm.doc.name,
                },
                callback: function(r) {
                    frappe.dom.unfreeze();
                    
                    if (r.message && r.message.file_url) {
                        // Open PDF in new tab
                        window.open(r.message.file_url, '_blank');
                        
                        // Show success message with settings used
                        const settings_info = r.message.settings_used;
                        frappe.show_alert({
                            message: __('PDF/A-3 generated with: Print Format: {0}, Letterhead: {1}, Language: {2}', [
                                settings_info.print_format,
                                settings_info.letterhead || 'None',
                                settings_info.language
                            ]),
                            indicator: 'green'
                        }, 5);
                        
                        // Reload to show attached file
                        frm.reload_doc();
                    }
                },
                error: function(r) {
                    frappe.dom.unfreeze();
                }
            });
        }).css({
            "background-color": "#0066cc",
            "color": "white"
        }), true;
    },

    /**
     * Remove/hide "Send To Zatca" button if user lacks permission
     */
    removeSendToZatcaButton(frm) {
        // Check if user has access
        if (frappe.user.has_role('Zatca Role')) return;
        
        // Select Send To Zatca Button
        const btn = $('[data-label="Send%20To%20Zatca"]');
        
        // Delete all event listeners and hide
        btn.off();
        btn.hide();
        
        // Add custom event listener showing permission error
        btn.click(() => {
            frappe.msgprint('You have NO Permission for send to Zatca , Please Try to Connect with your Manager');
        });
    }
});

// ============================================================================
// EVENT HANDLERS
// ============================================================================

/**
 * Setup ZATCA button event handlers on Sales Invoice form
 */
frappe.ui.form.on("Sales Invoice", {
    add_zatca_button(frm) {
        optima_zatca.sales_invoice.zatca.addZatcaButton(frm);
    },

    add_pdfa3_button(frm) {
        optima_zatca.sales_invoice.zatca.addPdfA3Button(frm);
    },

    remove_send_to_zatca_button(frm) {
        optima_zatca.sales_invoice.zatca.removeSendToZatcaButton(frm);
    }
});
