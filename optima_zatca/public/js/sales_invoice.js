



erpnext.accounts.SalesInvoiceController = class SalesInvoiceController extends erpnext.accounts.SalesInvoiceController {
    add_taxes_from_item_tax_template(item_tax_map) {
		let me = this;

		if(item_tax_map && cint(frappe.defaults.get_default("add_taxes_from_item_tax_template"))) {
			if(typeof (item_tax_map) == "string") {
				item_tax_map = JSON.parse(item_tax_map);
			}

			$.each(item_tax_map, function(tax, rate) {
				let found = (me.frm.doc.taxes || []).find(d => d.account_head === tax);
				if(!found) {
					let child = frappe.model.add_child(me.frm.doc, "taxes");
					child.charge_type = "On Net Total";
					child.account_head = tax;
					child.rate = 0;
				}
			});
		}
	}
}



frappe.ui.form.on("Sales Invoice" , {
    refresh(frm) {
        frm.trigger("add_zatca_button") ;
        frm.trigger("setup_query_filters") ;
    },


    add_zatca_button(frm) {
        if ( frm.is_new() ) return ;
        
        frm.add_custom_button(__("Send To Zatca"), function () {
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
            "background-color" : "red",
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
    },

    async commercial_register(frm) {
        let company_address = "";

        if (frm.doc.commercial_register) {
            let commercial_register = await frappe.db.get_value("Commercial Register", frm.doc.commercial_register, ["address"]) ;
            company_address = commercial_register.message ? commercial_register.message.address : "";
        }
        frm.set_value("company_address" , company_address) ;
    }
})

