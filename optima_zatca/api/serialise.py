"""Turn Optima ZATCA's documents into the wire shapes the onboarding interface expects.

The interface's contract is camelCase and deliberately free of Frappe concepts, so
the translation happens here rather than leaking field names into the client. Two
rules hold throughout.

Errors are message *keys*, never sentences. The client looks the key up in its own
translations, so a server that returns prose produces untranslated, unstyled text.

Progress is structured, not narrated. The server says which stage is moving and how
far through it is; the interface writes the sentence. That is what lets the status
column translate without the backend knowing a language.

The mapping onto Optima's own schema is:

    Register            one ``Optima Zatca Setting`` (a company + a commercial register)
    crn / name / address the linked ``Commercial Register`` and its ``Address``
    environment         the setting's ``api_endpoints``
    the five stages     ``private_key``, ``csr``, ``check_csid``, the six
                        ``invoice_*`` flags, ``check_pcsid``
    certificate         the X.509 details already extracted onto the setting
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import get_datetime, now_datetime

from optima_zatca.optima_zatca.doctype.zatca_onboarding_run.zatca_onboarding_run import (
	STAGES,
	idle_stages,
	latest_for,
)

REGISTER_STATUS_DRAFT = "draft"
DEFAULT_COUNTRY = "Saudi Arabia"


def iso(value: Any) -> str | None:
	"""Render a datetime as ISO 8601, or ``None`` when it is unset."""
	if not value:
		return None
	return get_datetime(value).isoformat()


# --------------------------------------------------------------------------
# Address and register
# --------------------------------------------------------------------------

def address_payload(address_name: str | None) -> dict[str, str]:
	"""The address grid's fields, with the country the server owns."""
	empty = {
		"buildingNumber": "",
		"street": "",
		"district": "",
		"city": "",
		"postalCode": "",
		"country": DEFAULT_COUNTRY,
		"additionalNumber": "",
		"vatGroupNumber": "",
	}
	if not address_name:
		return empty

	address = frappe.db.get_value(
		"Address",
		address_name,
		["address_line1", "address_line2", "city", "pincode", "country",
		 "building_no", "district"],
		as_dict=True,
	)
	if not address:
		return empty

	return {
		"buildingNumber": address.get("building_no") or "",
		"street": address.get("address_line1") or "",
		"district": address.get("district") or "",
		"city": address.get("city") or "",
		"postalCode": address.get("pincode") or "",
		"country": address.get("country") or DEFAULT_COUNTRY,
		"additionalNumber": address.get("address_line2") or "",
		"vatGroupNumber": "",
	}


def register_payload(setting: dict, index: int, setup=None) -> dict[str, Any]:
	"""One register, including its run and certificate when they exist."""
	run = latest_for(setting["name"])
	register = _commercial_register(setting.get("commercial_register"))

	return {
		"id": setting["name"],
		"index": index,
		"environment": setting.get("api_endpoints") or None,
		"registerName": register.get("commercial_register_name") or "",
		"crn": register.get("commercial_register") or "",
		# The address hangs off the commercial register, which is where the rest
		# of the app reads it from when it builds an invoice. The copy on the
		# setting is a convenience link to the same document.
		"address": address_payload(register.get("address") or setting.get("address")),
		"status": _register_status(setting, run, setup),
		"run": run_payload(run) if run else None,
		"certificate": certificate_payload(setting["name"]),
	}


def _commercial_register(name: str | None) -> dict:
	if not name:
		return {}
	return (
		frappe.db.get_value(
			"Commercial Register",
			name,
			["commercial_register", "commercial_register_name", "address"],
			as_dict=True,
		)
		or {}
	)


def _register_status(setting: dict, run, setup=None) -> str:
	"""What this register's row says.

	A register that already holds a production certificate is live whether or not
	a run record survives to say so — the certificate is the fact, and the run is
	only the story of how it was obtained.

	Phase one is the exception, because it obtains no certificate at all: it puts
	a QR code on the printed invoice and transmits nothing. Judging it by
	`check_pcsid` left every register of a finished phase one setup reading
	"draft", which told the operator the thing they had just completed had not
	started — and left the summary offering to open a run that was never queued.
	"""
	if setup is not None and setup.phase == "phase_1":
		return "live" if setup.completed_at else REGISTER_STATUS_DRAFT

	if setting.get("check_pcsid"):
		return "live"
	if run:
		return run.status
	return REGISTER_STATUS_DRAFT


def certificate_payload(setting: str) -> dict[str, Any] | None:
	"""Only the fingerprint and validity. Secrets never cross this boundary."""
	values = frappe.db.get_value(
		"Optima Zatca Setting",
		setting,
		["check_pcsid", "serial_number509", "certificate_hash", "modified"],
		as_dict=True,
	)
	if not values or not values.get("check_pcsid"):
		return None

	digest = values.get("serial_number509") or values.get("certificate_hash")
	if not digest:
		return None

	return {
		"fingerprint": _fingerprint(digest),
		# ZATCA states the validity window in the certificate itself; nothing on
		# the setting records it, and inventing dates would be worse than saying
		# nothing, because an operator would plan a renewal around them.
		"issuedAt": iso(values.get("modified")),
		"validTo": None,
	}


def _fingerprint(digest: str) -> str:
	"""A short, readable form of the certificate digest."""
	import base64

	try:
		decoded = base64.b64decode(digest).decode()
	except Exception:
		decoded = str(digest)
	compact = decoded[:32].upper()
	return " ".join(compact[i : i + 4] for i in range(0, len(compact), 4))


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------

def run_payload(run) -> dict[str, Any]:
	"""Where one register stands, in the structured shape the interface renders."""
	stages = run.stage_map() if run else idle_stages()
	stage = run.stage if run.stage in STAGES else STAGES[0]

	started = get_datetime(run.started_at) if run.started_at else None
	settled = get_datetime(run.settled_at) if run.settled_at else None
	reference = settled or now_datetime()
	elapsed = int((reference - started).total_seconds()) if started else 0

	payload = {
		"stages": stages,
		"stageProgress": int(run.stage_progress or 0) if stages.get(stage) == "run" else 0,
		"stage": stage,
		"stageIndex": STAGES.index(stage) + 1,
		"elapsedSeconds": max(0, elapsed),
		"error": error_payload(run),
	}
	if run.document_index:
		payload["testInvoice"] = int(run.document_index)
	return payload


def error_payload(run) -> dict[str, Any] | None:
	"""The failure, keyed by code so the interface supplies the words."""
	if not run.error_code:
		return None
	return {
		"code": run.error_code,
		"httpStatus": int(run.error_http_status or 0),
		"endpoint": run.error_endpoint or "",
		"requestId": run.name,
		"attempt": int(run.attempt or 1),
		"maxAttempts": int(run.attempt or 1),
		"occurredAt": iso(run.settled_at) or iso(run.modified),
		"details": _error_details(run),
	}


def _error_details(run) -> dict[str, str]:
	details: dict[str, str] = {}
	if run.error_stage:
		details["stage"] = run.error_stage
	if run.error_detail:
		details["detail"] = str(run.error_detail)[:600]
	for result in run.document_results():
		if not result.get("accepted"):
			details[result.get("label", "document")] = "; ".join(
				result.get("errors") or ["rejected"]
			)
	return details


# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------

def setup_payload(setup) -> dict[str, Any]:
	"""The single record the whole wizard renders from."""
	registers = setup.registers()
	return {
		"id": setup.name,
		"company": setup.company,
		"environment": site_environment(setup),
		"status": setup.status,
		"step": setup.resume_step(),
		"phase": setup.phase or None,
		"scope": setup.scope or None,
		"entity": entity_payload(setup),
		"entityVerifiedOn": iso(setup.entity_verified_on),
		"expectedRegisters": setup.expected_registers or None,
		"registers": [
			register_payload(setting, index, setup)
			for index, setting in enumerate(registers, start=1)
		],
		"acknowledged": bool(setup.acknowledged),
		"reference": setup.reference or None,
		"startedAt": iso(setup.started_at),
		"completedAt": iso(setup.completed_at),
		"modified": iso(setup.modified),
	}


def entity_payload(setup) -> dict[str, str] | None:
	if not (setup.legal_name_ar and setup.tin):
		return None
	return {
		"company": setup.company,
		"legalNameAr": setup.legal_name_ar,
		"tin": setup.tin,
	}


def site_environment(setup) -> str | None:
	"""Which authority this company registers against, or ``None`` when unset.

	Taken from the registers themselves, because in this app the environment is a
	property of each ``Optima Zatca Setting`` rather than a site-wide switch. When
	they disagree there is no single honest answer, so none is given.

	Deliberately not defaulted. Telling an operator they are on production when
	nobody has said so would have them believe their invoices count; an absent
	value the interface can render as nothing is the honest answer.
	"""
	environments = {
		setting.get("api_endpoints")
		for setting in setup.registers()
		if setting.get("api_endpoints")
	}
	return environments.pop() if len(environments) == 1 else None
