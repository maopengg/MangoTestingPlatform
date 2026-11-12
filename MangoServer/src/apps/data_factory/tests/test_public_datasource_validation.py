from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_api.api.serializers.api_pulic import ApiPublicSerializers
from src.apps.auto_ui.api.serializers.ui_public import UiPublicSerializers
from src.apps.auto_ui.enums import UiPublicTypeEnum
from src.apps.auto_ui.services.execution.cases.test_case import TestCase as UiTestCaseService
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver


class PublicDatasourceValidationTests(SimpleTestCase):

    @staticmethod
    def serializer_instance():
        return SimpleNamespace(
            type=1,
            datasource_alias=None,
            project_product=None,
            test_envs=[],
            test_env=None,
        )

    @staticmethod
    def sql_attrs():
        return {
            'type': 1,
            'datasource_alias': SimpleNamespace(id=9, project_product_id=22),
            'project_product': SimpleNamespace(id=22),
            'test_envs': [],
        }

    @patch.object(DataFactoryDatasourceResolver, 'require_sql_public_alias')
    def test_api_public_save_validates_sql_datasource(self, require_sql_public_alias):
        serializer = ApiPublicSerializers(instance=self.serializer_instance())
        attrs = self.sql_attrs()

        serializer.validate(attrs)

        require_sql_public_alias.assert_called_once_with(attrs['datasource_alias'], 22)

    @patch.object(DataFactoryDatasourceResolver, 'require_sql_public_alias')
    def test_ui_public_save_validates_sql_datasource(self, require_sql_public_alias):
        serializer = UiPublicSerializers(instance=self.serializer_instance())
        attrs = self.sql_attrs()

        serializer.validate(attrs)

        require_sql_public_alias.assert_called_once_with(attrs['datasource_alias'], 22)

    @patch('src.apps.auto_ui.services.execution.cases.test_case.UiCaseGlobalVariableService.list_public')
    def test_ui_runtime_rejects_legacy_redis_sql_public_variable(self, list_public):
        list_public.return_value = [SimpleNamespace(
            id=7,
            type=UiPublicTypeEnum.SQL.value,
            key='token',
            value='GET token',
            datasource_alias_id=9,
            datasource_alias=SimpleNamespace(
                project_product_id=22,
                status=1,
                db_type=10,
            ),
        )]

        with self.assertRaisesMessage(DataFactoryError, '仅支持MySQL、PostgreSQL和SQLite'):
            UiTestCaseService._TestCase__public_data(22, 1)
