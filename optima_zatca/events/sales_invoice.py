import frappe
from frappe import _

def sales_invoice_on_cancel(doc , event) :

    enable_cancel_invoice = frappe.db.get_single_value("Zatca Main Settings" , "enable_cancel_invoice")
    
    if doc.get("send_to_zatca") and doc.get("clearance_or_reporting") in ["CLEARED" , "REPORTED"] and not enable_cancel_invoice :
        frappe.throw(_("No Permission To Cancel Invoice Sent To Zatca") , title=_("Zatca Permission"))


def sales_invoice_on_trash(doc , event) :

    enable_delete_invoice = frappe.db.get_single_value("Zatca Main Settings" , "enable_delete_invoice")

    if doc.get("send_to_zatca") and doc.get("clearance_or_reporting") in ["CLEARED" , "REPORTED"] and not enable_delete_invoice :
        frappe.throw(_("No Permission To Delete Invoice Sent To Zatca") , title=_("Zatca Permission"))