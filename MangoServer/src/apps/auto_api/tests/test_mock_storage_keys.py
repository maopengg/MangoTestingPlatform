import copy

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from src.apps.auto_api.api.serializers.api_mock import ApiMockConfigSerializer
from src.apps.auto_api.exceptions import AutoApiError, MockRequestDecryptionError
from src.apps.auto_api.models import ApiMockConfig
from src.apps.auto_api.services.mock.mock_request_decryption import MockRequestDecryptionService as Service


class MockStorageKeyTests(SimpleTestCase):
    def legacy_config(self, key):
        cipher = Service._cipher_for_key(key)
        return {"type": "lark_event", "storage_algorithm": "fernet-sha256-v1",
                "encrypt_key_ciphertext": cipher.encrypt(b"example-encrypt-key").decode("ascii"),
                "verification_token_ciphertext": cipher.encrypt(b"example-token").decode("ascii")}

    def test_new_values_are_plaintext_and_independent_of_system_secret(self):
        stored = Service.normalize_for_storage({"type": "lark_event", "encrypt_key": "example-key"})
        self.assertEqual(stored, {"type": "lark_event", "encrypt_key": "example-key", "verification_token": ""})
        with override_settings(VERSION="example-new-version", SECRET_KEY="example-new-django-secret"):
            self.assertEqual(Service.editable_config(stored)["encrypt_key"], "example-key")
            self.assertEqual(Service.runtime_config({"request_decryption": stored})["request_decryption"], stored)

    @override_settings(VERSION="7.3.0", SECRET_KEY="example-legacy-prefix-7.3.0")
    def test_all_released_legacy_versions_remain_readable(self):
        for version in ("7.1.1", "7.2.0", "7.2.1", "7.2.2", "7.2.3"):
            with self.subTest(version=version):
                config = self.legacy_config(f"example-legacy-prefix-{version}")
                self.assertEqual(Service.editable_config(config)["encrypt_key"], "example-encrypt-key")
                self.assertEqual(Service.runtime_config({"request_decryption": config})[
                    "request_decryption"]["verification_token"], "example-token")

    def test_current_django_key_remains_readable(self):
        with override_settings(SECRET_KEY="example-custom-legacy-key"):
            self.assertEqual(Service.editable_config(self.legacy_config(settings.SECRET_KEY))[
                "encrypt_key"], "example-encrypt-key")

    def test_legacy_config_converts_to_plaintext_on_save_without_mutating_source(self):
        old = self.legacy_config(settings.SECRET_KEY)
        before = copy.deepcopy(old)
        saved = Service.normalize_for_storage({"type": "lark_event"}, {"request_decryption": old})
        self.assertEqual(old, before)
        self.assertEqual(saved["encrypt_key"], "example-encrypt-key")
        self.assertNotIn("encrypt_key_ciphertext", saved)
        self.assertNotIn("storage_algorithm", saved)
        self.assertEqual(Service.editable_config(saved)["verification_token"], "example-token")

    def test_plaintext_updates_preserve_omitted_token_and_allow_explicit_clear(self):
        old = {"type": "lark_event", "encrypt_key": "example-key", "verification_token": "example-token"}
        saved = Service.normalize_for_storage({"type": "lark_event"}, {"request_decryption": old})
        self.assertEqual(saved, old)
        cleared = Service.normalize_for_storage({"type": "lark_event", "verification_token": ""},
                                                {"request_decryption": old})
        self.assertEqual(cleared["verification_token"], "")

    def test_missing_key_cannot_run_or_save(self):
        with self.assertRaises(AutoApiError):
            Service.normalize_for_storage({"type": "lark_event", "encrypt_key": ""})
        with self.assertRaises(MockRequestDecryptionError):
            Service.runtime_config({"request_decryption": {"type": "lark_event", "encrypt_key": ""}})

    def test_broken_ciphertext_keeps_detail_accessible_but_runtime_fails_closed(self):
        broken = {"type": "lark_event", "encrypt_key_ciphertext": "invalid-ciphertext"}
        config = ApiMockConfig(id=1, project_product_id=1, name="Example", mock_key="example",
                               config={"request_decryption": broken})
        detail = ApiMockConfigSerializer(config).data
        editable = detail["config"]["request_decryption"]
        self.assertTrue(editable["configuration_error"])
        self.assertEqual(editable["encrypt_key"], "")
        self.assertNotIn("ciphertext", str(detail))
        self.assertEqual(config.config["request_decryption"], broken)
        with self.assertRaises(MockRequestDecryptionError):
            Service.runtime_config(config.config)
        with self.assertRaises(AutoApiError):
            Service.normalize_for_storage({"type": "lark_event"}, config.config)

    def test_tampered_token_is_not_silently_disabled(self):
        config = self.legacy_config(settings.SECRET_KEY)
        config["verification_token_ciphertext"] = "invalid-token"
        self.assertTrue(Service.editable_config(config)["configuration_error"])
        with self.assertRaises(MockRequestDecryptionError):
            Service.runtime_config({"request_decryption": config})
        with self.assertRaises(AutoApiError):
            Service.normalize_for_storage({"type": "lark_event", "encrypt_key": "example-new-key"},
                                          {"request_decryption": config})
        saved = Service.normalize_for_storage({"type": "lark_event", "encrypt_key": "example-new-key",
                                              "verification_token": ""}, {"request_decryption": config})
        self.assertNotIn("verification_token_ciphertext", saved)

    def test_unknown_key_can_be_replaced_without_reading_corrupted_secrets(self):
        old = self.legacy_config("example-unknown-key")
        saved = Service.normalize_for_storage({"type": "lark_event", "encrypt_key": "example-replacement",
                                              "verification_token": "example-new-token"},
                                             {"request_decryption": old})
        self.assertEqual(Service.editable_config(saved)["encrypt_key"], "example-replacement")
        self.assertEqual(Service.normalize_for_storage({"type": "none"}, {"request_decryption": old}),
                         {"type": "none"})
