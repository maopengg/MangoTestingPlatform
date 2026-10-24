import io
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
    def test_data_source_opener_disables_proxy_without_installing_global_opener(self):
        request = Request('https://es.example.com:9200/_cluster/health')
        context = MagicMock()
        with patch('src.apps.data_factory.services.elasticsearch_http.urllib_request.build_opener') as build, \
                patch('src.apps.data_factory.services.elasticsearch_http.urllib_request.install_opener') as install:
            result = open_elasticsearch_request(request, timeout=5, context=context)
            handlers = build.call_args.args
            self.assertEqual({}, handlers[0].proxies)
            self.assertIs(context, handlers[1]._context)
            build.return_value.open.assert_called_once_with(request, timeout=5)
            self.assertIs(result, build.return_value.open.return_value)
            install.assert_not_called()

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
