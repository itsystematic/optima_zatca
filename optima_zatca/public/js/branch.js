frappe.ui.form.on("Branch", {
    refresh (frm) {
        frm.trigger("setup_query_filters");
    },


    setup_query_filters(frm) {

        frm.set_query("commercial_register", () => {
            return {
                filters : {
                    is_main_commercial_register_for_the_company : 0
                }
            }
        })
    }
})