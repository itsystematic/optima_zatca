"""Drive one register through the certificate chain, reporting where it is.

Optima ZATCA already knows how to onboard a register: ``add_company_to_zatca``
generates the keys, asks for a compliance certificate, submits the six documents
and collects the production certificate. What it does not do is say *which* of
those it is on, and the onboarding board is built entirely around that question.

So this module sequences the same primitives — ``GenerateCSR``,
``get_certificate``, ``send_sample_sales_invoices``, ``get_production_certificate``
— rather than reimplementing any of them, writing the stage to a
``Zatca Onboarding Run`` between each one. The engine stays exactly where it was;
only the narration is new.

Each register is its own background job, because they are independent: one
register's expired code has nothing to do with the next one's, and a run that
stopped four registers early would be far worse than four separate failures.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from optima_zatca.optima_zatca.doctype.zatca_onboarding_run.zatca_onboarding_run import (
	DOCUMENT_FLAGS,
	STATUS_FAILED,
	STATUS_LIVE,
	STATUS_QUEUED,
	STATUS_RUNNING,
)

#: The realtime event the onboarding board listens on. Optima's own ``zatca``
#: event is published as well, so the desk's existing listeners keep working.
PROGRESS_EVENT = "optima_zatca_run_progress"

QUEUE = "long"
JOB_TIMEOUT = 1500


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def start(company: str, codes: dict[str, str]) -> list[str]:
	"""Queue every register of a company, one job each.

	``codes`` maps a register id to its one-time password.
	"""
	settings = frappe.get_all(
		"Optima Zatca Setting", filters={"company": company}, pluck="name", order_by="creation asc"
	)
	return _enqueue(settings, codes, company=company)


def retry(settings: list[str], codes: dict[str, str]) -> list[str]:
	"""Queue a named subset again, resuming wherever they got to."""
	return _enqueue(settings, codes)


def _enqueue(settings: list[str], codes: dict[str, str], company: str | None = None) -> list[str]:
	queued: list[str] = []
	for setting in settings:
		run = _open_run(setting, company)
		_apply_code(setting, codes.get(setting))
		frappe.enqueue(
			"optima_zatca.api.runner.execute",
			queue=QUEUE,
			timeout=JOB_TIMEOUT,
			setting=setting,
			run=run.name,
			enqueue_after_commit=True,
		)
		queued.append(run.name)
	return queued


def _open_run(setting: str, company: str | None):
	"""Start a fresh run record, carrying the attempt count forward."""
	from optima_zatca.optima_zatca.doctype.zatca_onboarding_run.zatca_onboarding_run import (
		latest_for,
	)

	previous = latest_for(setting)
	values = frappe.db.get_value(
		"Optima Zatca Setting", setting, ["company", "commercial_register"], as_dict=True
	) or {}

	run = frappe.get_doc(
		{
			"doctype": "Zatca Onboarding Run",
			"setting": setting,
			"company": company or values.get("company"),
			"commercial_register": values.get("commercial_register"),
			"status": STATUS_QUEUED,
			"stage": "keys",
			"stage_progress": 0,
			"attempt": int(previous.attempt or 1) + 1 if previous else 1,
			"started_at": now_datetime(),
		}
	)
	run.flags.ignore_permissions = True
	return run.insert(ignore_permissions=True)


def _apply_code(setting: str, code: str | None) -> None:
	"""Put the one-time password where the engine reads it from.

	The reference design keeps a code in memory and forgets it. This app cannot:
	``otp`` is a mandatory field on ``Optima Zatca Setting`` and every one of the
	certificate calls reads it from there. It is written for the attempt and
	overwritten by the next one, so a spent code is never reused, but it is
	stored — which is a property of this schema, not a choice made here.
	"""
	if code:
		frappe.db.set_value("Optima Zatca Setting", setting, "otp", code, update_modified=False)


# --------------------------------------------------------------------------
# The job
# --------------------------------------------------------------------------

def execute(setting: str, run: str) -> None:
	"""Take one register as far along the chain as it can go.

	Every stage is skipped when the setting already records it as done, which is
	what makes a retry resume rather than start again: a register that failed
	while submitting its fourth document keeps its compliance certificate and
	picks up at the documents.
	"""
	doc = frappe.get_doc("Zatca Onboarding Run", run)
	settings = frappe.get_doc("Optima Zatca Setting", setting)
	details: dict = {}

	_set(doc, status=STATUS_RUNNING, stage="keys", stage_progress=5)

	try:
		details = _keys_and_csr(doc, settings)
		settings.reload()

		_compliance(doc, settings, details)
		settings.reload()

		_documents(doc, settings, details)
		settings.reload()

		_production(doc, settings, details)
		settings.reload()

		_set(
			doc,
			status=STATUS_LIVE if settings.check_pcsid else STATUS_FAILED,
			stage="production",
			stage_progress=100,
			settled_at=now_datetime(),
			error_code=None if settings.check_pcsid else "production_not_issued",
		)
		_announce(doc, settings, _("ZATCA setup completed"), "green", 100)

	except Exception as exception:
		_fail(doc, settings, exception)

	finally:
		_settle_company(doc.company)


def _keys_and_csr(doc, settings) -> dict:
	"""Generate the key pair and the signing request.

	``GenerateCSR`` does both in one pass, so the two stages are reported around
	it rather than between: the keys exist by the time it returns, and so does
	the request that carries them.
	"""
	from optima_zatca.zatca.keys import GenerateCSR
	from optima_zatca.zatca.setup import saving_data_to_company
	from optima_zatca.zatca.utils import get_company_data_to_config

	if settings.private_key and settings.csr:
		_set(doc, stage="csr", stage_progress=100)
		return {"csr": settings.csr}

	_set(doc, stage="keys", stage_progress=30)
	_announce(doc, settings, _("Generating keys"), "blue", 10)

	company_info = get_company_data_to_config(settings, {})
	generator = GenerateCSR(settings, frappe.local.site, **company_info)
	details = generator.get_generated_details()

	_set(doc, stage="csr", stage_progress=60)
	saving_data_to_company(settings.name, details)

	_set(doc, stage="csr", stage_progress=100)
	_announce(doc, settings, _("Certificate request prepared"), "blue", 20)
	return details


def _compliance(doc, settings, details: dict) -> None:
	"""Exchange the request and the one-time password for a compliance certificate."""
	from optima_zatca.zatca.setup import get_certificate, saving_data_to_company

	if settings.check_csid:
		return

	_set(doc, stage="compliance", stage_progress=40)
	_announce(doc, settings, _("Requesting compliance certificate"), "blue", 30)

	get_certificate(settings, details.get("csr") or settings.csr, details)
	saving_data_to_company(settings.name, details)

	_set(doc, stage="compliance", stage_progress=100)


def _documents(doc, settings, details: dict) -> None:
	"""Submit the six documents the authority checks before trusting the system."""
	from optima_zatca.zatca.demo import send_sample_sales_invoices
	from optima_zatca.zatca.setup import saving_data_to_company

	if all(settings.get(flag) for flag in DOCUMENT_FLAGS):
		return

	total = len(DOCUMENT_FLAGS)
	_set(doc, stage="tests", stage_progress=0, document_index=1)
	_announce(doc, settings, _("Submitting compliance documents"), "blue", 40)

	def progressed(index: int, count: int, accepted: bool) -> None:
		_set(
			doc,
			stage="tests",
			stage_progress=int(index * 100 / (count or total)),
			document_index=min(index + 1, count or total),
		)
		_announce(
			doc,
			settings,
			_("Document {0} of {1}").format(index, count or total),
			"green" if accepted else "red",
			40 + int(index * 40 / (count or total)),
		)

	send_sample_sales_invoices(settings, details, on_document=progressed)
	saving_data_to_company(settings.name, details)

	settings.reload()
	if not all(settings.get(flag) for flag in DOCUMENT_FLAGS):
		raise ComplianceRejected(
			_("The authority did not accept every compliance document.")
		)

	_set(doc, stage="tests", stage_progress=100, document_index=total)


def _production(doc, settings, details: dict) -> None:
	"""Collect the certificate that makes real invoices count."""
	from optima_zatca.zatca.setup import get_production_certificate, saving_data_to_company

	if settings.check_pcsid:
		return

	_set(doc, stage="production", stage_progress=50)
	_announce(doc, settings, _("Requesting production certificate"), "blue", 90)

	get_production_certificate(settings, details)
	saving_data_to_company(settings.name, details)


class ComplianceRejected(frappe.ValidationError):
	"""At least one of the six documents was refused."""


# --------------------------------------------------------------------------
# Bookkeeping
# --------------------------------------------------------------------------

def _set(doc, **values) -> None:
	"""Write run state and commit, so a watcher sees it while the job continues.

	A background job holds one transaction for its whole life. Without the commit
	the board would learn every stage at once, when the job ended — which is the
	one moment the information is of no use.
	"""
	for field, value in values.items():
		doc.set(field, value)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()


def _fail(doc, settings, exception: Exception) -> None:
	"""Record why this register stopped, in the shape the detail panel renders."""
	frappe.db.rollback()
	doc.reload()

	message = str(exception)
	_set(
		doc,
		status=STATUS_FAILED,
		settled_at=now_datetime(),
		error_code=_code_for(exception, message),
		error_stage=doc.stage,
		error_http_status=_http_status(message),
		error_endpoint=doc.stage,
		error_detail=message[:2000],
	)
	frappe.log_error(
		title=f"ZATCA onboarding failed: {settings.name}", message=frappe.get_traceback()
	)
	_announce(doc, settings, _("ZATCA setup failed: {0}").format(message[:200]), "red", 0)


def _code_for(exception: Exception, message: str) -> str:
	"""Name the failure so the interface can look up words for it.

	Only the cases the interface has copy for are named; everything else is left
	generic rather than invented, because a code the client cannot translate
	renders as the code itself.
	"""
	lowered = message.lower()
	if isinstance(exception, ComplianceRejected):
		return "compliance_rejected"
	if "otp" in lowered or "one-time" in lowered:
		return "otp_invalid"
	if "certificate" in lowered and "expired" in lowered:
		return "certificate_expired"
	if "timed out" in lowered or "timeout" in lowered:
		return "authority_timeout"
	if _http_status(message) in (401, 403):
		return "not_authorised"
	return "authority_error"


def _http_status(message: str) -> int:
	"""Pull a status code out of the authority's reply when it left one there."""
	import re

	found = re.search(r"\b([45]\d{2})\b", message or "")
	return int(found.group(1)) if found else 0


def _announce(doc, settings, message: str, indicator: str, percentage: int) -> None:
	"""Push progress to whoever is watching.

	Two events on purpose. ``zatca`` is what the existing desk screens already
	listen on and keeps working untouched; the board listens on its own event and
	then refetches, because the record is the authority on progress and an event
	that carried its own copy could contradict it.
	"""
	payload = {
		"message": message,
		"indicator": indicator,
		"percentage": percentage,
		"complete": percentage >= 100,
		"commercial_register_name": settings.commercial_register,
		"company": doc.company,
		"register": doc.setting,
		"stage": doc.stage,
		"status": doc.status,
	}
	frappe.publish_realtime("zatca", payload)
	frappe.publish_realtime(PROGRESS_EVENT, payload)


def _settle_company(company: str | None) -> None:
	"""Close the company's setup once no register is still moving."""
	if not company:
		return

	from optima_zatca.optima_zatca.doctype.zatca_onboarding_run.zatca_onboarding_run import (
		unsettled_for_company,
	)
	from optima_zatca.optima_zatca.doctype.zatca_onboarding_setup.zatca_onboarding_setup import (
		STATUS_LIVE as SETUP_LIVE,
		STATUS_PARTIAL,
		for_company,
	)

	if unsettled_for_company(company):
		return

	setup = for_company(company)
	# Per register rather than a bare existence test over every run ever recorded:
	# a failure that has since been superseded by a successful retry must not hold
	# the whole company at "partial" forever.
	failed = any(
		_latest_status(setting) == STATUS_FAILED
		for setting in frappe.get_all(
			"Optima Zatca Setting", filters={"company": company}, pluck="name"
		)
	)

	setup.db_set(
		{
			"status": STATUS_PARTIAL if failed else SETUP_LIVE,
			"completed_at": None if failed else (setup.completed_at or now_datetime()),
		},
		update_modified=True,
	)
	frappe.db.commit()


def _latest_status(setting: str) -> str | None:
	from optima_zatca.optima_zatca.doctype.zatca_onboarding_run.zatca_onboarding_run import (
		latest_for,
	)

	run = latest_for(setting)
	return run.status if run else None
