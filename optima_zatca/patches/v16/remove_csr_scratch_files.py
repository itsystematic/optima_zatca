"""Remove the key and CSR scratch files that onboarding left in the site's private files.

GenerateCSR wrote <prefix>_PrivateKey.pem, _PublicKey.pem, _csr.pem and _config.cnf there and
never deleted them, so an onboarded site kept a plain copy of its ZATCA signing key outside the
database. A set is deleted only when its private key is the one stored on an Optima Zatca Setting.
Every other set is kept and listed in the Error Log, for an administrator to decide on.

Sets are found by their four suffixes, not rebuilt from company names: the prefix was the company
name lowercased without spaces before #109 and a slug plus a hash after it, and a company may have
been renamed or deleted since.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime

import click
import frappe

KEY_SUFFIX = "_PrivateKey.pem"
SCRATCH_SUFFIXES = (KEY_SUFFIX, "_PublicKey.pem", "_csr.pem", "_config.cnf")
LOG_TITLE = "Optima ZATCA: key file cleanup"


@dataclass
class ScratchSet:
    prefix: str
    names: list[str]
    delete: bool
    reason: str
    modified: str
    failed: list[str] = field(default_factory=list)


def execute():
    files_dir = os.path.realpath(frappe.get_site_path("private", "files"))
    if not os.path.isdir(files_dir):
        return

    sets = remove_scratch_files(files_dir)
    if sets:
        frappe.log_error(title=LOG_TITLE, message=_format_report(files_dir, sets))
        click.echo(_format_report(files_dir, sets, style=click.style))


def remove_scratch_files(files_dir: str) -> list[ScratchSet]:
    """Delete the sets whose private key is stored on a setting, and return every set found."""
    groups = _group_scratch_files(_file_names(files_dir))
    if not groups:
        return []

    stored_keys = _stored_private_keys()
    uploaded = _names_with_file_record([name for names in groups.values() for name in names])

    sets = []
    for prefix, names in sorted(groups.items()):
        delete, reason = _decide_set(names, _read_private_key(files_dir, prefix), stored_keys, uploaded)
        scratch_set = ScratchSet(prefix, sorted(names), delete, reason, _modified(files_dir, names))
        if delete:
            scratch_set.failed = _delete_files(files_dir, scratch_set.names)
        sets.append(scratch_set)

    return sets


# ====================================================================================================
# WHAT TO DELETE AND WHAT TO REPORT

def _group_scratch_files(names) -> dict[str, list[str]]:
    groups = {}
    for name in names:
        suffix = next((s for s in SCRATCH_SUFFIXES if name.endswith(s)), None)
        if suffix:
            groups.setdefault(name[: -len(suffix)], []).append(name)
    return groups


def _decide_set(names, key_text, stored_keys, uploaded) -> tuple[bool, str]:
    """(delete?, reason) for one prefix's files, which are always deleted or kept together.

    `key_text` is the private key file's contents, None when it could not be read; `stored_keys`
    maps each stored private key to its setting; `uploaded` holds the names a File record points at.
    """
    if uploaded.intersection(names):
        return False, "a File record points at one of them, so a person uploaded it"

    if not any(name.endswith(KEY_SUFFIX) for name in names):
        return False, "there is no private key with them"

    if key_text is None:
        return False, "the private key could not be read"

    setting = stored_keys.get(key_text.strip())
    if not setting:
        return False, "the private key matches no Optima Zatca Setting"

    return True, f'the private key is saved on Optima Zatca Setting "{setting}"'


def _format_report(files_dir, sets, style=lambda text, **_: text) -> str:
    """Names, dates and reasons only: copying a key's contents would move the secret into the log.

    `style` is click.style for the terminal; the Error Log copy stays plain text.
    """
    lines = [f"ZATCA onboarding left key and CSR files in {files_dir}."]

    for title, color, chosen in (
        ("Deleted:", "green", [s for s in sets if s.delete]),
        ("Kept, for an administrator to decide on:", "yellow", [s for s in sets if not s.delete]),
    ):
        if chosen:
            lines += ["", style(title, fg=color, bold=True)]
            for s in chosen:
                lines.append(f"  {style(s.prefix + '_*', bold=True)} ({s.modified}): {s.reason}")
                lines.append(f"      {', '.join(s.names)}")

    failures = [failure for s in sets for failure in s.failed]
    if failures:
        lines += ["", style("Could not delete:", fg="red", bold=True)] + [f"  {failure}" for failure in failures]

    return "\n".join(lines)


# ====================================================================================================
# SITE FILES AND STORED KEYS

def _file_names(files_dir):
    return [entry.name for entry in os.scandir(files_dir) if entry.is_file()]


def _read_private_key(files_dir, prefix):
    try:
        # a name taken from the folder's own listing, joined back onto that folder
        with open(os.path.join(files_dir, prefix + KEY_SUFFIX), encoding="utf-8") as f:  # nosemgrep
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def _modified(files_dir, names):
    newest = max(os.path.getmtime(os.path.join(files_dir, name)) for name in names)
    return datetime.fromtimestamp(newest).strftime("%Y-%m-%d")


def _delete_files(files_dir, names) -> list[str]:
    failed = []
    for name in names:
        try:
            os.remove(os.path.join(files_dir, name))
        except OSError as e:
            failed.append(f"{name}: {e.strerror or e}")
    return failed


def _stored_private_keys():
    rows = frappe.get_all(
        "Optima Zatca Setting", filters={"private_key": ["is", "set"]}, fields=["name", "private_key"]
    )
    return {row.private_key.strip(): row.name for row in rows}


def _names_with_file_record(names):
    urls = frappe.get_all(
        "File", filters={"file_url": ["in", [f"/private/files/{name}" for name in names]]}, pluck="file_url"
    )
    return {url.rsplit("/", 1)[-1] for url in urls}
