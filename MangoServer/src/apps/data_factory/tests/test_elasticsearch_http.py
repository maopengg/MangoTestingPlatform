import io
from contextlib import nullcontext
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.models import Database
from src.apps.data_factory.services.datasource_discovery import DataSourceDiscoveryService
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.elasticsearch_http import open_elasticsearch_request


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class ElasticsearchHttpTests(SimpleTestCase):
    def setUp(self):
        governor = patch('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.operation',
                         side_effect=lambda target, **kwargs: nullcontext())
        governor.start()
        self.addCleanup(governor.stop)
        for method in ('start', 'finish_success', 'finish_failure'):
            patcher = patch('src.apps.data_factory.services.sql_execution_audit.SqlExecutionAuditService.' + method)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_data_source_opener_disables_proxy_without_installing_global_opener(self):
        request = Request('https://es.example.com:9200/_cluster/health')
        context = MagicMock()
        target = MagicMock()
        with patch('src.apps.data_factory.services.elasticsearch_http.httpx.Client') as client, \
                patch('src.apps.data_factory.services.elasticsearch_http.ProtocolPoolRegistry.borrow') as borrow:
            def pool(_target, protocol, factory):
                return nullcontext(factory(2))
            borrow.side_effect = pool
            response = client.return_value.stream.return_value.__enter__.return_value
            response.status_code = 200
            response.iter_bytes.return_value = iter([b'{}'])
            with open_elasticsearch_request(request, target=target, timeout=5, context=context) as result:
                self.assertEqual(result.read(), b'{}')
            self.assertFalse(client.call_args.kwargs['trust_env'])
            self.assertFalse(client.call_args.kwargs['follow_redirects'])
            self.assertIs(client.call_args.kwargs['verify'], context)

    def test_metadata_errors_keep_their_classification(self):
        database = Database(id=10, db_type=20, host='es.example.com', port=9200,
                            user='tester', password='secret', extra_config={}, update_time=timezone.now())
        failures = [
            (HTTPError('http://es.example.com', 401, 'Unauthorized', {}, io.BytesIO(b'{}')), 34171),
            (HTTPError('http://es.example.com', 403, 'Forbidden', {}, io.BytesIO(b'{}')), 34035),
            (HTTPError('http://es.example.com', 502, 'Bad Gateway', {}, io.BytesIO(b'{}')), 34040),
            (URLError('connection refused'), 34039),
        ]
        for error, code in failures:
            with self.subTest(code=code), \
                    patch.object(DataSourceDiscoveryService, 'get_database', return_value=database), \
                    patch('src.apps.data_factory.services.datasource_discovery.open_elasticsearch_request',
                          side_effect=error), \
                    patch(
                        'src.apps.data_factory.services.datasource_discovery.DataSourceConnectionService.timeout_seconds',
                        return_value=5):
                with self.assertRaises(DataFactoryError) as raised:
                    DataSourceDiscoveryService.tables(DatasourceTargetService.maintenance(database), refresh=True)
                self.assertEqual(code, raised.exception.code)
                self.assertNotIn('元数据权限', raised.exception.msg)
