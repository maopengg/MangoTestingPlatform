import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import StatusEnum

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.datasource.elasticsearch import ElasticsearchDatasourceService as ES
from src.apps.data_factory.services.schema.schema_monitor import DataFactorySchemaMonitorService as Monitor
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit


class CleanupIndexResolutionTests(SimpleTestCase):
    def resolve(self, payload, name='example_alias'):
        target = SimpleNamespace(extra_config={}, host='es.example.com', port=9200, user='', password='')
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps(payload).encode()
        with patch.object(Audit, 'call', side_effect=lambda target, operation, callback, **kwargs: callback()) as audit, \
                patch('src.apps.data_factory.services.datasource.elasticsearch.open_elasticsearch_request', return_value=response) as http:
            result = ES.resolve_index(target, name)
        self.assertEqual(audit.call_args.args[1]['operation'], 'resolve_cleanup_index')
        self.assertIn('/example_alias?filter_path=', http.call_args.args[0].full_url)
        return result

    def test_alias_resolves_exact_physical_index_and_uuid(self):
        self.assertEqual(self.resolve({'example_physical': {
            'aliases': {'example_alias': {}}, 'settings': {'index': {'uuid': 'AUTO_UUID'}}}}),
            ('example_physical', 'AUTO_UUID'))

    def test_multi_target_filtered_routed_missing_uuid_and_wrong_alias_fail_closed(self):
        good = {'aliases': {'example_alias': {}}, 'settings': {'index': {'uuid': 'AUTO_UUID'}}}
        for payload in (
            {}, {'example_a': good, 'example_b': good},
            {'example_a': {'aliases': {'example_alias': {'filter': {'term': {'tenant': 7}}}},
                           'settings': good['settings']}},
            {'example_a': {'aliases': {'example_alias': {'routing': '7'}}, 'settings': good['settings']}},
            {'example_a': {'aliases': good['aliases'], 'settings': {}}},
            {'example_a': {'aliases': {}, 'settings': good['settings']}},
        ):
            with self.subTest(payload=payload), self.assertRaises(DataFactoryError):
                self.resolve(payload)


class ActivationDiagnosticTests(SimpleTestCase):
    def test_selected_test_schema_ignores_dev_but_reports_real_test_nullable_difference(self):
        entity = SimpleNamespace(id=228, name='AUTO缓存记录', table_name='example_record', schema_name='',
            primary_key='id', unique_key='', datasource_alias_id=1, datasource_alias=SimpleNamespace(status=StatusEnum.SUCCESS.value))
        bindings = [SimpleNamespace(id=10, database_id=11, environment=0, database=Mock()),
                    SimpleNamespace(id=12, database_id=13, environment=3, database=Mock())]
        column = {'name': 'id', 'db_type': 'BIGINT', 'nullable': False, 'primary_key': True,
                  'autoincrement': True, 'max_length': None}
        expected = Monitor.columns_signature([column])
        with patch('src.apps.data_factory.services.schema.schema_monitor.DataFactoryEntity.objects') as entities, \
                patch('src.apps.data_factory.services.schema.schema_monitor.DataFactoryDatasourceBinding.objects') as sources, \
                patch.object(Monitor, 'configured_validation_environments', return_value=[0]), \
                patch.object(Monitor, 'entity_signature', return_value=expected), \
                patch('src.apps.data_factory.services.schema.schema_monitor.DataFactoryDatasourceResolver.require_binding_permission'), \
                patch('src.apps.data_factory.services.schema.schema_monitor.DatasourceTargetService.resolve'), \
                patch('src.apps.data_factory.services.schema.schema_monitor.DataFactoryDiscover.get_table_schema') as discover:
            entities.select_related.return_value.get.return_value = entity
            sources.select_related.return_value.filter.return_value.order_by.return_value = bindings
            discover.return_value = {'columns': [column]}
            self.assertEqual(Monitor.validate_entity_activation(228)['checked_binding_ids'], [10])
            self.assertEqual(discover.call_count, 1)
            discover.return_value = {'columns': [{**column, 'nullable': True}]}
            with self.assertRaises(DataFactoryError) as raised:
                Monitor.validate_entity_activation(228)
        error = raised.exception
        self.assertEqual(error.code, 34197)
        self.assertIn('环境 0', error.msg)
        self.assertIn('nullable：模型=False，数据库=True', error.msg)
        self.assertEqual(error.details['failures'][0]['binding_id'], 10)
        self.assertEqual(error.details['entity_id'], 228)
