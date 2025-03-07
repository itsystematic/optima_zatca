app_name = "optima_zatca"
app_title = "Optima Zatca"
app_publisher = "IT Systematic"
app_description = "App For Zatca Phase Two"
app_email = "sales@itsystematic.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "optima_zatca",
# 		"logo": "/assets/optima_zatca/logo.png",
# 		"title": "Optima Zatca",
# 		"route": "/optima_zatca",
# 		"has_permission": "optima_zatca.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/optima_zatca/css/optima_zatca.css"
# app_include_js = "/assets/optima_zatca/js/optima_zatca.js"

# include js, css files in header of web template
# web_include_css = "/assets/optima_zatca/css/optima_zatca.css"
# web_include_js = "/assets/optima_zatca/js/optima_zatca.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "optima_zatca/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views

doctype_js = {
    "Company" : "public/js/company.js",
    "Branch" : "public/js/branch.js",
	"Sales Invoice" : "public/js/sales_invoice.js" ,
	"Sales Order" : "public/js/sales_order.js" ,
    "Quotation" : "public/js/quotation.js" ,
	"Delivery Note" : "public/js/delivery_note.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "optima_zatca/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "optima_zatca.utils.jinja_methods",
# 	"filters": "optima_zatca.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "optima_zatca.install.before_install"
# after_install = "optima_zatca.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "optima_zatca.uninstall.before_uninstall"
# after_uninstall = "optima_zatca.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "optima_zatca.utils.before_app_install"
after_app_install = "optima_zatca.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "optima_zatca.utils.before_app_uninstall"
# after_app_uninstall = "optima_zatca.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "optima_zatca.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"on_cancel": "optima_zatca.events.sales_invoice.sales_invoice_on_cancel",
		"on_trash": "optima_zatca.events.sales_invoice.sales_invoice_on_trash",
        "on_submit" : "optima_zatca.events.sales_invoice.sales_invoice_on_submit"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"optima_zatca.tasks.all"
# 	],
# 	"daily": [
# 		"optima_zatca.tasks.daily"
# 	],
# 	"hourly": [
# 		"optima_zatca.tasks.hourly"
# 	],
# 	"weekly": [
# 		"optima_zatca.tasks.weekly"
# 	],
# 	"monthly": [
# 		"optima_zatca.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "optima_zatca.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "optima_zatca.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "optima_zatca.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

ignore_links_on_delete = ["Optima Zatca Logs"]

# Request Events
# ----------------
# before_request = ["optima_zatca.utils.before_request"]
# after_request = ["optima_zatca.utils.after_request"]

# Job Events
# ----------
# before_job = ["optima_zatca.utils.before_job"]
# after_job = ["optima_zatca.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"optima_zatca.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


website_route_rules = [{'from_route': '/zatca-onboarding/<path:app_path>', 'to_route': 'zatca-onboarding'},]

regional_overrides = {
	'Saudi Arabia': {
		'erpnext.controllers.taxes_and_totals.update_itemised_tax_data': 'optima_zatca.zatca.invoice.update_itemised_tax_data'
	}
}


# fixtures = ["Tax Category" , "Tax Exemption" , "Registration Type"]

boot_session = "optima_zatca.startup.boot.add_optima_payment_setting"
