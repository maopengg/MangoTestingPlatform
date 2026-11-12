from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_ui.api.serializers.ui_case import UiCaseSerializersC
from src.apps.auto_ui.models import UiCase
from src.apps.user.models import User


class UiCaseListOwnerTests(SimpleTestCase):
    def test_owner_representation_does_not_read_personal_environment_or_save(self):
        owner = User(id=7, name='测试负责人', username='owner@example.com',
                     config={})
        case = UiCase(id=1, name='测试用例', case_people=owner,
                      project_product=None, module=None, update_user=None)
        with (
            patch('src.apps.user.services.preferences.user_config.UserConfigService.selected_environment',
                  side_effect=AssertionError('列表不应读取个人环境')) as environment,
            patch.object(User, 'save') as save,
        ):
            result = UiCaseSerializersC([case], many=True).data

        self.assertEqual(result[0]['case_people'], {
            'id': 7, 'name': '测试负责人', 'username': 'owner@example.com',
        })
        environment.assert_not_called()
        save.assert_not_called()
        self.assertEqual(owner.config, {})

    def test_missing_owner_remains_null(self):
        case = UiCase(id=1, name='无负责人用例', case_people=None,
                      project_product=None, module=None, update_user=None)
        self.assertIsNone(UiCaseSerializersC(case).data['case_people'])
