from django.contrib.auth.hashers import check_password
from django.test import SimpleTestCase
from mangotools.data_processor import EncryptionTool

from src.apps.user.services.authentication.password import double_md5, encode_plain_password, verify_password_digest


class PasswordCompatibilityTests(SimpleTestCase):
    def test_single_md5_import_preserves_original_password(self):
        stored = EncryptionTool.md5_32_small('LegacyPasswordForTest1!')
        digest = double_md5('LegacyPasswordForTest1!')
        valid, upgraded = verify_password_digest(digest, stored)
        self.assertTrue(valid)
        self.assertTrue(check_password(digest, upgraded))
        self.assertEqual(verify_password_digest(digest, upgraded), (True, None))

    def test_double_md5_import_preserves_original_password(self):
        digest = double_md5('LegacyPasswordForTest2!')
        valid, upgraded = verify_password_digest(digest, digest)
        self.assertTrue(valid)
        self.assertTrue(check_password(digest, upgraded))

    def test_wrong_password_does_not_upgrade_either_legacy_format(self):
        for stored in (
            EncryptionTool.md5_32_small('LegacyPasswordForTest3!'),
            double_md5('LegacyPasswordForTest3!'),
        ):
            self.assertEqual(
                verify_password_digest(double_md5('WrongPasswordForTest!'), stored),
                (False, None),
            )

    def test_current_hash_is_unchanged_and_cannot_be_replayed(self):
        stored = encode_plain_password('CurrentPasswordForTest1!')
        self.assertEqual(
            verify_password_digest(double_md5('CurrentPasswordForTest1!'), stored),
            (True, None),
        )
        self.assertEqual(verify_password_digest(stored, stored), (False, None))

    def test_missing_credentials_are_rejected(self):
        for supplied, stored in ((None, 'value'), ('value', None), ('', '')):
            self.assertEqual(verify_password_digest(supplied, stored), (False, None))

    def test_non_digest_row_is_not_accepted_by_single_md5_bridge(self):
        stored = 'not-a-legacy-digest'
        self.assertEqual(
            verify_password_digest(EncryptionTool.md5_32_small(stored), stored),
            (False, None),
        )
