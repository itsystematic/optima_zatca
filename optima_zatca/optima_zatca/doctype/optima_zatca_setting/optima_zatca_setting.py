# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.model.document import Document

class OptimaZatcaSetting(Document):
	pass

	# def validate(self) :
	# 	self.validate_company_data()
	# 	self.validate_tax_id()


	# def validate_company_data(self) :

	# 	fields = [
	# 		"company" ,"otp","organization_identifier","country_name" ,
	# 		"organization_unit_name", "oganization_name","commercial_register" ,
	# 		"address" , "location" , "industry" , "invoice_type" , "registration_type" ,
	# 		"certificate" , "public_key" , "secret" , "request_id"
	# 	]

	# 	for fn in fields :
	# 		if self.get(fn)  in ["",None]  :
	# 			frappe.throw(_("Please Enter {0}").format(self.meta.get_label(fn)))


	# def validate_tax_id(self) :
	# 	validate_tax_id_in_saudia_arabia(self.organization_identifier)





