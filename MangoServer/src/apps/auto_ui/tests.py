# Create your tests here.
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_ui.service.test_case import test_case as ui_test_case_module
from src.apps.auto_ui.service.test_case.test_case import TestCase
from src.common.exceptions import UiError


class FakeQuerySet(list):

    def order_by(self, *args):
        return self


class UiTestCaseParametrizeTests(SimpleTestCase):

    def make_case(self, parametrize):
        return SimpleNamespace(
            id=1,
            name='允许空参数用例',
            status=None,
            save=lambda: None,
            front_custom=[],
            front_sql=[],
            posterior_sql=[],
            parametrize=parametrize,
            module=SimpleNamespace(name='合同管理'),
            project_product=SimpleNamespace(id=1, name='智书合同'),
            case_people=SimpleNamespace(name='liqian'),
        )

    def run_case(self, case):
        step = SimpleNamespace(page_step=SimpleNamespace(id=1), switch_step_open_url=False)
        service = TestCase(user_id=1, username='liqian', test_env=1)

        with patch.object(ui_test_case_module.UiCase.objects, 'get', return_value=case), \
                patch.object(ui_test_case_module.UiCaseStepsDetailed.objects, 'filter',
                             return_value=FakeQuerySet([step])), \
                patch.object(service, 'steps_model', return_value=object()), \
                patch.object(ui_test_case_module, 'CaseModel', return_value=SimpleNamespace()), \
                patch.object(service, '_TestCase__socket_send'):
            return service.test_case(case_id=case.id)

    def test_case_parametrize_allows_empty_values(self):
        case = self.make_case([
            {
                'name': '参数组1',
                'parametrize': [
                    {'key': 'empty_text', 'value': ''},
                    {'key': 'null_value', 'value': None},
                    {'key': 'missing_value'},
                    {'key': 'zero_value', 'value': 0},
                    {'key': 'false_value', 'value': False},
                    {'key': 'empty_list', 'value': []},
                ],
            }
        ])

        self.assertIsNotNone(self.run_case(case))

    def test_case_parametrize_still_rejects_empty_key(self):
        case = self.make_case([{'name': '参数组1', 'parametrize': [{'key': '', 'value': 'ok'}]}])

        with self.assertRaises(UiError):
            self.run_case(case)
