# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ZatcaMainSettings(Document):
	
	def before_save(self) :

		if self.has_value_changed("phase") :
			frappe.clear_cache()
