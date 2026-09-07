"""Server-side field rules, in the same message-key vocabulary as the client.

The interface validates as the operator types, and this validates again on write.
That duplication is deliberate: client validation is a courtesy and can be
bypassed, so the server has to enforce the same rules. Sharing the *keys* is what
keeps the two renderings identical, because both sides look the key up in the same
translation files.

Each function returns a list of field errors rather than raising on the first, so a
form can highlight everything at once instead of one problem per round trip.
"""

from __future__ import annotations

import re
from typing import Any

TIN_LENGTH = 15
CRN_LENGTH = 10
OTP_LENGTH = 6

ARABIC = re.compile(r"[؀-ۿݐ-ݿ]")
DIGITS_ONLY = re.compile(r"^\d*$")
BUILDING = re.compile(r"^\d{4}$")
POSTAL = re.compile(r"^\d{5}$")
VAT_GROUP = re.compile(r"^\d{15}$")


def error(field: str, key: str, **params: Any) -> dict[str, Any]:
    payload = {"field": field, "key": key}
    if params:
        payload["params"] = params
    return payload


# --------------------------------------------------------------------------
# Single values
# --------------------------------------------------------------------------

def tin_problem(value: str) -> tuple[str, dict] | None:
    value = (value or "").strip()
    if not value:
        return ("validation.tin.required", {})
    if not DIGITS_ONLY.match(value):
        return ("validation.digitsOnly", {})
    if len(value) < TIN_LENGTH:
        return ("validation.tin.short", {"count": TIN_LENGTH - len(value), "length": TIN_LENGTH})
    if len(value) > TIN_LENGTH:
        return ("validation.tin.long", {"length": TIN_LENGTH})
    if not re.match(rf"^3\d{{{TIN_LENGTH - 2}}}3$", value):
        return ("validation.tin.brackets", {})
    return None


def crn_problem(value: str) -> tuple[str, dict] | None:
    value = (value or "").strip()
    if not value:
        return ("validation.crn.required", {"count": CRN_LENGTH})
    if not DIGITS_ONLY.match(value):
        return ("validation.digitsOnly", {})
    if len(value) != CRN_LENGTH:
        return ("validation.crn.length", {"count": CRN_LENGTH})
    return None


def legal_name_ar_problem(value: str) -> tuple[str, dict] | None:
    value = (value or "").strip()
    if not value:
        return ("validation.legalName.required", {})
    if not ARABIC.search(value):
        return ("validation.legalName.arabic", {})
    return None


def otp_problem(value: str) -> tuple[str, dict] | None:
    value = (value or "").strip()
    if not value:
        return ("validation.required", {})
    if len(value) != OTP_LENGTH:
        return ("validation.otp.length", {"count": OTP_LENGTH})
    if not DIGITS_ONLY.match(value):
        return ("validation.digitsOnly", {})
    return None


# --------------------------------------------------------------------------
# Composite inputs
# --------------------------------------------------------------------------

def validate_entity(payload: dict) -> list[dict]:
    errors: list[dict] = []
    if not (payload.get("company") or "").strip():
        errors.append(error("company", "validation.company.required"))

    problem = legal_name_ar_problem(payload.get("legalNameAr", ""))
    if problem:
        errors.append(error("legalNameAr", problem[0], **problem[1]))

    problem = tin_problem(payload.get("tin", ""))
    if problem:
        errors.append(error("tin", problem[0], **problem[1]))

    return errors


ADDRESS_RULES = {
    "buildingNumber": lambda v: None if BUILDING.match(v or "")
    else ("validation.required", {}) if not v else ("validation.building.format", {}),
    "street": lambda v: None if (v or "").strip() else ("validation.required", {}),
    "district": lambda v: None if (v or "").strip() else ("validation.required", {}),
    "city": lambda v: None if (v or "").strip() else ("validation.required", {}),
    "postalCode": lambda v: None if POSTAL.match(v or "")
    else ("validation.required", {}) if not v else ("validation.postal.format", {}),
    "additionalNumber": lambda v: None if not v or BUILDING.match(v)
    else ("validation.additional.format", {}),
    "vatGroupNumber": lambda v: None if not v or VAT_GROUP.match(v)
    else ("validation.vatGroup.format", {}),
}


def validate_register(payload: dict, taken_crns: list[str] | None = None) -> list[dict]:
    errors: list[dict] = []

    if not (payload.get("registerName") or "").strip():
        errors.append(error("registerName", "validation.registerName.required"))

    crn = (payload.get("crn") or "").strip()
    problem = crn_problem(crn)
    if problem:
        errors.append(error("crn", problem[0], **problem[1]))
    elif taken_crns and crn in taken_crns:
        errors.append(error("crn", "validation.crn.duplicate"))

    address = payload.get("address") or {}
    for field, rule in ADDRESS_RULES.items():
        problem = rule(str(address.get(field) or ""))
        if problem:
            errors.append(error(field, problem[0], **problem[1]))

    return errors


def validate_otp_entries(entries: list[dict], register_ids: list[str]) -> list[dict]:
    """Every register needs a well-formed code before a run may start."""
    errors: list[dict] = []
    by_register = {entry.get("registerId"): (entry.get("code") or "") for entry in entries}

    for register_id in register_ids:
        problem = otp_problem(by_register.get(register_id, ""))
        if problem:
            errors.append(error(register_id, problem[0], **problem[1]))

    return errors
