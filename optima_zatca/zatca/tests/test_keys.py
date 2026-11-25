"""GenerateCSR leaves no file behind: the private key must persist only on the Optima Zatca Setting.

Runs the real openssl into a temporary folder this test owns, so a scratch file that outlives the
run shows up as a leftover there.
"""

import base64
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import frappe
from cryptography import x509
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from optima_zatca.zatca import keys

IDENTITY = {
    "organization_name": "Optima Zatca Test Company",
    "organization_unit_name": "Riyadh Branch",
    "organization_identifier": "300000000000003",
    "invoice_type": "1100",
    "industry": "Retail",
    "address": "Riyadh",
}


class TestGenerateCSRScratchFiles(unittest.TestCase):
    def setUp(self):
        self.temp_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_root, ignore_errors=True)
        for patcher in (
            patch.object(tempfile, "tempdir", self.temp_root),
            patch.object(keys, "get_company_info", return_value={}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def generate(self):
        settings = frappe._dict(company="Optima Zatca Test Company", api_endpoints="sandbox")
        return keys.GenerateCSR(settings, **IDENTITY).get_generated_details()

    def test_details_survive_the_folder(self):
        # Catches the read-back running after the folder is gone, or the folder outliving the run.
        details = self.generate()

        load_pem_private_key(details["private_key"].encode(), password=None)
        x509.load_pem_x509_csr(base64.b64decode(details["csr"]))
        self.assertEqual(os.listdir(self.temp_root), [])

    def test_folder_is_removed_when_a_later_step_fails(self):
        # Catches cleanup on the success path only: the key is already on disk when the CSR fails.
        with patch.object(keys.GenerateCSR, "create_csr", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.generate()

        self.assertEqual(os.listdir(self.temp_root), [])


if __name__ == "__main__":
    unittest.main()
