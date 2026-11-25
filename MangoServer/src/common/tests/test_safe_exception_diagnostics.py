from django.test import SimpleTestCase
from django.db import DataError, OperationalError

from src.common.logging.diagnostics import safe_exception_diagnostics


class SafeExceptionDiagnosticsTests(SimpleTestCase):
    def test_driver_message_and_locals_are_not_included(self):
        private = 'example-password SELECT private_value FROM example_table'
        try:
            raise DataError(1264, private)
        except DataError as error:
            code, frames = safe_exception_diagnostics(error)
        self.assertEqual(code, 1264)
        self.assertIn('test_driver_message_and_locals_are_not_included', frames)
        self.assertIn('DataError', frames)
        self.assertNotIn(private, frames)
        self.assertNotIn('SELECT', frames)

    def test_chained_driver_code_is_preserved_without_exception_text(self):
        try:
            try:
                raise OperationalError(1205, 'example-secret')
            except OperationalError as cause:
                raise RuntimeError('private wrapper') from cause
        except RuntimeError as error:
            code, frames = safe_exception_diagnostics(error)
        self.assertEqual(code, 1205)
        self.assertIn('OperationalError', frames)
        self.assertIn('RuntimeError', frames)
        self.assertNotIn('example-secret', frames)
        self.assertNotIn('private wrapper', frames)

    def test_non_numeric_codes_and_exception_cycles_are_safe(self):
        error = ValueError('secret-is-not-an-error-code')
        error.__cause__ = error
        code, frames = safe_exception_diagnostics(error)
        self.assertIsNone(code)
        self.assertEqual(frames, 'ValueError')
