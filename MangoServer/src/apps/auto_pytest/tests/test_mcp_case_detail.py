from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_pytest.exceptions import AutoPytestError
from src.interfaces.mcp.tools.pytest import helpers


class PytestMcpCaseDetailTests(SimpleTestCase):
    def read_detail(self, source_status=0, file_exists=True):
        case = SimpleNamespace(
            source_status=source_status, file_path='auto_tests/example/test_example.py',
            project_product=SimpleNamespace(name='Example project'),
            module=SimpleNamespace(name='Example module'), case_people=SimpleNamespace(name='Tester'),
        )
        query = Mock()
        query.select_related.return_value.get.return_value = case
        with patch.object(helpers.PytestQuerySelector, 'pytest_case', return_value=query), \
                patch.object(helpers.RepositoryGitService, 'for_product') as service, \
                patch.object(helpers, '_case_summary', return_value={'id': 1}):
            service.return_value.repository_file_exists.return_value = file_exists
            return helpers._case_detail(1)

    def test_available_source_can_be_read_without_removed_binding_enum(self):
        self.assertEqual(self.read_detail()['project_product_name'], 'Example project')

    def test_missing_source_is_rejected(self):
        for args in [{'source_status': 2}, {'file_exists': False}]:
            with self.subTest(**args), self.assertRaises(AutoPytestError):
                self.read_detail(**args)
