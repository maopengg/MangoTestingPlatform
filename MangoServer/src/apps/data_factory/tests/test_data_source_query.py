import io
import json
from unittest.mock import MagicMock, patch
from urllib import error as urllib_error

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.models import Database
from src.apps.data_factory.services.datasource_target import DatasourceTargetService


def query_target(**values):
    options = values.get('extra_config', {})
    redis_db = options.pop('database', None)
    return DatasourceTargetService.build(Database(id=1, update_time=timezone.now(), **values), redis_db=redis_db)


from src.apps.data_factory.services.data_source_query import DataFactoryDatasourceQuery
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
    def test_query_permission_is_required_for_every_source_type(self):
        data_source = query_target(
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
        )

        with self.assertRaises(Exception) as error:
            DataFactoryDatasourceQuery.query(data_source, {'command': 'GET user:1'}, allow_query=False)

        self.assertIn('未开启读取权限', str(error.exception))

    @patch('src.apps.data_factory.services.data_source_query.DataFactorySqlQuery.query')
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

    def test_redis_read_query_supports_array_response(self):
        connection = _RedisConnection(
            b'*4\r\n$4\r\nname\r\n$5\r\nMango\r\n$3\r\nage\r\n:3\r\n'
        )
        raw_socket = MagicMock()
        raw_socket.makefile.return_value = connection
        data_source = query_target(
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
            host='redis.internal',
            port=6379,
            extra_config={'database': 0, 'ssl': False},
        )

        with patch(
                'src.apps.data_factory.services.data_source_query.socket.create_connection',
                return_value=raw_socket,
        ):
            result = DataFactoryDatasourceQuery.query_redis(data_source, 'HGETALL user:1')

        self.assertEqual(result['result'], ['name', 'Mango', 'age', 3])
        self.assertIn(b'HGETALL', connection.writes.getvalue())

    def test_redis_server_wrong_type_error_is_preserved(self):
        connection = _RedisConnection(
            b'-WRONGTYPE Operation against a key holding the wrong kind of value\r\n'
        )
        raw_socket = MagicMock()
        raw_socket.makefile.return_value = connection
        data_source = query_target(
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
            host='redis.internal',
            port=6379,
            extra_config={'database': 0, 'ssl': False},
        )

        with patch(
                'src.apps.data_factory.services.data_source_query.socket.create_connection',
                return_value=raw_socket,
        ), self.assertRaises(Exception) as error:
            DataFactoryDatasourceQuery.query_redis(data_source, 'HGETALL user:1')

        self.assertIn('Redis数据类型不匹配', str(error.exception))
        self.assertIn('WRONGTYPE', str(error.exception))

    def test_elasticsearch_query_only_calls_index_search_and_preserves_json(self):
        response = MagicMock()
        response.read.return_value = b'{"hits":{"total":{"value":1},"hits":[{"_id":"1","_source":{"name":"Mango"}}]}}'
        response.__enter__.return_value = response
        data_source = query_target(
            source_category=DataSourceCategoryEnum.SEARCH.value,
            db_type=DataSourceTypeEnum.ELASTICSEARCH.value,
            host='es.internal',
            port=9200,
            user='reader',
            password='secret',
            extra_config={'scheme': 'https', 'path_prefix': 'search', 'verify_certs': False},
        )

        with patch(
                'src.apps.data_factory.services.data_source_query.open_elasticsearch_request',
                return_value=response,
        ) as urlopen:
            result = DataFactoryDatasourceQuery.query_elasticsearch(
                data_source,
                'orders-*',
                {'query': {'match_all': {}}, 'size': 500},
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, 'https://es.internal:9200/search/orders-*/_search')
        self.assertEqual(json.loads(request.data.decode('utf-8'))['size'], 100)
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
            'http://es.internal:9200/orders/_search',
            400,
            'Bad Request',
            {},
            io.BytesIO(response_body),
        )
        data_source = query_target(
            source_category=DataSourceCategoryEnum.SEARCH.value,
            db_type=DataSourceTypeEnum.ELASTICSEARCH.value,
            host='es.internal',
            port=9200,
        )

        with patch(
                'src.apps.data_factory.services.data_source_query.open_elasticsearch_request',
                side_effect=http_error,
        ), self.assertRaises(Exception) as error:
            DataFactoryDatasourceQuery.query_elasticsearch(
                data_source,
                'orders',
                {'query': {'matc': {'name': 'Mango'}}},
            )

        self.assertIn('Elasticsearch查询语法错误', str(error.exception))
        self.assertIn('unknown query [matc]', str(error.exception))
