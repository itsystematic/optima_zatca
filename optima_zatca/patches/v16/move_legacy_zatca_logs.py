"""Move the logs of the optima app's old ZATCA integration into Optima Zatca Logs, then drop their table.

Before optima_zatca, the optima app sent invoices to ZATCA itself and logged each call in its own
Zatca Logs doctype. Those rows are the only record of what that integration sent. handle_optima_zatca
was meant to copy them, but it was listed in patches.txt only from 29 to 31 December 2024, so most
sites still hold them there alone.

The table is read directly, not through the doctype: once optima stops shipping Zatca Logs, Frappe
deletes the DocType record at the end of a migrate but leaves the table and its rows.
"""

import json

import frappe

LEGACY_DOCTYPE = "Zatca Logs"
BATCH_SIZE = 500
SAMPLE_INVOICE_METHOD = "send_sample_sales_invoices"
COPIED_FIELDS = (
    "status",
    "method",
    "message",
    "reference_doctype",
    "reference_name",
    "company",
    "uuid",
    "pih",
    "icv",
    "hash",
    "qr_code",
    "invoice",
    "owner",
    "creation",
)


def execute():
    if not frappe.db.table_exists(LEGACY_DOCTYPE, cached=False):
        return

    for rows in _legacy_batches():
        for log in _logs_to_copy(rows, _creations_already_copied(rows)):
            frappe.get_doc(log).insert(ignore_permissions=True, ignore_links=True, set_name=log["name"])
        frappe.db.commit()

    frappe.delete_doc("DocType", LEGACY_DOCTYPE, force=True, ignore_missing=True)
    frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{LEGACY_DOCTYPE}`")


# ====================================================================================================
# WHAT EACH LEGACY ROW BECOMES

def _logs_to_copy(rows, copied_creations) -> list[dict]:
    """Every row not copied yet, matched by creation: handle_optima_zatca kept a row's creation but
    gave it a new name."""
    return [_optima_log(row) for row in rows if row.creation not in copied_creations]


def _optima_log(row) -> dict:
    """The legacy row as an Optima Zatca Log, keeping its name, owner and creation.

    The commercial register and environment stay empty. get_invoice_counter_and_pih continues a
    register's ICV/PIH chain from its highest logged ICV in an environment, so a legacy row given
    both could put an old invoice at the head of a live chain.
    """
    return {
        "doctype": "Optima Zatca Logs",
        "name": row.name,
        **{field: row.get(field) for field in COPIED_FIELDS},
        "api_endpoint": _api_endpoint(row.get("method"), row.get("message")),
    }


def _api_endpoint(method, message):
    """The endpoint the call went to, which the legacy log never stored and the reports count by.

    Only ZATCA's answer names it, so a call that failed before ZATCA answered gets none.
    """
    if (method or "").startswith(SAMPLE_INVOICE_METHOD):
        return "complainace_checks"

    response = _json_object(message)
    if "clearanceStatus" in response:
        return "clearance"
    if "reportingStatus" in response:
        return "reporting"
    return None


def _json_object(text) -> dict:
    try:
        value = json.loads(text or "")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


# ====================================================================================================
# READS

def _legacy_batches():
    table = frappe.qb.DocType(LEGACY_DOCTYPE)
    last_name = ""
    while rows := (
        frappe.qb.from_(table)
        .select(table.star)
        .where(table.name > last_name)
        .orderby(table.name)
        .limit(BATCH_SIZE)
        .run(as_dict=True)
    ):
        yield rows
        last_name = rows[-1].name


def _creations_already_copied(rows) -> set:
    return set(
        frappe.get_all(
            "Optima Zatca Logs", filters={"creation": ["in", [row.creation for row in rows]]}, pluck="creation"
        )
    )
