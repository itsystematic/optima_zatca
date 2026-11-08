"""Host page for the ZATCA onboarding SPA built from zatca-onboarding/ into www/zatca-onboarding.html."""

import json

import frappe
from frappe.translate import get_all_translations
from frappe.utils.jinja_globals import is_rtl

no_cache = 1
sitemap = 0


def get_context(context):
	# A template page ignores `login_required`, so both redirects are done by hand.
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/zatca-onboarding"
		raise frappe.Redirect
	if frappe.session.data.user_type != "System User":
		frappe.local.flags.redirect_location = "/"
		raise frappe.Redirect

	# Minting a CSRF token writes the session, and a GET is only committed when asked to.
	frappe.local.flags.commit = True
	lang = frappe.local.lang
	boot = {
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
		# Behind nginx socket.io shares the page's origin; `bench start` serves it on its own port.
		"socketio_port": frappe.conf.socketio_port if frappe._dev_server else None,
		"lang": lang,
		"rtl": is_rtl(),
		"translations": get_all_translations(lang) if lang != "en" else {},
	}
	# The JSON sits inside a <script> element, which a "</" in any translation would close.
	context.boot_json = json.dumps(boot, ensure_ascii=False).replace("</", "<\\/")
	return context
