from copy import deepcopy
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.governance.datasource_cost import DatasourceCostService as Cost
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
from src.apps.data_factory.services.protocols.redis_protocol import BoundedRedisBuffer


class CostCompatibilityTests(SimpleTestCase):
    def test_legal_collection_and_scan_commands_are_not_rewritten_or_rejected(self):
        commands = [
            ['HGETALL', 'AUTO_hash'], ['HKEYS', 'AUTO_hash'], ['HVALS', 'AUTO_hash'],
            ['SMEMBERS', 'AUTO_set'], ['LRANGE', 'AUTO_list', '0', '-1'],
            ['ZRANGE', 'AUTO_rank', '-10', '-1'], ['SCAN', '0'],
            ['HSCAN', 'AUTO_hash', '0', 'MATCH', 'COUNT', 'COUNT', '500'],
            ['MGET', *[f'AUTO_{index}' for index in range(250)]],
        ]
        for command in commands:
            original = deepcopy(command)
            Cost.redis(command)
            self.assertEqual(command, original)

    def test_legal_es_dsl_and_business_field_names_are_not_cost_predictions(self):
        query = {'size': 0, 'query': {'bool': {'should': [
            {'term': {'script': 'AUTO'}}, {'wildcard': {'name': 'AUTO_*'}},
            {'terms': {'id': list(range(250))}},
        ]}}, 'aggs': {'by_time': {'date_histogram': {'field': 'created_at', 'calendar_interval': 'day'}}}}
        original = deepcopy(query)
        Cost.elasticsearch('example-*', query)
        self.assertEqual(query, original)
        Cost.sql("SELECT payload @> '{\"name\": \"AUTO\"}' FROM example")

    def test_shared_session_operations_still_block_without_business_failure_or_replay(self):
        for callback in (lambda: Cost.sql('SET @tenant=1'), lambda: Cost.redis(['SUBSCRIBE', 'AUTO_topic'])):
            with Infrastructure.scope():
                with self.assertRaises(DataFactoryError) as error:
                    callback()
                self.assertEqual(error.exception.code, 34187)
                self.assertEqual(Infrastructure.current()[0].code, 34187)

    def test_resp_headers_do_not_count_as_result_elements_but_real_overflow_never_returns_partial(self):
        source = Mock()
        source.readline.side_effect = [b'*2', b'$1', b'$1', b'$1']
        source.read.return_value = b'x'
        with patch('src.apps.data_factory.services.protocols.redis_protocol.SystemConfigService.get_ranged_int', return_value=2):
            buffer = BoundedRedisBuffer(source)
        self.assertEqual(buffer.readline(), b'*2')
        for _ in range(2):
            self.assertEqual(buffer.readline(), b'$1')
            self.assertEqual(buffer.read(1), b'x')
        self.assertEqual(buffer.items, 2)
        with Infrastructure.scope():
            with self.assertRaises(DataFactoryError):
                buffer.readline()
            self.assertEqual(Infrastructure.current()[0].code, 34187)

    def test_sql_respects_explicit_result_budget_over_one_hundred_and_never_truncates(self):
        from sqlalchemy import create_engine, text
        from src.apps.data_factory.services.sql.sql_query import DataFactorySqlQuery
        engine = create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE example (id INTEGER PRIMARY KEY)'))
            connection.execute(text('INSERT INTO example (id) VALUES (:id)'), [{'id': index} for index in range(201)])
        with patch('src.apps.data_factory.services.sql.sql_query.DataFactoryDatasource.create_engine', return_value=engine), \
                patch.object(engine, 'dispose'):
            result = DataFactorySqlQuery.query(Mock(), 'SELECT id FROM example ORDER BY id', limit=250, allow_query=True)
            self.assertEqual(len(result['rows']), 201)
            self.assertEqual(result['rows'][-1]['id'], 200)
            with Infrastructure.scope():
                with self.assertRaises(DataFactoryError) as caught:
                    DataFactorySqlQuery.query(Mock(), 'SELECT id FROM example ORDER BY id', limit=200, allow_query=True)
                self.assertEqual(caught.exception.code, 34194)
                self.assertIn('200 行', caught.exception.msg)
                self.assertIn('至少 201 行', caught.exception.msg)
                self.assertEqual(Infrastructure.current(), [])
