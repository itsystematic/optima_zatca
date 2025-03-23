import frappe
from click import secho

def execute():
    """
    Adding Zatca Manager Role.
    """
    print("Create Zatca Manager Role Patch is running")

    try:
        if not frappe.db.exists("Role", "Zatca Manager"):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": "Zatca Manager",
            }).insert(ignore_permissions=True)
            
            secho("Zatca Manager role added successfully", fg="green")

    except Exception as e:
        secho(f"Error adding ZATCA roles: {str(e)}", fg="red")