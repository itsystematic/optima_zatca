import os
import tempfile
import unittest
from unittest.mock import patch

from optima_zatca.zatca import pdfa3


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
