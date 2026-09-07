"""The whitelisted methods the onboarding interface calls.

Every mutation returns the complete setup record, because the client writes the
response straight into its query cache. A method that returned nothing, or a
fragment, would leave the interface showing the previous step's data.

Failures are raised as :class:`ApiError` carrying a message *key* and, where the
problem is in a field, a list of field errors in the same vocabulary the client
validates with. Prose never crosses this boundary.

Guarding is uniform: nothing may be changed while a run is in flight or after the
setup completed. The two exceptions are :func:`retry_registers` and
:func:`finish_with_live`, which exist precisely to resolve a finished run.

A register here is one ``Optima Zatca Setting`` — the pairing of a company with a
commercial register that the rest of Optima ZATCA already signs invoices from. The
wizard creates and edits those documents directly, so a company set up through
this interface is indistinguishable from one set up through the desk.
"""

from __future__ import annotations

import json
import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

from optima_zatca.api import serialise, validation
from optima_zatca.optima_zatca.doctype.zatca_onboarding_setup.zatca_onboarding_setup import (
	STATUS_DRAFT,
	STATUS_LIVE,
	STATUS_PARTIAL,
	STATUS_RUNNING,
	for_company,
)

DEFAULT_COUNTRY = "Saudi Arabia"

#: Optima records the obligation as prose on a single; the wire uses keys.
PHASE_TO_SETTINGS = {"phase_1": "Phase One", "phase_2": "Phase Two"}


class ApiError(frappe.ValidationError):
	"""A failure the interface can render. ``key`` is a message key, not a sentence."""

	def __init__(self, key: str, field_errors: list[dict] | None = None, http_status: int = 400):
		self.key = key
		self.field_errors = field_errors or []
		self.http_status = http_status
		super().__init__(key)


def _fail(key: str, field_errors: list[dict] | None = None, http_status: int = 400):
	"""Raise in a shape Frappe will deliver and the client can parse.

	The payload is put on ``frappe.local.response`` as well as in the exception,
	because Frappe's error envelope does not carry structured data on its own and
	the forms need the field list.
	"""
	frappe.local.response["optima_error"] = {
		"key": key,
		"fieldErrors": field_errors or [],
	}
	frappe.local.response["http_status_code"] = http_status
	raise ApiError(key, field_errors, http_status)


# --------------------------------------------------------------------------
# Context
# --------------------------------------------------------------------------

def _company(explicit: str | None = None) -> str:
	"""Which company this session is setting up.

	An explicit choice wins; otherwise the user's default, then the only company
	on the site. Guessing between several companies would silently configure the
	wrong one, so that case is refused.
	"""
	if explicit:
		return explicit

	default = frappe.defaults.get_user_default("Company")
	if default:
		return default

	companies = frappe.get_all("Company", pluck="name", limit=2)
	if len(companies) == 1:
		return companies[0]
	if not companies:
		_fail("api.noCompany")
	_fail("api.chooseCompany")


def _setup(company: str | None = None):
	return for_company(_company(company))


def _payload(setup) -> dict[str, Any]:
	setup.reload()
	return serialise.setup_payload(setup)


def _as_dict(value: Any) -> dict:
	"""Accept a dict or a JSON string, which is how Frappe delivers nested args."""
	if isinstance(value, str):
		try:
			return json.loads(value)
		except ValueError:
			return {}
	return dict(value or {})


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------

@frappe.whitelist()
def get_setup(company: str | None = None) -> dict:
	"""The single record the whole wizard renders from."""
	return _payload(_setup(company))


@frappe.whitelist()
def get_guidance(company: str | None = None) -> dict:
	"""Explainer copy, served by country so it can differ per mandate."""
	from optima_zatca.api.guidance import guidance_for

	setup = _setup(company)
	return guidance_for(_country_code(setup.company))


@frappe.whitelist()
def get_companies() -> list[dict]:
	"""Companies the operator may set up, and whether tax accounts are configured."""
	companies = frappe.get_all(
		"Company", fields=["name", "default_currency", "country"], order_by="name asc"
	)
	return [
		{
			"name": company.name,
			"linked": _has_tax_configuration(company.name),
			"defaultTin": _company_tax_id(company.name),
			"defaultLegalNameAr": _company_arabic_name(company.name),
			# Carried here so the company can be chosen first and an unsupported
			# one refused at the point of choosing. Discovering it two screens
			# later, after the obligation and scope have been answered, means
			# answering them again for a company that was never going to work.
			"eligible": not _shared_blockers(company.name, company.country),
			"blockers": _shared_blockers(company.name, company.country),
			"status": frappe.db.get_value(
				"Zatca Onboarding Setup", {"company": company.name}, "status"
			)
			or "not_started",
		}
		for company in companies
	]


@frappe.whitelist()
def get_cities(country: str | None = None) -> list[dict]:
	"""Cities already used in addresses, so the operator picks rather than types."""
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT city FROM `tabAddress`
		WHERE IFNULL(city, '') != '' AND (%(country)s IS NULL OR country = %(country)s)
		ORDER BY city ASC
		""",
		{"country": country or DEFAULT_COUNTRY},
		as_dict=True,
	)
	return [{"name": row["city"]} for row in rows]


def _has_tax_configuration(company: str) -> bool:
	return bool(
		frappe.db.exists("Item Tax Template", {"company": company, "disabled": 0})
		and frappe.db.exists("Account", {"company": company, "account_type": "Tax", "is_group": 0})
	)


def _company_tax_id(company: str) -> str:
	return frappe.db.get_value("Company", company, "tax_id") or ""


def _company_arabic_name(company: str) -> str:
	meta = frappe.get_meta("Company")
	if meta.has_field("company_name_in_arabic"):
		return frappe.db.get_value("Company", company, "company_name_in_arabic") or ""
	return ""


def _country_code(company: str) -> str:
	country = frappe.db.get_value("Company", company, "country")
	return (frappe.db.get_value("Country", country, "code") or "sa").upper()


# --------------------------------------------------------------------------
# Decisions
# --------------------------------------------------------------------------

@frappe.whitelist()
def save_mode(phase: str, company: str | None = None) -> dict:
	"""Record which obligation the company is registering for."""
	setup = _setup(company)
	_ensure_editable(setup)

	if phase not in PHASE_TO_SETTINGS:
		_fail("api.fixHighlighted", [validation.error("phase", "validation.required")])

	setup.db_set({"phase": phase, "status": STATUS_DRAFT}, update_modified=True)

	# Mirror the decision onto the single the rest of the app reads, so an invoice
	# submitted after this wizard behaves the way the wizard said it would.
	frappe.db.set_single_value(
		"Zatca Main Settings", "phase", PHASE_TO_SETTINGS[phase], update_modified=True
	)
	return _payload(setup)


@frappe.whitelist()
def save_scope(scope: str, expectedRegisters: int | None = None, company: str | None = None) -> dict:
	"""Record how many registers are in play."""
	setup = _setup(company)
	_ensure_editable(setup)

	if scope not in ("single", "multiple"):
		_fail("api.fixHighlighted", [validation.error("scope", "validation.required")])

	expected = 1 if scope == "single" else (
		int(expectedRegisters) if expectedRegisters else setup.expected_registers
	)
	setup.db_set({"scope": scope, "expected_registers": expected}, update_modified=True)
	return _payload(setup)


@frappe.whitelist()
def save_entity(
	company: str | None = None,
	legalNameAr: str | None = None,
	tin: str | None = None,
) -> dict:
	"""Record the legal identity every register will be certified under."""
	payload = {
		"company": (company or _company(None)).strip(),
		"legalNameAr": legalNameAr,
		"tin": tin,
	}
	errors = validation.validate_entity(payload)
	if errors:
		_fail("api.fixHighlighted", errors)

	setup = for_company(payload["company"])
	_ensure_editable(setup)
	setup.db_set(
		{"legal_name_ar": payload["legalNameAr"].strip(), "tin": payload["tin"].strip()},
		update_modified=True,
	)

	# The certificate carries these, and so does every invoice, so they belong on
	# the company itself rather than only in the wizard's own record.
	values = {"tax_id": payload["tin"].strip()}
	if frappe.get_meta("Company").has_field("company_name_in_arabic"):
		values["company_name_in_arabic"] = payload["legalNameAr"].strip()
	frappe.db.set_value("Company", setup.company, values, update_modified=True)

	_apply_entity_to_registers(setup)
	return _payload(setup)


@frappe.whitelist()
def mark_entity_verified(company: str | None = None) -> dict:
	"""Record that the operator checked the identity against the portal."""
	setup = _setup(company)
	setup.db_set("entity_verified_on", now_datetime(), update_modified=True)
	return _payload(setup)


def _apply_entity_to_registers(setup) -> None:
	"""Push the legal identity onto every register, which is certified under it."""
	for setting in setup.registers():
		frappe.db.set_value(
			"Optima Zatca Setting",
			setting["name"],
			{
				"organization_identifier": setup.tin or "",
				"organization_name": setup.legal_name_ar or "",
			},
			update_modified=True,
		)


# --------------------------------------------------------------------------
# Registers
# --------------------------------------------------------------------------

@frappe.whitelist()
def add_register(
	registerName: str | None = None,
	crn: str | None = None,
	address: Any = None,
	company: str | None = None,
) -> dict:
	"""Add a commercial register, with its own address and certificate."""
	setup = _setup(company)
	_ensure_editable(setup)

	payload = {
		"registerName": registerName,
		"crn": crn,
		"address": _as_dict(address),
	}
	errors = validation.validate_register(payload, _taken_crns(setup))
	if errors:
		_fail("api.fixHighlighted", errors)

	address_name = _create_address(setup, payload)
	register = _create_commercial_register(setup, payload, address_name)
	_create_setting(setup, register, address_name, payload)

	setup.clear_acknowledgement()
	return _payload(setup)


@frappe.whitelist()
def update_register(
	id: str,
	registerName: str | None = None,
	crn: str | None = None,
	address: Any = None,
	company: str | None = None,
) -> dict:
	"""Change a register that has not gone live."""
	setup = _setup(company)
	_ensure_editable(setup)

	if not frappe.db.exists("Optima Zatca Setting", id):
		_fail("api.registerGone", http_status=404)
	if _is_live(id):
		_fail("api.liveNoEdit", http_status=409)

	payload = {
		"registerName": registerName,
		"crn": crn,
		"address": _as_dict(address),
	}
	errors = validation.validate_register(payload, _taken_crns(setup, exclude=id))
	if errors:
		_fail("api.fixHighlighted", errors)

	setting = frappe.get_doc("Optima Zatca Setting", id)
	register = frappe.get_doc("Commercial Register", setting.commercial_register)
	_update_address(register.address or setting.address, setup, payload)

	# The commercial register number is this document's name, so changing it is a
	# rename rather than a field write, and everything pointing at it — the
	# setting, the logs, the invoices already issued — has to follow.
	if register.commercial_register != payload["crn"].strip():
		register = _rename_register(register, payload["crn"].strip())
		setting.reload()

	frappe.db.set_value(
		"Commercial Register",
		register.name,
		{"commercial_register_name": payload["registerName"].strip()},
		update_modified=True,
	)
	frappe.db.set_value(
		"Optima Zatca Setting",
		setting.name,
		{
			"commercial_register": register.name,
			"organization_unit_name": payload["registerName"].strip(),
			"location": payload["address"].get("buildingNumber") or setting.location,
		},
		update_modified=True,
	)

	setup.clear_acknowledgement()
	return _payload(setup)


@frappe.whitelist()
def remove_register(id: str, company: str | None = None) -> dict:
	"""Remove a register that has not gone live."""
	setup = _setup(company)
	_ensure_editable(setup)

	if not frappe.db.exists("Optima Zatca Setting", id):
		_fail("api.registerGone", http_status=404)
	if _is_live(id):
		_fail("api.liveNoRemove", http_status=409)

	register = frappe.db.get_value("Optima Zatca Setting", id, "commercial_register")
	frappe.delete_doc("Optima Zatca Setting", id, force=True, ignore_permissions=True)

	# The commercial register goes too, but only when nothing else is holding it:
	# it may have been created in the desk and be linked from a branch or an
	# invoice, and deleting it would take those with it.
	if register and not frappe.db.exists("Optima Zatca Setting", {"commercial_register": register}):
		try:
			frappe.delete_doc("Commercial Register", register, ignore_permissions=True)
		except frappe.LinkExistsError:
			pass

	setup.clear_acknowledgement()
	return _payload(setup)


@frappe.whitelist()
def set_acknowledged(value: Any = True, company: str | None = None) -> dict:
	"""Record the operator's acknowledgement that the register list is correct."""
	setup = _setup(company)
	_ensure_editable(setup)
	setup.db_set("acknowledged", 1 if frappe.utils.cint(value) else 0, update_modified=True)
	return _payload(setup)


def _taken_crns(setup, exclude: str | None = None) -> list[str]:
	return [
		frappe.db.get_value(
			"Commercial Register", setting["commercial_register"], "commercial_register"
		)
		or ""
		for setting in setup.registers()
		if setting["name"] != exclude and setting.get("commercial_register")
	]


def _environment_for(setup) -> str:
	"""The environment a new register onboards against.

	Read from the registers already set up rather than assumed. Defaulting to
	production would send a taxpayer's first attempt at the real authority with a
	code generated for testing, and the failure it produces says only that the
	code is invalid, which sends people looking in the wrong place entirely.
	"""
	return serialise.site_environment(setup) or "sandbox"


def _address_values(setup, payload: dict) -> dict:
	address = payload["address"]
	return {
		"address_title": f"{setup.company} {payload['registerName']}".strip()[:140],
		"address_type": "Billing",
		"address_line1": address.get("street") or "",
		"address_line2": address.get("additionalNumber") or "",
		"city": address.get("city") or "",
		"pincode": address.get("postalCode") or "",
		"country": frappe.db.get_value("Company", setup.company, "country") or DEFAULT_COUNTRY,
		"building_no": address.get("buildingNumber") or "",
		"district": address.get("district") or "",
	}


def _create_address(setup, payload: dict) -> str:
	doc = frappe.get_doc({"doctype": "Address", **_address_values(setup, payload)})
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	return doc.insert(ignore_permissions=True).name


def _update_address(address_name: str | None, setup, payload: dict) -> None:
	if not address_name:
		return
	frappe.db.set_value(
		"Address", address_name, _address_values(setup, payload), update_modified=True
	)


def _create_commercial_register(setup, payload: dict, address_name: str):
	doc = frappe.get_doc(
		{
			"doctype": "Commercial Register",
			"company": setup.company,
			"commercial_register": payload["crn"].strip(),
			"commercial_register_name": payload["registerName"].strip(),
			"address": address_name,
		}
	)
	doc.flags.ignore_permissions = True
	return doc.insert(ignore_permissions=True, ignore_if_duplicate=True)


def _create_setting(setup, register, address_name: str, payload: dict) -> str:
	"""Create the document the rest of Optima ZATCA signs invoices from."""
	doc = frappe.get_doc(
		{
			"doctype": "Optima Zatca Setting",
			"company": setup.company,
			"commercial_register": register.name,
			"address": address_name,
			"organization_identifier": setup.tin or "",
			"organization_name": setup.legal_name_ar or "",
			"organization_unit_name": payload["registerName"].strip(),
			"location": payload["address"].get("buildingNumber") or "",
			"registration_type": "CRN",
			"country_name": "SA",
			"industry": "Commercial",
			"invoice_type": "1100",
			"api_endpoints": _environment_for(setup),
			# Mandatory in this schema and replaced by the real code the moment a
			# run starts; a placeholder here keeps the document insertable while
			# the operator is still filling the list in.
			"otp": "000000",
		}
	)
	doc.flags.ignore_permissions = True
	return doc.insert(ignore_permissions=True, ignore_if_duplicate=True).name


def _rename_register(register, crn: str):
	"""Give a commercial register its new number, carrying every link with it."""
	frappe.db.set_value(
		"Commercial Register", register.name, "commercial_register", crn, update_modified=True
	)
	renamed = frappe.rename_doc(
		"Commercial Register", register.name, crn, force=True, ignore_permissions=True
	)
	return frappe.get_doc("Commercial Register", renamed)


def _is_live(setting: str) -> bool:
	"""Whether this register already holds a production certificate."""
	return bool(frappe.db.get_value("Optima Zatca Setting", setting, "check_pcsid"))


# --------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------

@frappe.whitelist()
def submit_otp(entries: Any, company: str | None = None) -> dict:
	"""Start onboarding every register, one background job each."""
	setup = _setup(company)
	_ensure_editable(setup)

	registers = setup.registers()
	if not registers:
		_fail("api.otpAll")

	if not setup.acknowledged:
		_fail("api.fixHighlighted", [validation.error("acknowledged", "validation.required")])

	if setup.phase == "phase_1":
		return _complete_phase_one(setup)

	parsed = entries if isinstance(entries, list) else json.loads(entries or "[]")
	register_ids = [setting["name"] for setting in registers]
	errors = validation.validate_otp_entries(parsed, register_ids)
	if errors:
		_fail("api.otpAll", errors)

	codes = {entry["registerId"]: entry["code"] for entry in parsed}

	from optima_zatca.api import runner

	setup.db_set(
		{
			"status": STATUS_RUNNING,
			"started_at": now_datetime(),
			"completed_at": None,
			"reference": setup.reference or _reference(setup),
		},
		update_modified=True,
	)
	runner.start(setup.company, codes)
	return _payload(setup)


def _complete_phase_one(setup) -> dict:
	"""Finish a phase one setup without contacting the authority.

	Phase one puts a QR code on the printed invoice and transmits nothing. There
	is no certificate to obtain, so there is nothing for a one-time password to
	authorise, and asking for one would send the operator to the portal for a code
	that is never used.
	"""
	now = now_datetime()
	setup.db_set(
		{
			"status": STATUS_LIVE,
			"started_at": setup.started_at or now,
			"completed_at": now,
			"reference": setup.reference or _reference(setup),
		},
		update_modified=True,
	)
	return _payload(setup)


@frappe.whitelist()
def retry_registers(ids: Any, entries: Any = None, company: str | None = None) -> dict:
	"""Retry the registers that failed, resuming where a certificate already exists."""
	setup = _setup(company)
	targets = ids if isinstance(ids, list) else json.loads(ids or "[]")
	if not targets:
		_fail("api.nothingToRetry", http_status=409)

	failed = [name for name in targets if _has_failed(name)]
	if not failed:
		_fail("api.nothingToRetry", http_status=409)

	parsed = entries if isinstance(entries, list) else json.loads(entries or "[]")
	codes = {entry["registerId"]: entry["code"] for entry in parsed}

	from optima_zatca.api import runner

	setup.db_set({"status": STATUS_RUNNING, "completed_at": None}, update_modified=True)
	runner.retry(failed, codes)
	return _payload(setup)


@frappe.whitelist()
def finish_with_live(company: str | None = None) -> dict:
	"""Accept the run as it stands, leaving any failed register to be dealt with later."""
	setup = _setup(company)

	from optima_zatca.optima_zatca.doctype.zatca_onboarding_run.zatca_onboarding_run import (
		unsettled_for_company,
	)

	if unsettled_for_company(setup.company):
		_fail("api.stillRunning", http_status=409)

	setup.db_set(
		{
			"completed_at": setup.completed_at or now_datetime(),
			"status": STATUS_LIVE if not _any_failed(setup) else STATUS_PARTIAL,
		},
		update_modified=True,
	)
	return _payload(setup)


def _has_failed(setting: str) -> bool:
	from optima_zatca.optima_zatca.doctype.zatca_onboarding_run.zatca_onboarding_run import (
		latest_for,
	)

	run = latest_for(setting)
	return bool(run and run.status == "failed")


def _any_failed(setup) -> bool:
	return any(_has_failed(setting["name"]) for setting in setup.registers())


def _reference(setup) -> str:
	"""A short support reference, stable once minted."""
	return f"SETUP-{frappe.generate_hash(setup.name, 4).upper()}"


def _ensure_editable(setup) -> None:
	if setup.status == STATUS_RUNNING:
		_fail("api.alreadyRunning", http_status=409)
	if setup.completed_at:
		_fail("api.alreadyComplete", http_status=409)


@frappe.whitelist()
def get_register_log(register: str, limit: int = 50) -> list[dict]:
	"""The authority exchanges for one register, oldest first.

	Shaped for reading rather than for machines: the operation in plain words, the
	outcome, how long it took, and the authority's own message when it refused.
	The signed document is deliberately absent; it is large, it is already on the
	log record, and nobody diagnosing a rejection is reading base64.
	"""
	commercial_register = frappe.db.get_value(
		"Optima Zatca Setting", register, "commercial_register"
	) or register

	rows = frappe.get_all(
		"Optima Zatca Logs",
		filters={"commercial_register": commercial_register},
		fields=["name", "creation", "environment", "api_endpoint", "method", "status", "message"],
		order_by="creation asc",
		limit=int(limit),
	)
	return [
		{
			"id": row["name"],
			"at": serialise.iso(row["creation"]),
			"environment": row["environment"] or "production",
			"operation": row["method"] or row["api_endpoint"] or "request",
			"outcome": _outcome(row["status"]),
			"httpStatus": _status_code(row.get("message")),
			"durationMs": None,
			"message": _log_message(row),
		}
		for row in rows
	]


#: Optima records three outcomes; the wire has four, the fourth being a call that
#: never came back at all. Nothing writes a log row in that case, so it is absent
#: here by construction rather than by omission.
OUTCOMES = {"Success": "ok", "Warning": "ok", "Failed": "rejected"}


def _outcome(status: str | None) -> str:
	return OUTCOMES.get(status or "", "error")


def _status_code(message: str | None) -> int | None:
	found = re.search(r"\b([1-5]\d{2})\b", message or "")
	return int(found.group(1)) if found else None


def _log_message(row: dict) -> str | None:
	"""What the authority actually said, when it is worth repeating."""
	body = row.get("message") or ""
	if not body:
		return None
	if row.get("status") == "Success":
		return None

	try:
		parsed = json.loads(body)
	except ValueError:
		return body[:300] or None

	validation_results = (parsed or {}).get("validationResults") or {}
	messages = [
		entry.get("message", "")
		for entry in validation_results.get("errorMessages", [])
		if isinstance(entry, dict)
	]
	if messages:
		return "; ".join(messages)[:300]
	return str(parsed.get("message") or parsed)[:300]


# --------------------------------------------------------------------------
# Which obligations this company can actually register for
# --------------------------------------------------------------------------

@frappe.whitelist()
def get_phase_options(company: str | None = None) -> list[dict]:
	"""What each obligation requires, and whether this company can choose it.

	Two kinds of finding, and the difference matters.

	A **blocker** is something this system checked and found wanting. It disables
	the choice, and it names a fix the operator can carry out.

	A **note** is a condition the system cannot verify. Whether a taxpayer has
	been called up for phase two is decided by the authority and communicated
	directly to them; nothing in an accounting system knows it. Presenting that as
	though it had been checked would be inventing a fact about someone's tax
	position, so it is stated as something for them to confirm instead.
	"""
	name = _company(company)
	country = frappe.db.get_value("Company", name, "country")
	shared = _shared_blockers(name, country)

	return [
		{
			"phase": "phase_1",
			"eligible": not shared,
			"blockers": shared,
			"notes": [],
			"recommended": False,
		},
		{
			"phase": "phase_2",
			"eligible": not shared,
			"blockers": shared,
			"notes": [{"key": "eligibility.note.waveIsAuthorityAssigned"}],
			# Recommended only when the company already looks like a going
			# concern for it, and the interface is told exactly which fact
			# justified that rather than being handed a slogan.
			"recommended": not shared and _looks_established(name),
			"recommendedBecause": (
				"eligibility.because.registeredAndConfigured"
				if not shared and _looks_established(name)
				else None
			),
		},
	]


def _shared_blockers(company: str, country: str | None) -> list[dict]:
	"""Conditions that stop this company registering for anything at all."""
	blockers: list[dict] = []

	code = frappe.db.get_value("Country", country, "code") if country else None
	if not code:
		blockers.append({"key": "eligibility.blocker.noCountry", "params": {"company": company}})
	elif code.upper() != "SA":
		# Optima ZATCA implements one mandate. Letting a company from elsewhere
		# through would produce certificates against an authority that has never
		# heard of it.
		blockers.append(
			{"key": "eligibility.blocker.countryUnsupported", "params": {"country": country}}
		)

	if not _has_tax_configuration(company):
		blockers.append({"key": "eligibility.blocker.noTaxAccounts", "params": {"company": company}})

	return blockers


def _looks_established(company: str) -> bool:
	"""Whether the company already carries a well formed tax registration.

	A weak signal deliberately: it says the company is set up to charge VAT, which
	is the only part of the question this system can answer for itself.
	"""
	tax_id = (_company_tax_id(company) or "").strip()
	return bool(tax_id) and bool(re.match(r"^3\d{13}3$", tax_id))
