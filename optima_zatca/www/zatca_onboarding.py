"""Serve the ZATCA onboarding interface.

The page is the built single-page app. Rendering it through Frappe rather than
handing out a static file is what gives it a session and a CSRF token, which the
whitelisted methods in ``optima_zatca.api`` both require.
"""

from __future__ import annotations

no_cache = 1
sitemap = 0


def get_context(context):
	"""The app owns the whole viewport; the website chrome would only crowd it."""
	import frappe

	# Send a signed-out visitor to the login page and back.
	#
	# Done here rather than with a `login_required` flag, module level or on the
	# context, because a template page honours neither: only web forms and
	# doctype-driven pages read that. Without this a guest is served the shell and
	# every call it makes is refused, which looks like a broken app rather than a
	# session that has expired.
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/zatca-onboarding"
		raise frappe.Redirect

	context.no_cache = 1
	context.no_sidebar = 1
	context.no_breadcrumbs = 1

	# Every write the app makes is a POST to a whitelisted method, and a site with
	# CSRF enforcement refuses those without this token. It is minted here rather
	# than read from the session, because a session that has never needed one does
	# not have one yet and reading it directly would hand the page an empty string
	# that only fails once the operator tries to save something.
	context.csrf_token = frappe.sessions.get_csrf_token()

	# The progress board is pushed to rather than polled. Behind a reverse proxy
	# socket.io is on this origin, but under `bench start` it is a separate port and
	# the page has no other way to find out which.
	context.socketio_port = frappe.conf.socketio_port or ""
	return context
