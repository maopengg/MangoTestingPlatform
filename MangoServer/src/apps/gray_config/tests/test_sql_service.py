from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.gray_config.services.sql_service import GraySqlService


class GraySqlServiceTests(SimpleTestCase):

    @patch('src.apps.gray_config.services.sql_service.DataSourceExecutionService.execute')
    @patch('src.apps.gray_config.services.sql_service.DataFactoryDatasourceResolver.resolve_binding_by_env')
    def test_logical_datasource_executes_through_unified_service(self, resolve_binding, execute):
        resolve_binding.return_value = SimpleNamespace(
            datasource_alias_id=9,
            database_id=18,
        )
        execute.return_value = {'affected_rows': 2}
        feature = SimpleNamespace(
            datasource_alias_id=9,
            database_id=None,
            project_product_id=22,
            runtime_environment=1,
        )

        affected_rows = GraySqlService.execute_sql(
            feature,
            'UPDATE gray_switch SET enabled=:target_value WHERE feature_key=:feature_key',
            {'target_value': '1', 'feature_key': 'new_checkout'},
        )

        self.assertEqual(affected_rows, 2)
        self.assertEqual(feature.runtime_database_id, 18)
        execute.assert_called_once_with(
            datasource_alias_id=9,
            project_product_id=22,
            test_env=1,
            operation_config=(
                'UPDATE gray_switch SET enabled=:target_value WHERE feature_key=:feature_key'
            ),
            parameters={'target_value': '1', 'feature_key': 'new_checkout'},
            source_context={
                'source_type': 'gray_config',
                'source_stage': 'execute',
                'source_id': None,
                'gray_feature_id': None,
            },
        )
