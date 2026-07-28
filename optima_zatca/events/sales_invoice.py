import io
import os
from base64 import b64encode
from pyqrcode import create as qr_create

import frappe
from frappe import _
from frappe.utils import getdate, get_time, add_to_date

from erpnext import get_region


SAUDI_REGION = "Saudi Arabia"
PHASE_ONE = "Phase One"
# ZATCA-accepted states: a cleared (B2B) or reported (B2C) invoice is final.
CLEARED_OR_REPORTED = ("CLEARED", "REPORTED")

# What on_submit should do about ZATCA state before touching the QR.
SUBMIT_ACTION_GENERATE = "generate"  # proceed to (region-gated) Phase-1 QR
SUBMIT_ACTION_SKIP = "skip"          # already sent to ZATCA — nothing to do
SUBMIT_ACTION_BLOCK = "block"        # Phase Two, not yet reported — disallow submit


# ================================================================================================
# ENTRY POINTS (Sales Invoice doc_events)
# ================================================================================================


def sales_invoice_before_cancel(doc, event):
    enable_cancel_invoice = frappe.db.get_single_value("Zatca Main Settings", "enable_cancel_invoice")
    if _decide_cancel_blocked(doc, enable_cancel_invoice):
        frappe.throw(_("No Permission To Cancel Invoice Sent To Zatca"), title=_("Zatca Permission"))


def sales_invoice_on_trash(doc, event):
    enable_delete_invoice = frappe.db.get_single_value("Zatca Main Settings", "enable_delete_invoice")
    if _decide_delete_blocked(doc, enable_delete_invoice):
        frappe.throw(_("No Permission To Delete Invoice Sent To Zatca"), title=_("Zatca Permission"))


def sales_invoice_on_submit(doc, event):
    phase = frappe.db.get_single_value("Zatca Main Settings", "phase")
    action = _decide_submit_action(doc, phase)
    if action == SUBMIT_ACTION_SKIP:
        return
    if action == SUBMIT_ACTION_BLOCK:
        frappe.throw(_("Invoice Not Reported Yet"), title=_("Zatca Error"))

    if get_region(doc.company) != SAUDI_REGION:
        return

    # QR already attached (e.g. a re-submit) — don't regenerate.
    if doc.ksa_einv_qr and frappe.db.exists("File", {"file_url": doc.ksa_einv_qr}):
        return

    inputs = _collect_phase_one_qr_inputs(doc)
    base64_string = _build_phase_one_tlv_base64(*inputs)
    _write_qr_file(doc, base64_string)


# ================================================================================================
# CANCEL / DELETE GUARDS
# ================================================================================================
# A finalized ZATCA invoice may not be cancelled or deleted unless the matching global override
# is enabled — otherwise the local document would drift from what ZATCA holds.


def _is_sent_and_finalized(doc):
    """True when the invoice was sent to ZATCA and is cleared or reported."""
    return bool(doc.get("sent_to_zatca")) and doc.get("clearance_or_reporting") in CLEARED_OR_REPORTED


def _decide_cancel_blocked(doc, enable_cancel_invoice):
    return _is_sent_and_finalized(doc) and not enable_cancel_invoice


def _decide_delete_blocked(doc, enable_delete_invoice):
    return _is_sent_and_finalized(doc) and not enable_delete_invoice


# ================================================================================================
# SUBMIT PHASE GUARD
# ================================================================================================
# Phase One generates a QR at submit for every invoice. Phase Two forbids submitting an invoice
# that hasn't been cleared/reported first (that happens via the "Send to ZATCA" flow, not here),
# and skips QR generation entirely once the invoice has been sent.


def _decide_submit_action(doc, phase):
    if phase == PHASE_ONE:
        return SUBMIT_ACTION_GENERATE
    if doc.get("sent_to_zatca") == 1:
        return SUBMIT_ACTION_SKIP
    if doc.get("clearance_or_reporting") not in CLEARED_OR_REPORTED:
        return SUBMIT_ACTION_BLOCK
    return SUBMIT_ACTION_GENERATE


# ================================================================================================
# PHASE-ONE TLV QR
# ================================================================================================
# Builds the ZATCA Phase-1 (simplified invoice) QR: a base64-encoded TLV buffer of five tags —
# seller name, VAT number, timestamp, invoice total, VAT total — rendered to an attached PNG.


def _collect_phase_one_qr_inputs(doc):
    """Gather the five TLV values from the invoice and its company, raising the
    same user-facing errors as before when a mandatory company field is unset."""
    seller_name = frappe.db.get_value("Company", doc.company, "company_name_in_arabic")
    if not seller_name:
        frappe.throw(_("Arabic name missing for {} in the company document").format(doc.company))

    tax_id = frappe.db.get_value("Company", doc.company, "tax_id")
    if not tax_id:
        frappe.throw(_("Tax ID missing for {} in the company document").format(doc.company))

    timestamp = _posting_timestamp(doc)
    invoice_amount = str(doc.grand_total)
    vat_amount = str(_sum_vat_amount(doc))
    return seller_name, tax_id, timestamp, invoice_amount, vat_amount


def _posting_timestamp(doc):
    """ZATCA timestamp: posting date + posting time as UTC ISO-8601."""
    posting_date = getdate(doc.posting_date)
    time = get_time(doc.posting_time)
    seconds = time.hour * 60 * 60 + time.minute * 60 + time.second
    return add_to_date(posting_date, seconds=seconds).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sum_vat_amount(doc):
    """Total VAT across the invoice's tax rows whose account is a company VAT
    account, rejecting a duplicated rate (which would double-count the tax)."""
    accounts_type_tax = frappe.get_list(
        "Item Tax Template",
        {"company": doc.company, "disabled": 0},
        ["`tabItem Tax Template Detail`.tax_type"],
        join="Left join",
    )
    tax_accounts = list(map(lambda x: x.get("tax_type"), accounts_type_tax))
    vat_amount_row = list(filter(lambda x: x.get("account_head") in tax_accounts, doc.taxes))

    total_vat_amount = 0
    taxes_rate = []
    for tax in vat_amount_row:
        if tax.get("rate") in taxes_rate:
            frappe.throw(_("VAT {} is Duplicated in Document {}").format(tax.get("rate"), doc.name))
        total_vat_amount += tax.get("tax_amount")
        taxes_rate.append(tax.get("rate"))
    return total_vat_amount


def _tlv_field(tag_number, value, length):
    """One TLV triplet (tag, length, value) as a hex string.

    ``length`` is passed in rather than derived so each field keeps its original
    byte computation exactly (tag 1 counts UTF-8 bytes; the rest count string
    length — identical for the ASCII fields). ``bytes([length])`` still caps a
    field at 255 bytes, as it always has.
    """
    tag = bytes([tag_number]).hex()
    length_hex = bytes([length]).hex()
    value_hex = value.encode("utf-8").hex()
    return "".join([tag, length_hex, value_hex])


def _build_phase_one_tlv_base64(seller_name, tax_id, timestamp, invoice_amount, vat_amount):
    """Assemble the five-tag TLV buffer and base64-encode it (pure)."""
    tlv_array = [
        _tlv_field(1, seller_name, len(seller_name.encode("utf-8"))),
        _tlv_field(2, tax_id, len(tax_id)),
        _tlv_field(3, timestamp, len(timestamp)),
        _tlv_field(4, invoice_amount, len(invoice_amount)),
        _tlv_field(5, vat_amount, len(vat_amount)),
    ]
    tlv_buff = "".join(tlv_array)
    return b64encode(bytes.fromhex(tlv_buff)).decode()


def _write_qr_file(doc, base64_string):
    """Render the QR PNG, attach it to the invoice, and store its URL."""
    qr_image = io.BytesIO()
    url = qr_create(base64_string, error="L")
    url.png(qr_image, scale=2, quiet_zone=1)

    name = frappe.generate_hash(doc.name, 5)
    filename = f"QRCode-{name}.png".replace(os.path.sep, "__")
    _file = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": filename,
            "is_private": 0,
            "content": qr_image.getvalue(),
            "attached_to_doctype": doc.get("doctype"),
            "attached_to_name": doc.get("name"),
            "attached_to_field": "ksa_einv_qr",
        }
    )
    _file.save()

    doc.db_set("ksa_einv_qr", _file.file_url)
    doc.notify_update()
