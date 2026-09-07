# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""The onboarding wizard's own state, one record per company.

The wizard's decisions do not belong on any single register: the phase and the
scope are company-wide, and the acknowledgement covers the whole register list.
Keeping them here means a half-finished setup survives a reload, a new browser or
a different operator, which is the property the wizard's step guard depends on.

The registers themselves stay where the rest of Optima ZATCA already keeps them —
one ``Optima Zatca Setting`` per commercial register. This record holds only what
has nowhere else to live.

``step`` is derived rather than stored as an intention. What the operator may open
is a question about what has actually been filled in, so recomputing it on every
read cannot drift out of step with the data.
"""

import frappe
from frappe import _
from frappe.model.document import Document

STATUS_NOT_STARTED = "not_started"
STATUS_DRAFT = "draft"
STATUS_RUNNING = "running"
STATUS_PARTIAL = "partial"
STATUS_LIVE = "live"

STEP_ORDER = (
	"mode",
	"scope",
	"entity",
	"registers",
	"review",
	"otp",
	"progress",
	"done",
)


class ZatcaOnboardingSetup(Document):
	def validate(self):
		self.step = self.resume_step()

	# -- derived state ---------------------------------------------------

	def registers(self) -> list[dict]:
		"""The company's registers, in the order they were added.

		One row per ``Optima Zatca Setting``: that document is the pairing of a
		company with a commercial register, which is exactly what a register is
		to this wizard.
		"""
		return frappe.get_all(
			"Optima Zatca Setting",
			filters={"company": self.company},
			fields=[
				"name",
				"commercial_register",
				"api_endpoints",
				"address",
				"check_csr",
				"check_csid",
				"check_pcsid",
				"creation",
			],
			order_by="creation asc",
		)

	def resume_step(self) -> str:
		"""Where the operator should pick up.

		Not the same question as what they are allowed to open. Having said to
		expect five registers and entered three, the natural place to resume is the
		register form even though the review page is perfectly reachable.
		"""
		if self.completed_at:
			return "done"
		if self.status in (STATUS_RUNNING, STATUS_PARTIAL):
			return "progress"
		if not self.phase:
			return "mode"
		if not self.scope:
			return "scope"
		if not (self.legal_name_ar and self.tin):
			return "entity"

		count = len(self.registers())
		if count == 0:
			return "registers"
		if self.expected_registers and count < self.expected_registers:
			return "registers"
		if not self.acknowledged:
			return "review"
		return "otp"

	def clear_acknowledgement(self) -> None:
		"""Drop the acknowledgement because the register list changed underneath it.

		The operator acknowledged a specific list. Changing it invalidates that,
		and the review page gates submission on the flag.
		"""
		if self.acknowledged:
			self.db_set("acknowledged", 0, update_modified=False)
			self.acknowledged = 0

	# -- guards ----------------------------------------------------------

	def ensure_editable(self) -> None:
		"""Refuse a change while a run is in flight or after it finished."""
		if self.status == STATUS_RUNNING:
			frappe.throw(_("api.alreadyRunning"), exc=frappe.ValidationError)
		if self.completed_at:
			frappe.throw(_("api.alreadyComplete"), exc=frappe.ValidationError)


def for_company(company: str, create: bool = True) -> ZatcaOnboardingSetup:
	"""Return the company's setup record, creating an empty one on first use."""
	name = frappe.db.get_value("Zatca Onboarding Setup", {"company": company}, "name")
	if name:
		return frappe.get_doc("Zatca Onboarding Setup", name)
	if not create:
		frappe.throw(_("No ZATCA onboarding setup exists for {0}.").format(company))

	doc = frappe.get_doc(
		{
			"doctype": "Zatca Onboarding Setup",
			"company": company,
			"status": STATUS_NOT_STARTED,
		}
	)
	doc.flags.ignore_permissions = True
	return doc.insert(ignore_permissions=True)
