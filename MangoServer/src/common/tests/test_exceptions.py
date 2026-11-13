from django.core.exceptions import ObjectDoesNotExist
from django.db.models.deletion import ProtectedError, RestrictedError
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from src.apps.auto_api.exceptions import AutoApiError
from src.common.exceptions import ErrorDefinition, RESOURCE_DELETE_PROTECTED, normalize_expected_exception


class UnifiedExceptionTests(SimpleTestCase):
    def test_foreign_key_protection_is_expected_and_does_not_expose_internal_objects(self):
        for error in (ProtectedError('private database and object details', []),
                      RestrictedError('private database and object details', [])):
            normalized = normalize_expected_exception(error)
            self.assertEqual(normalized.code, RESOURCE_DELETE_PROTECTED.code)
            self.assertEqual(normalized.log_status_code, 409)
            self.assertEqual(normalized.details, {})
            self.assertNotIn('private', normalized.message)

    def test_definition_formats_message_and_defaults_machine_code(self):
        definition = ErrorDefinition(code=1234, message="对象 {} 不存在")

        error = AutoApiError(definition, value=(99,), details={"object_id": 99})

        self.assertEqual(error.code, 1234)
        self.assertEqual(error.msg, "对象 99 不存在")
        self.assertEqual(error.error_code, "1234")
        self.assertEqual(error.details, {"object_id": 99})

    def test_semantic_machine_code_is_optional(self):
        definition = ErrorDefinition(code=300, message="执行器离线")

        error = AutoApiError(definition, error_code="EXECUTOR_OFFLINE")

        self.assertEqual(error.error_code, "EXECUTOR_OFFLINE")

    def test_missing_django_object_is_an_expected_protocol_error(self):
        normalized = normalize_expected_exception(ObjectDoesNotExist("internal model name"))

        self.assertIsNotNone(normalized)
        self.assertEqual(normalized.error_code, "300")
        self.assertNotIn("internal model name", normalized.message)
        self.assertEqual(normalized.log_status_code, 404)

    def test_drf_validation_error_is_expected_and_sanitized(self):
        normalized = normalize_expected_exception(ValidationError([{
            'loc': ['json_path'],
            'msg': 'Extra inputs are not permitted',
            'input': 'sensitive-input',
            'url': 'https://errors.example.com/internal',
        }]))

        self.assertIsNotNone(normalized)
        self.assertEqual(normalized.error_code, 'VALIDATION_ERROR')
        self.assertEqual(normalized.log_status_code, 400)
        self.assertNotIn('sensitive-input', str(normalized.details))
        self.assertNotIn('errors.example.com', str(normalized.details))
