# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from optima_zatca.zatca.classes.validate import validate_tax_id_in_saudia_arabia


class OptimaZatcaSetting(Document):
	"""One commercial register's device in one ZATCA environment.

	A register may hold a setting per environment, side by side; the one ticked Use for Invoices
	signs its invoices.
	"""

	def validate(self):
		validate_tax_id_in_saudia_arabia(self.organization_identifier)
		self.validate_one_setting_per_environment()
		self.validate_use_for_invoices()

	def on_update(self):
		if self.use_for_invoices:
			frappe.db.set_value(
				self.doctype,
				{"commercial_register": self.commercial_register, "use_for_invoices": 1, "name": ["!=", self.name]},
				"use_for_invoices",
				0,
			)

	def validate_one_setting_per_environment(self):
		other = frappe.db.exists(self.doctype, {
			"commercial_register": self.commercial_register,
			"api_endpoints": self.api_endpoints,
			"name": ["!=", self.name],
		})
		if other:
			frappe.throw(_("Commercial register {0} already has a setting in the {1} environment: {2}").format(
				self.commercial_register, self.api_endpoints, other
			))

	def validate_use_for_invoices(self):
		if self.use_for_invoices and self.has_value_changed("use_for_invoices") and not self.check_pcsid:
			frappe.throw(_("Only a setting with a production CSID can be used for invoices"))

	@property
	def status(self) :
		return "Connected" if self.check_pcsid == 1 else "Not Connected"


def on_doctype_update():
	frappe.db.add_unique("Optima Zatca Setting", ["commercial_register", "api_endpoints"])
