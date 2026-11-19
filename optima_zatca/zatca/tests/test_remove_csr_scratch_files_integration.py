"""The cleanup patch against the real Optima Zatca Setting and File tables.

The files live in a temporary folder standing in for the site's private files, so the site's own
files are never touched. The matrix suite covers why each set is kept; this one proves the stored
keys and File records are read from the right fields, the right files go, and the Error Log names
what is left without copying a key into it.
"""

import os
import shutil
import tempfile
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from optima_zatca.patches.v16 import remove_csr_scratch_files as cleanup

STORED_KEY = "-----BEGIN EC PRIVATE KEY-----\nOZTSTORED\n-----END EC PRIVATE KEY-----\n"
ORPHAN_KEY = "-----BEGIN EC PRIVATE KEY-----\nOZTORPHAN\n-----END EC PRIVATE KEY-----\n"
SUFFIXES = ("_PrivateKey.pem", "_PublicKey.pem", "_csr.pem", "_config.cnf")


class TestRemoveCSRScratchFiles(IntegrationTestCase):
    def setUp(self):
        self.files_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.files_dir, ignore_errors=True)

        self.write_set("ozt-stored", STORED_KEY)
        self.write_set("ozt-orphan", ORPHAN_KEY)
        self.write_set("ozt-uploaded", STORED_KEY)

        frappe.get_doc(
            {"doctype": "Optima Zatca Setting", "name": "OZT Key Cleanup Test", "private_key": STORED_KEY.strip()}
        ).db_insert()
        frappe.get_doc(
            {
                "doctype": "File",
                "name": "ozt-key-cleanup-upload",
                "file_name": "ozt-uploaded_csr.pem",
                "file_url": "/private/files/ozt-uploaded_csr.pem",
                "is_private": 1,
            }
        ).db_insert()

    def tearDown(self):
        frappe.db.rollback()

    def write_set(self, prefix, key):
        for suffix in SUFFIXES:
            with open(os.path.join(self.files_dir, prefix + suffix), "w") as f:
                f.write(key if suffix == "_PrivateKey.pem" else "not secret\n")

    def test_only_the_stored_set_goes_and_the_log_names_the_rest(self):
        started = frappe.utils.now()
        with patch.object(cleanup.frappe, "get_site_path", return_value=self.files_dir):
            cleanup.execute()

        left = sorted(os.listdir(self.files_dir))
        self.assertEqual(left, sorted(prefix + s for prefix in ("ozt-orphan", "ozt-uploaded") for s in SUFFIXES))

        log = frappe.get_all(
            "Error Log", filters={"method": cleanup.LOG_TITLE, "creation": [">=", started]}, pluck="error"
        )
        self.assertEqual(len(log), 1)
        self.assertIn("ozt-orphan_PrivateKey.pem", log[0])
        self.assertNotIn("OZTORPHAN", log[0])
