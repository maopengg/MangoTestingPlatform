# -*- coding: utf-8 -*-
import io
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.models import Database
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
from src.apps.test_center.api.serializers.data_source import DataSourceSerializer
from src.apps.test_center.enums.data_source import (
    DataSourceCategoryEnum,
    DataSourceTypeEnum,
)
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.services.datasource.data_source import DataSourceConnectionService
from src.common.exceptions import ErrorDefinition


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


class DataSourceConnectionServiceTests(SimpleTestCase):
    def test_redis_diagnostics_normalize_connection_before_describing_target(self):
        database = Database(
            id=1, update_time=timezone.now(),
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
            host='redis.example.com', port=6379, extra_config={},
        )
        bound = DatasourceTargetService.build(database, redis_db=2)
        for source, expected in ((database, 0), (bound, 2)):
            with self.subTest(expected=expected), \
                    patch.object(DataSourceConnectionService, '_diagnose_network', return_value={'status': 'passed'}), \
                    patch.object(DataSourceConnectionService, '_test_redis', return_value={'ping': 'PONG'}) as ping:
                result = DataSourceConnectionService.diagnose_connection(source)
                self.assertTrue(result['connected'])
                self.assertEqual(ping.call_args.args[0].redis_db, expected)
                self.assertEqual(result['checks'][-1]['message'], f'Redis DB {expected} 可正常访问')

    def setUp(self):
        super().setUp()
        for method in ('start', 'finish_success', 'finish_failure'):
            patcher = patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionAuditService.' + method)
            patcher.start()
            self.addCleanup(patcher.stop)
        # 连接诊断测试不访问配置库；重复校验由配置服务专项测试覆盖。
        validator = patch(
            'src.apps.test_center.api.serializers.data_source.DataSourceConfigurationService.validate_unique')
        validator.start()
        self.addCleanup(validator.stop)

    @staticmethod
    def _mysql_data_source():
        return Database(
            id=1,
            update_time=timezone.now(),
            source_category=DataSourceCategoryEnum.DATABASE.value,
            db_type=DataSourceTypeEnum.MYSQL.value,
            display_name='订单测试库',
            host='mysql.internal',
            port=3306,
            user='tester',
            password='secret',
        )

    @patch.object(DataSourceConnectionService, 'test_connection')
    @patch.object(DataSourceConnectionService, '_diagnose_network')
    def test_connection_diagnosis_stops_when_domain_or_port_is_unreachable(
            self,
            diagnose_network,
            test_connection,
    ):
        diagnose_network.return_value = {
            'key': 'network', 'name': '域名解析与端口访问',
            'status': 'failed', 'message': '域名解析失败',
        }

        result = DataSourceConnectionService.diagnose_connection(self._mysql_data_source())

        self.assertFalse(result['connected'])
        self.assertEqual([item['status'] for item in result['checks']], ['failed', 'skipped', 'skipped'])
        test_connection.assert_not_called()

    @patch.object(DataSourceConnectionService, 'test_connection')
    @patch.object(DataSourceConnectionService, '_diagnose_network')
    def test_connection_diagnosis_reports_password_or_configuration_failure(
            self,
            diagnose_network,
            test_connection,
    ):
        diagnose_network.return_value = {
            'key': 'network', 'name': '域名解析与端口访问',
            'status': 'passed', 'message': 'mysql.internal:3306 可访问',
        }
        test_connection.side_effect = TestCenterError(
            ErrorDefinition(code=300, message='Access denied for user tester')
        )

        result = DataSourceConnectionService.diagnose_connection(self._mysql_data_source())

        self.assertFalse(result['connected'])
        self.assertEqual([item['status'] for item in result['checks']], ['passed', 'failed', 'skipped'])
        self.assertNotIn('secret', result['error'])

    @patch.object(DataSourceConnectionService, 'test_connection')
    @patch.object(DataSourceConnectionService, '_diagnose_network')
    def test_connection_diagnosis_reports_target_database_success(
            self,
            diagnose_network,
            test_connection,
    ):
        data_source = self._mysql_data_source()
        diagnose_network.return_value = {
            'key': 'network', 'name': '域名解析与端口访问',
            'status': 'passed', 'message': 'mysql.internal:3306 可访问',
        }
        test_connection.return_value = DataSourceConnectionService._result(
            data_source,
            {'database': {'connected': True}},
        )

        result = DataSourceConnectionService.diagnose_connection(data_source)

        self.assertTrue(result['connected'])
        self.assertEqual([item['status'] for item in result['checks']], ['passed', 'passed', 'passed'])

    @patch.object(DataSourceConnectionService, '_test_redis')
    @patch.object(DataSourceConnectionService, '_diagnose_network')
    def test_redis_diagnosis_uses_the_same_target_for_connection_and_success_message(
            self,
            diagnose_network,
            test_redis,
    ):
        diagnose_network.return_value = {
            'key': 'network', 'name': '域名解析与端口访问',
            'status': 'passed', 'message': 'redis.example.com:6379 可访问',
        }
        database = Database(
            id=2, update_time=timezone.now(),
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
            display_name='缓存连接', host='redis.example.com', port=6379,
            extra_config={'ssl': False},
        )
        self.assertFalse(hasattr(database, 'redis_db'))

        for source, database_index in (
                (database, 0),
                (DatasourceTargetService.build(database, redis_db=3), 3),
        ):
            with self.subTest(database_index=database_index):
                test_redis.reset_mock()
                test_redis.return_value = {
                    'protocol': 'redis', 'database': database_index, 'ping': 'PONG',
                }

                result = DataSourceConnectionService.diagnose_connection(source)

                target = test_redis.call_args.args[0]
                self.assertEqual(target.redis_db, database_index)
                if source is not database:
                    self.assertIs(target, source)
                self.assertTrue(result['connected'])
                self.assertIsNone(result['error'])
                self.assertEqual(result['details']['database'], database_index)
                self.assertEqual([item['status'] for item in result['checks']], ['passed'] * 3)
                self.assertEqual(
                    result['checks'][-1]['message'], f'Redis DB {database_index} 可正常访问',
                )

    def test_relational_database_keeps_optional_alias_separate_from_database_name(self):
        serializer = DataSourceSerializer(data={
            "source_category": DataSourceCategoryEnum.DATABASE.value,
            "db_type": DataSourceTypeEnum.MYSQL.value,
            "display_name": "订单测试库",
            "name": "order_service",
            "host": "mysql.internal",
            "port": 3306,
            "user": "tester",
            "password": "secret",
            "extra_config": {},
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["display_name"], "订单测试库")
        self.assertNotIn("name", serializer.validated_data)

    def test_postgresql_also_uses_database_name_as_connection_name(self):
        serializer = DataSourceSerializer(data={
            "source_category": DataSourceCategoryEnum.DATABASE.value,
            "db_type": DataSourceTypeEnum.POSTGRESQL.value,
            "display_name": "分析连接",
            "host": "postgres.internal",
            "port": 5432,
            "user": "tester",
            "extra_config": {},
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["display_name"], "分析连接")

    def test_mysql_connection_url_targets_configured_database(self):
        data_source = Database(
            source_category=DataSourceCategoryEnum.DATABASE.value,
            db_type=DataSourceTypeEnum.MYSQL.value,
            id=1, update_time=timezone.now(),
            host="mysql.internal",
            port=3306,
            user="tester",
            password="secret",
        )
        target = DatasourceTargetService.build(data_source, database_name='order_service')
        self.assertIn("mysql.internal:3306/order_service", DataFactoryDatasource.build_url(target))

    def test_postgresql_connection_url_targets_configured_database(self):
        data_source = Database(
            source_category=DataSourceCategoryEnum.DATABASE.value,
            db_type=DataSourceTypeEnum.POSTGRESQL.value,
            id=1, update_time=timezone.now(),
            host="postgres.internal",
            port=5432,
            user="tester",
            password="secret",
        )
        target = DatasourceTargetService.build(data_source, database_name='analytics')
        self.assertIn("postgres.internal:5432/analytics", DataFactoryDatasource.build_url(target))

    def test_redis_serializer_accepts_empty_optional_alias(self):
        serializer = DataSourceSerializer(data={
            "source_category": DataSourceCategoryEnum.CACHE.value,
            "db_type": DataSourceTypeEnum.REDIS.value,
            "host": "redis.internal",
            "port": 6379,
            "display_name": "缓存连接",
            "extra_config": {"ssl": False},
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["display_name"], "缓存连接")

    def test_non_relational_source_uses_technical_identifier_without_alias(self):
        redis = Database(
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
            display_name="",
            host="redis.internal",
            port=6379,
            extra_config={"database": 2},
        )
        elasticsearch = Database(
            source_category=DataSourceCategoryEnum.SEARCH.value,
            db_type=DataSourceTypeEnum.ELASTICSEARCH.value,
            display_name="",
            host="es.internal",
            port=9200,
            extra_config={"path_prefix": "search"},
        )
        self.assertEqual(DataSourceConnectionService.connection_name(redis), "redis.internal:6379")
        self.assertEqual(DataSourceConnectionService.display_label(redis), "redis.internal:6379")
        self.assertEqual(DataSourceConnectionService.connection_name(elasticsearch), "es.internal:9200/search")

    def test_serializer_rejects_mismatched_category(self):
        serializer = DataSourceSerializer(data={
            "source_category": DataSourceCategoryEnum.SEARCH.value,
            "db_type": DataSourceTypeEnum.REDIS.value,
            "display_name": "错误分类",
            "host": "redis.internal",
            "port": 6379,
            "extra_config": {},
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("source_category", serializer.errors)

    def test_redis_connection_sends_ping_and_parses_pong(self):
        connection = _RedisConnection(b"+PONG\r\n")
        raw_socket = MagicMock()
        raw_socket.makefile.return_value = connection
        data_source = Database(
            id=1, update_time=timezone.now(),
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
            display_name="缓存",
            host="redis.internal",
            port=6379,
            extra_config={"database": 0, "ssl": False},
        )

        with patch("src.apps.test_center.services.datasource.data_source.socket.create_connection", return_value=raw_socket):
            result = DataSourceConnectionService.test_connection(data_source)

        self.assertTrue(result["connected"])
        self.assertTrue(result["capabilities"]["key_value"])
        self.assertEqual(result["details"]["ping"], "PONG")
        self.assertIn(b"PING", connection.writes.getvalue())

    def test_elasticsearch_connection_reads_cluster_health(self):
        response = MagicMock()
        response.read.return_value = (
            b'{"cluster_name":"search-test","status":"green","number_of_nodes":3,"number_of_data_nodes":2}'
        )
        response.__enter__.return_value = response
        data_source = Database(
            id=2, update_time=timezone.now(),
            source_category=DataSourceCategoryEnum.SEARCH.value,
            db_type=DataSourceTypeEnum.ELASTICSEARCH.value,
            display_name="检索集群",
            host="es.internal",
            port=9200,
            extra_config={"scheme": "http", "path_prefix": "", "verify_certs": True},
        )

        with patch("src.apps.test_center.services.datasource.data_source.open_elasticsearch_request", return_value=response):
            result = DataSourceConnectionService.test_connection(data_source)

        self.assertTrue(result["connected"])
        self.assertTrue(result["capabilities"]["search"])
        self.assertEqual(result["details"]["cluster_name"], "search-test")
        self.assertEqual(result["details"]["status"], "green")

    def test_non_sql_source_is_rejected_by_sql_capability(self):
        data_source = Database(
            source_category=DataSourceCategoryEnum.CACHE.value,
            db_type=DataSourceTypeEnum.REDIS.value,
        )
        with self.assertRaises(Exception) as error:
            DataSourceConnectionService.require_sql(data_source)
        self.assertIn("不支持 SQL", str(error.exception))
