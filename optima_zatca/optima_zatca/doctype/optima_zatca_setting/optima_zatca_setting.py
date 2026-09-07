# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.model.document import Document
from optima_zatca.zatca.classes.validate import validate_tax_id_in_saudia_arabia

class OptimaZatcaSetting(Document):

	def validate(self) :
		validate_tax_id_in_saudia_arabia(self.organization_identifier)

	@property
	def status(self) :
		return "Connected" if self.check_pcsid == 1 else "Not Connected"
