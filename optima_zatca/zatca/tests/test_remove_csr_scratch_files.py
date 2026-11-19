"""Which leftover CSR scratch files the cleanup patch deletes, and which it keeps for an administrator.

Deleting a private key that is stored nowhere else would lose it for good, so a set goes only when
its key is stored on a setting, and every other case keeps it.
"""

import unittest

from optima_zatca.patches.v16 import remove_csr_scratch_files as cleanup

KEY = "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEE\n-----END EC PRIVATE KEY-----\n"
STORED = {KEY.strip(): "OZT-1010000001-production"}
FULL_SET = ["masar_PrivateKey.pem", "masar_PublicKey.pem", "masar_csr.pem", "masar_config.cnf"]


class TestGroupScratchFiles(unittest.TestCase):
    def test_sets_are_split_on_the_suffix(self):
        # Catches splitting on the first "_" (old names may start with one, or hold several) and a
        # suffix matched anywhere in the name rather than at its end.
        names = [
            "_testcompany_PrivateKey.pem",
            "_testcompany_csr.pem",
            "masar(demo)_config.cnf",
            "dev_co-1a2b3c4d_PublicKey.pem",
            "masar_csr.pem.bak",
            "invoice.pdf",
        ]

        self.assertEqual(
            cleanup._group_scratch_files(names),
            {
                "_testcompany": ["_testcompany_PrivateKey.pem", "_testcompany_csr.pem"],
                "masar(demo)": ["masar(demo)_config.cnf"],
                "dev_co-1a2b3c4d": ["dev_co-1a2b3c4d_PublicKey.pem"],
            },
        )


class TestDecideSet(unittest.TestCase):
    def test_stored_key_deletes_the_set_and_names_its_setting(self):
        # Catches comparing the file's text unstripped: the setting holds the same key without the
        # trailing newline openssl writes.
        delete, reason = cleanup._decide_set(FULL_SET, KEY, STORED, uploaded=set())

        self.assertTrue(delete)
        self.assertIn("OZT-1010000001-production", reason)

    def test_key_stored_nowhere_is_kept(self):
        # Catches deleting every set that has a key: this may be the only copy.
        other_key = KEY.replace("MHQCAQEE", "OTHERKEY")

        self.assertFalse(cleanup._decide_set(FULL_SET, other_key, STORED, uploaded=set())[0])

    def test_set_without_a_key_is_kept(self):
        # Catches deleting companions on their own, which the administrator asked to decide on.
        self.assertFalse(cleanup._decide_set(["masar_csr.pem"], None, STORED, uploaded=set())[0])

    def test_unreadable_key_is_kept(self):
        # Catches an unreadable key crashing the patch or counting as a match.
        self.assertFalse(cleanup._decide_set(FULL_SET, None, STORED, uploaded=set())[0])

    def test_uploaded_companion_keeps_the_set_even_with_a_stored_key(self):
        # Catches checking only the key file for a File record, or checking it after the key match.
        self.assertFalse(cleanup._decide_set(FULL_SET, KEY, STORED, uploaded={"masar_csr.pem"})[0])


if __name__ == "__main__":
    unittest.main()
