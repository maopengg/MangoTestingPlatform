import io
import json
from contextlib import nullcontext
from unittest.mock import MagicMock, patch
from urllib import error as urllib_error

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.models import Database
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService


def query_target(**values):
    options = values.get('extra_config', {})
    redis_db = options.pop('database', None)
    return DatasourceTargetService.build(Database(id=1, update_time=timezone.now(), **values), redis_db=redis_db)


from src.apps.data_factory.services.datasource.data_source_query import DataFactoryDatasourceQuery
from src.apps.test_center.enums.data_source import (
    DataSourceCategoryEnum,
    DataSourceTypeEnum,
)


class _RedisConnection:
    def __init__(self, response: bytes):
        self.reader = io.BytesIO(response)
        self.writes = io.BytesIO()

    def write(self, value):
        return self.writes.write(value)

    def flush(self):
        return None

    def read(self, size=-1):
        return self.reader.read(size)

    def readline(self, size=-1):
        return self.reader.readline(size)

    def close(self):
        return None


class DataFactoryDatasourceQueryTests(SimpleTestCase):
    def setUp(self):
        # 协议测试隔离审计持久化；审计接入、脱敏与失败闭环由独立测试覆盖。
        for method in ('start', 'finish_success', 'finish_failure'):
            patcher = patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionAuditService.' + method)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_query_permission_is_required_for_every_source_type(self):
        data_source = query_target(
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
        )

        with self.assertRaises(Exception) as error:
            DataFactoryDatasourceQuery.query(data_source, {'command': 'GET user:1'}, allow_query=False)

        self.assertIn('未开启读取权限', str(error.exception))

    @patch('src.apps.data_factory.services.datasource.data_source_query.DataFactorySqlQuery.query')
    def test_relational_query_keeps_existing_sql_query_implementation(self, sql_query):
        sql_query.return_value = {'columns': ['id'], 'rows': [{'id': 1}]}
        data_source = query_target(
            source_category=DataSourceCategoryEnum.DATABASE.value,
            db_type=DataSourceTypeEnum.MYSQL.value,
        )

        result = DataFactoryDatasourceQuery.query(
            data_source,
            {'sql': 'SELECT id FROM users'},
            allow_query=True,
        )

        self.assertEqual(result['rows'], [{'id': 1}])
        sql_query.assert_called_once_with(
            data_source,
            'SELECT id FROM users',
            limit=100,
            allow_query=True,
        )

    def test_redis_write_command_is_rejected_before_connection(self):
        data_source = query_target(
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
        )

        with self.assertRaises(Exception) as error:
            DataFactoryDatasourceQuery.query_redis(data_source, 'SET user:1 mango')

        self.assertIn('只读查询命令', str(error.exception))

    def test_redis_factory_uses_real_supported_constructor_and_owns_its_pool(self):
        import redis

        constructed = []
        client = MagicMock()
        client.connection_pool.get_connection.return_value.read_response.return_value = 'OK'

        def borrow(target, protocol, factory):
            actual = factory(2)
            constructed.append(actual)
            self.addCleanup(actual.close)
            return nullcontext(client)

        target = query_target(source_category=DataSourceCategoryEnum.CACHE.value,
                              db_type=DataSourceTypeEnum.REDIS.value,
                              host='redis.example.com', port=6379)
        with patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.borrow', side_effect=borrow):
            result = DataFactoryDatasourceQuery.execute_redis(
                target, 'SET AUTO_example value NX EX 60', allow_query=True, allow_write=True)
        self.assertEqual(result['result'], 'OK')
        self.assertIsInstance(constructed[0], redis.Redis)
        self.assertTrue(constructed[0].auto_close_connection_pool)
        self.assertEqual(constructed[0].connection_pool.max_connections, 2)

    def test_redis_read_query_supports_array_response(self):
        connection = MagicMock()
        connection.read_response.return_value = ['Mango', '3']
        client = MagicMock()
        client.connection_pool.get_connection.return_value = connection
        data_source = query_target(
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
            host='redis.example.com',
            port=6379,
            extra_config={'database': 0, 'ssl': False},
        )

        with patch(
                'src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.borrow',
                return_value=nullcontext(client),
        ):
            result = DataFactoryDatasourceQuery.query_redis(data_source, 'HMGET user:1 name age')

        self.assertEqual(result['result'], ['Mango', '3'])
        connection.send_command.assert_called_once_with('HMGET', 'user:1', 'name', 'age')

    def test_small_hash_complete_result_reaches_case_without_command_name_rejection(self):
        connection = MagicMock()
        connection.read_response.return_value = ['name', 'AUTO_example', 'state', 'ready']
        client = MagicMock()
        client.connection_pool.get_connection.return_value = connection
        target = query_target(source_category=DataSourceCategoryEnum.CACHE.value,
                              db_type=DataSourceTypeEnum.REDIS.value, host='redis.example.com', port=6379,
                              extra_config={'database': 0})
        with patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.borrow', return_value=nullcontext(client)):
            result = DataFactoryDatasourceQuery.query_redis(target, 'HGETALL AUTO_hash')
        self.assertEqual(result['result'], ['name', 'AUTO_example', 'state', 'ready'])
        connection.send_command.assert_called_once_with('HGETALL', 'AUTO_hash')

    def test_redis_server_wrong_type_error_is_preserved(self):
        from redis.exceptions import ResponseError
        connection = MagicMock()
        connection.read_response.side_effect = ResponseError('WRONGTYPE Operation against a key holding the wrong kind of value')
        client = MagicMock()
        client.connection_pool.get_connection.return_value = connection
        data_source = query_target(
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
            host='redis.example.com',
            port=6379,
            extra_config={'database': 0, 'ssl': False},
        )

        with patch(
                'src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.borrow',
                return_value=nullcontext(client),
        ), self.assertRaises(Exception) as error:
            DataFactoryDatasourceQuery.query_redis(data_source, 'HGET user:1 name')

        self.assertIn('Redis数据类型不匹配', str(error.exception))
        self.assertIn('WRONGTYPE', str(error.exception))

    def test_elasticsearch_query_only_calls_index_search_and_preserves_json(self):
        response = MagicMock()
        response.read.return_value = b'{"hits":{"total":{"value":1},"hits":[{"_id":"1","_source":{"name":"Mango"}}]}}'
        response.__enter__.return_value = response
        data_source = query_target(
            source_category=DataSourceCategoryEnum.SEARCH.value,
            db_type=DataSourceTypeEnum.ELASTICSEARCH.value,
            host='es.example.com',
            port=9200,
            user='reader',
            password='secret',
            extra_config={'scheme': 'https', 'path_prefix': 'search', 'verify_certs': False},
        )

        with patch(
                'src.apps.data_factory.services.datasource.data_source_query.open_elasticsearch_request',
                return_value=response,
        ) as urlopen:
            result = DataFactoryDatasourceQuery.query_elasticsearch(
                data_source,
                'orders',
                {'query': {'match_all': {}}, 'size': 50},
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, 'https://es.example.com:9200/search/orders/_search')
        self.assertEqual(json.loads(request.data.decode('utf-8'))['size'], 50)
        self.assertEqual(result['result']['hits']['hits'][0]['_source']['name'], 'Mango')

    def test_elasticsearch_index_cannot_escape_search_path(self):
        data_source = query_target(
            source_category=DataSourceCategoryEnum.SEARCH.value,
            db_type=DataSourceTypeEnum.ELASTICSEARCH.value,
        )

        with self.assertRaises(Exception) as error:
            DataFactoryDatasourceQuery.query_elasticsearch(data_source, '_cluster/health', {})

        self.assertIn('索引名称', str(error.exception))

    def test_elasticsearch_http_error_exposes_query_reason(self):
        response_body = json.dumps({
            'error': {
                'type': 'parsing_exception',
                'reason': 'unknown query [matc]',
                'root_cause': [{
                    'type': 'parsing_exception',
                    'reason': 'unknown query [matc]',
                }],
            },
            'status': 400,
        }).encode('utf-8')
        http_error = urllib_error.HTTPError(
            'http://es.example.com:9200/orders/_search',
            400,
            'Bad Request',
            {},
            io.BytesIO(response_body),
        )
        data_source = query_target(
            source_category=DataSourceCategoryEnum.SEARCH.value,
            db_type=DataSourceTypeEnum.ELASTICSEARCH.value,
            host='es.example.com',
            port=9200,
        )

        with patch(
                'src.apps.data_factory.services.datasource.data_source_query.open_elasticsearch_request',
                side_effect=http_error,
        ), self.assertRaises(Exception) as error:
            DataFactoryDatasourceQuery.query_elasticsearch(
                data_source,
                'orders',
                {'query': {'matc': {'name': 'Mango'}}},
            )

        self.assertIn('Elasticsearch查询语法错误', str(error.exception))
        self.assertIn('unknown query [matc]', str(error.exception))
