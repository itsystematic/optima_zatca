import frappe


def add_optima_payment_setting(boot_info):
    boot_info["zatca_phase"] = frappe.db.get_single_value("Zatca Main Settings" , "phase") or "Phase One"