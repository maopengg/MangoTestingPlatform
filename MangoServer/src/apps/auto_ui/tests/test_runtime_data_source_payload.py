from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_ui.enums import UiPublicTypeEnum
from src.apps.auto_ui.services.execution.cases.test_case import TestCase as UiTestCaseService


class UiRuntimeDataSourcePayloadTests(SimpleTestCase):
    @patch(
        'src.apps.auto_ui.services.execution.cases.test_case.func_test_object_value',
        return_value=SimpleNamespace(id=9, value='https://example.test'),
    )
    def test_environment_payload_does_not_include_database_connection(self, _test_object):
        service = UiTestCaseService(user_id=1, username='tester', test_env=0)

        config = service._TestCase__environment_config(3)

        payload = config.model_dump()
        self.assertEqual(payload, {
            'id': 9,
            'test_object_value': 'https://example.test',
            'target_config': None,
        })
        self.assertNotIn('db_c_status', payload)
        self.assertNotIn('db_rud_status', payload)
        self.assertNotIn('mysql_config', payload)
        self.assertNotIn('database_connections', payload)

    @patch(
        'src.apps.auto_ui.services.execution.cases.test_case.UiCaseGlobalVariableService.list_public',
    )
    def test_global_variable_payload_keeps_source_id(self, list_public):
        list_public.return_value = [SimpleNamespace(
            id=71,
            type=UiPublicTypeEnum.CUSTOM.value,
            key='username',
            value='AUTO-user',
            datasource_alias=None,
            datasource_alias_id=None,
        )]

        result = UiTestCaseService._TestCase__public_data(3, 0)

        self.assertEqual(result[0].id, 71)
