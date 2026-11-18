import frappe
from frappe.tests import IntegrationTestCase

# The role "All" used to grant read on these doctypes, and "All" includes Website Users.
ZATCA_DOCTYPES = (
    "Commercial Register",
    "Optima Zatca Logs",
    "Optima Zatca Setting",
    "Prepayment Invoice",
    "Tax Exemption",
)
# Read from the Sales Invoice form (frappe.db.get_value / get_doc, item Link fields).
READ_BY_SALES_FORM = ("Commercial Register", "Prepayment Invoice", "Tax Exemption", "Optima Zatca Logs")


class TestZatcaDoctypePermissions(IntegrationTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def _user(self, email, roles, user_type="System User"):
        if not frappe.db.exists("User", email):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": email.split("@")[0],
                    "user_type": user_type,
                    "send_welcome_email": 0,
                    "roles": [{"role": role} for role in roles],
                }
            ).insert(ignore_permissions=True)
        return email

    def test_website_user_reads_no_zatca_doctype(self):
        # Catches a row for "All" (or "Guest") coming back: it exposes ZATCA records to portal users.
        frappe.set_user(self._user("zatca-perm-web@example.com", [], "Website User"))
        for doctype in ZATCA_DOCTYPES:
            self.assertFalse(frappe.has_permission(doctype, "read"), doctype)

    def test_sales_user_reads_what_the_sales_invoice_form_loads(self):
        # Catches a Sales User losing access the Sales Invoice form needs when "All" was removed.
        frappe.set_user(self._user("zatca-perm-sales@example.com", ["Sales User"]))
        for doctype in READ_BY_SALES_FORM:
            self.assertTrue(frappe.has_permission(doctype, "read"), doctype)
        self.assertFalse(frappe.has_permission("Optima Zatca Setting", "read"))

    def test_accounts_user_reads_every_zatca_doctype(self):
        # Catches the invoice submitters (Accounts User) losing read on any ZATCA doctype.
        frappe.set_user(self._user("zatca-perm-accounts@example.com", ["Accounts User"]))
        for doctype in ZATCA_DOCTYPES:
            self.assertTrue(frappe.has_permission(doctype, "read"), doctype)

    def test_vat_details_report_is_not_open_to_all(self):
        roles = {row.role for row in frappe.get_doc("Report", "Zatca VAT Details").roles}
        self.assertNotIn("All", roles)
        self.assertTrue({"Accounts Manager", "Accounts User"} <= roles)
