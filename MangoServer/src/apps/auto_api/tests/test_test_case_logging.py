from django.test import SimpleTestCase

from src.apps.auto_api.services.test_case.test_case_parts import debugging, execution, parameter
from src.common.logging import log


class ApiTestCaseLoggingImportsTests(SimpleTestCase):

    def test_test_case_mixins_use_shared_logger(self):
        for module in (execution, parameter, debugging):
            with self.subTest(module=module.__name__):
                self.assertIs(module.log, log)
