# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""Where one register stands while its certificate is being obtained.

Optima ZATCA already records the *outcome* of onboarding on the setting itself:
``check_csr``, ``check_csid``, the six ``invoice_*`` flags and ``check_pcsid``
between them say how far a register got. What they cannot say is whether it is
moving right now, how far through the current step it is, or why it stopped —
all three of which the progress board has to render.

This document carries that, and only that. It is deliberately derivable-adjacent
rather than authoritative: :func:`stage_map` reads the flags on the setting for
everything that has already happened, and uses its own ``stage`` only to say
which link of the chain is in flight. A run record that goes missing therefore
loses the animation, not the facts.
"""

import frappe
from frappe.model.document import Document

STAGES: tuple[str, ...] = ("keys", "csr", "compliance", "tests", "production")

STATE_IDLE = "idle"
STATE_RUN = "run"
STATE_DONE = "done"
STATE_FAIL = "fail"

STATUS_DRAFT = "draft"
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_LIVE = "live"
STATUS_FAILED = "failed"

#: The six compliance documents ZATCA requires before it will issue production.
DOCUMENT_FLAGS = (
	"invoice_one",
	"invoice_two",
	"invoice_three",
	"invoice_four",
	"invoice_five",
	"invoice_six",
)


def idle_stages() -> dict[str, str]:
	return {stage: STATE_IDLE for stage in STAGES}


class ZatcaOnboardingRun(Document):
	def stage_map(self) -> dict[str, str]:
		"""Each link of the chain, as one of idle / run / done / fail.

		Completion comes from the setting's own flags rather than from this
		record, so a board rendered after a restart still shows what actually
		happened rather than resetting to the beginning.
		"""
		stages = idle_stages()
		settled = completed_stages(self.setting)
		for stage in settled:
			stages[stage] = STATE_DONE

		if self.status == STATUS_FAILED:
			failed = self.error_stage if self.error_stage in stages else self.stage
			if failed in stages and stages[failed] != STATE_DONE:
				stages[failed] = STATE_FAIL
			return stages

		if self.status in (STATUS_QUEUED, STATUS_RUNNING):
			current = self.stage if self.stage in stages else STAGES[0]
			if stages[current] != STATE_DONE:
				stages[current] = STATE_RUN

		return stages

	def document_results(self) -> list[dict]:
		"""Per-document outcomes for the tests stage, newest attempt only.

		Read from the exchange log rather than stored again here: the log is
		already written for every call, and a second copy could disagree with it.
		"""
		if not self.commercial_register:
			return []

		rows = frappe.get_all(
			"Optima Zatca Logs",
			filters={
				"commercial_register": self.commercial_register,
				"method": ["like", "%complainace%"],
			},
			fields=["status", "message", "method"],
			order_by="creation desc",
			limit=len(DOCUMENT_FLAGS),
		)
		return [
			{
				"label": row.get("method") or "document",
				"accepted": row.get("status") == "Success",
				"errors": [row["message"][:300]] if row.get("message") else [],
			}
			for row in rows
		]


def completed_stages(setting: str | None) -> list[str]:
	"""Which links of the chain this register has already finished.

	The single source of truth is the setting, because that is what the rest of
	the app reads when it decides whether a register may sign an invoice.
	"""
	if not setting:
		return []

	values = frappe.db.get_value(
		"Optima Zatca Setting",
		setting,
		["private_key", "csr", "check_csr", "check_csid", "check_pcsid", *DOCUMENT_FLAGS],
		as_dict=True,
	)
	if not values:
		return []

	done: list[str] = []
	if values.get("private_key"):
		done.append("keys")
	if values.get("csr") or values.get("check_csr"):
		done.append("csr")
	if values.get("check_csid"):
		done.append("compliance")
	if all(values.get(flag) for flag in DOCUMENT_FLAGS):
		done.append("tests")
	if values.get("check_pcsid"):
		done.append("production")
	return done


def latest_for(setting: str):
	"""The most recent run for one register, or ``None`` if it has never run."""
	name = frappe.db.get_value(
		"Zatca Onboarding Run", {"setting": setting}, "name", order_by="creation desc"
	)
	return frappe.get_doc("Zatca Onboarding Run", name) if name else None


def unsettled_for_company(company: str) -> bool:
	"""Whether any register of this company is still queued or moving."""
	return bool(
		frappe.db.exists(
			"Zatca Onboarding Run",
			{"company": company, "status": ["in", (STATUS_QUEUED, STATUS_RUNNING)]},
		)
	)
