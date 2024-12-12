
import frappe


def make_action_log(**kwargs) :
    new_log = frappe.new_doc("Optima Zatca Logs")
    new_log.update(kwargs)
    new_log.save(ignore_permissions=True)
