

frappe.ui.form.on("Sales Order" , {
    refresh(frm) {
        frm.set_query("tax_exemption" , "items" , (doc ,cdt,cdn) => {
            let row = frappe.get_doc(cdt ,cdn) ;
            return {
                filters : {
                    code : row.tax_category 
                }
            }
        })

        // Add custom button for Advance Sales Invoice
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Advance Sales Invoice'), function() {
                frappe.model.open_mapped_doc({
                    method: "optima_zatca.zatca.sales_order.make_advance_sales_invoice",
                    frm: frm
                });
            }, __('Create'));
        }
    }
})



frappe.ui.form.on("Sales Order Item" , {
    item_tax_template(frm ,cdt ,cdn) {
        let item = frappe.get_doc(cdt ,cdn) ;

        if (item.item_tax_template) {
            frappe.db.get_value("Item Tax Template", item.item_tax_template, ["tax_category"]).then(r => {
                frappe.model.set_value(cdt ,cdn , "tax_category" , r.message.tax_category)
            })
        }
    }
})