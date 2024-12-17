import frappe
from frappe import _

def sales_invoice_on_cancel(doc , event) :

    if doc.get("send_to_zatca") and doc.get("clearance_or_reporting") in ["CLEARED" , "REPORTED"]:
        frappe.throw(_("No Permission To Cancel Invoice Sent To Zatca") , title=_("Zatca Permission"))


def sales_invoice_on_trash(doc , event) :

    if doc.get("send_to_zatca") and doc.get("clearance_or_reporting") in ["CLEARED" , "REPORTED"] :
        frappe.throw(_("No Permission To Delete Invoice Sent To Zatca") , title=_("Zatca Permission"))