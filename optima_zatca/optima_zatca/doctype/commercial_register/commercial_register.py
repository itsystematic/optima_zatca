# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CommercialRegister(Document):

	def validate(self) :
		self.validate_default_value()
	

	def validate_default_value(self) :

		if commercial_register := frappe.db.exists(self.doctype , {"company" : self.company , "is_default" : 1 , "name" : ["!=", self.name]}) :
			frappe.throw(_("There is already a default Commercial Register for this company {0}").format(commercial_register))
