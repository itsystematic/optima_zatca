"""optima_zatca's Arabic must load after the apps it translates. This only warns; it never reorders."""

import frappe

MUST_LOAD_BEFORE = ("frappe", "erpnext", "hrms")


def problems(apps):
	"""Messages for an installed-apps order that would hide optima_zatca's Arabic."""
	if "optima_zatca" not in apps:
		return []

	found = []
	position = apps.index("optima_zatca")
	late = [app for app in MUST_LOAD_BEFORE if app in apps and apps.index(app) > position]
	if late:
		found.append(
			f"optima_zatca loads before {', '.join(late)}, so their translations override its Arabic. "
			f"Installed order: {', '.join(apps)}. Move optima_zatca after them in Installed Applications."
		)
	if "daad" in apps:
		found.append(
			"DaaD is installed next to optima_zatca. optima_zatca already carries all the Arabic and the "
			"Almarai font, and DaaD sets its own --font-stack. Uninstall daad from this site."
		)
	return found


def check_load_order():
	"""after_migrate: report problems in the Error Log and on the console. Returns them."""
	found = problems(frappe.get_installed_apps())
	for message in found:
		frappe.log_error(title="optima_zatca Arabic load order", message=message + " Nothing was changed.")
		print(f"WARNING: {message}")
	return found
