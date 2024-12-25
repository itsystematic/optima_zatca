# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.model.document import Document

class OptimaZatcaSetting(Document):
	
	@property
	def status(self) :
		return "Connected" if self.check_pcsid == 1 else "Not Connected"
