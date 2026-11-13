import os
import tempfile
import unittest
from unittest.mock import patch

from optima_zatca.zatca import pdfa3
from optima_zatca.zatca.keys import key_file_path


class TestKeyFilePath(unittest.TestCase):
    def setUp(self):
        self.files_dir = tempfile.mkdtemp()

    def test_path_stays_in_private_files(self):
        # Catches a company name that walks out of private/files ("../../x").
        path = key_file_path(self.files_dir, "../../etc/passwd", "PrivateKey.pem")
        self.assertEqual(os.path.dirname(path), os.path.realpath(self.files_dir))
        self.assertTrue(os.path.basename(path).endswith("_PrivateKey.pem"))

    def test_arabic_names_do_not_collide(self):
        # Catches two Arabic company names reducing to the same (empty) file name.
        a = key_file_path(self.files_dir, "شركة أوبتيما للأعلاف", "csr.pem")
        b = key_file_path(self.files_dir, "شركة الأخوين", "csr.pem")
        self.assertNotEqual(a, b)

    def test_same_company_gets_the_same_path(self):
        # GenerateCSR writes a file and reads it back by calling get_file_path again.
        self.assertEqual(
            key_file_path(self.files_dir, "Dev Company", "csr.pem"),
            key_file_path(self.files_dir, "Dev Company", "csr.pem"),
        )

    def test_suffix_cannot_traverse(self):
        with self.assertRaises(ValueError):
            key_file_path(self.files_dir, "Dev", "../config.cnf")


class TestSiteFilePath(unittest.TestCase):
    def setUp(self):
        self.public = tempfile.mkdtemp()
        self.private = tempfile.mkdtemp()

        def files_path(*parts, is_private=False):
            return os.path.join(self.private if is_private else self.public, *parts)

        patcher = patch.object(pdfa3, "get_files_path", side_effect=files_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_url_is_reduced_to_a_file_in_the_files_folder(self):
        self.assertEqual(pdfa3._site_file_path("/files/logo.png"), os.path.join(os.path.realpath(self.public), "logo.png"))
        self.assertEqual(
            pdfa3._site_file_path("/private/files/qr.png", is_private=True),
            os.path.join(os.path.realpath(self.private), "qr.png"),
        )

    def test_traversal_is_refused(self):
        # Catches a letter head URL such as /files/../../site_config.json reading outside the files folder.
        for value in ("..", "/files/..", "", None):
            self.assertIsNone(pdfa3._site_file_path(value), value)
        self.assertEqual(
            pdfa3._site_file_path("/files/../../site_config.json"),
            os.path.join(os.path.realpath(self.public), "site_config.json"),
        )


if __name__ == "__main__":
    unittest.main()
