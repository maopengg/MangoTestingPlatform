from types import SimpleNamespace
from unittest.mock import Mock, patch
import sqlite3
from contextlib import closing

from django.db.backends.sqlite3.base import DatabaseWrapper
from django.db.models.query import get_related_populators
from django.test import SimpleTestCase

from src.apps.auto_api.api.serializers.api_info import ApiInfoListQuery, ApiInfoListSerializersC, ApiInfoSummarySerializers
from src.apps.auto_api.api.views.api_info import ApiInfoCRUD
from src.apps.auto_api.enums import MethodEnum
from src.apps.auto_api.models import ApiInfo, ApiInfoHttpConfig, ApiInfoWebSocketConfig, ApiInfoRevision, ApiInfoRelease
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.test_center.models import Project, ProjectProduct, ProductModule
from src.apps.user.models import User


class ApiInfoListSerializerTests(SimpleTestCase):

    def test_id_filter_still_uses_publication_state_serializer(self):
        view = ApiInfoCRUD()
        view.request = SimpleNamespace(method='GET', query_params={'id': '6'})

        self.assertIs(view.get_serializer_class(), ApiInfoListSerializersC)

    def test_summary_is_explicit_and_does_not_change_legacy_detail_fields(self):
        view = ApiInfoCRUD()
        view.request = SimpleNamespace(method='GET', query_params={'summary': 'true'})
        self.assertIs(view.get_serializer_class(), ApiInfoSummarySerializers)
        self.assertFalse(view.is_valid_query_param('summary'))

    @staticmethod
    def info(protocol='http', config=None):
        info = ApiInfo(id=6, name='示例接口', url='/example', protocol_type=protocol,
                       project_product=None, module=None, update_user=None)
        info._state.fields_cache.update(http_config=None, websocket_config=None,
                                        mcp_protocol_config=None, grpc_protocol_config=None)
        if config is not None:
            info._state.fields_cache['websocket_config' if protocol == 'websocket' else 'http_config'] = config
        info.current_revision_id = 9
        info.current_revision_no = 2
        info.published_release_id = 3
        info.published_revision_id = 9
        info.published_version_label = 'v1'
        info.publication_status = 'published'
        info.has_unpublished_changes = False
        return info

    def test_preloaded_http_list_uses_one_payload_and_no_per_row_sql(self):
        config = ApiInfoHttpConfig(method=MethodEnum.POST.value, url='/example',
                                   body_config={'body': {'amount': 123}}, headers={'Accept': 'application/json'})
        infos = [self.info(config=config) for _ in range(20)]
        with patch.object(ApiInfoRuntimeService, 'current_payload', wraps=ApiInfoRuntimeService.current_payload) as payload:
            data = ApiInfoListSerializersC(infos, many=True).data
        self.assertEqual(payload.call_count, 20)
        self.assertEqual(data[0]['method'], MethodEnum.POST.value)
        self.assertEqual(data[0]['body_config'], config.body_config)
        self.assertEqual(data[0]['protocol_config']['config']['headers'], config.headers)

    def test_preloaded_missing_protocol_config_does_not_query_and_keeps_defaults(self):
        for protocol in ('http', 'sse', 'websocket', 'mcp', 'grpc'):
            with self.subTest(protocol=protocol):
                data = ApiInfoListSerializersC(self.info(protocol)).data
                self.assertEqual(data['protocol_type'], protocol)
                self.assertIsNone(data['mcp_binding'])
                self.assertIsNone(data['grpc_binding'])

    def test_websocket_preload_preserves_script_and_method(self):
        config = ApiInfoWebSocketConfig(url='/ws', headers={'X-Test': 'example'}, body_config={'steps': []})
        data = ApiInfoListSerializersC(self.info('websocket', config)).data
        self.assertEqual(data['method'], MethodEnum.WEBSOCKET_CONNECT.value)
        self.assertEqual(data['body_config'], config.body_config)

    def test_summary_never_builds_runtime_or_serializes_heavy_fields(self):
        info = self.info()
        info.method = MethodEnum.GET.value
        info.posterior_func = 'large configuration' * 1000
        with patch.object(ApiInfoRuntimeService, 'current_payload') as payload:
            data = ApiInfoSummarySerializers(info).data
        payload.assert_not_called()
        self.assertNotIn('posterior_func', data)
        self.assertNotIn('protocol_config', data)
        self.assertNotIn('body_config', data)
        self.assertEqual(data['published_release_id'], 3)

    def test_lists_do_not_prefetch_unused_revision_or_release_payloads(self):
        query = ApiInfoListSerializersC.setup_eager_loading(ApiInfo.objects.all())
        self.assertNotIn('revisions', query._prefetch_related_lookups)
        self.assertNotIn('releases', query._prefetch_related_lookups)
        self.assertIn('project_product__owners', query._prefetch_related_lookups)

    def test_summary_sql_only_joins_method_not_mcp_or_grpc_payloads(self):
        query = ApiInfoSummarySerializers.setup_eager_loading(ApiInfo.objects.all())
        self.assertFalse(query._prefetch_related_lookups)
        sql = str(query.query)
        self.assertIn('api_info_http_config', sql)
        self.assertNotIn('api_info_grpc_config', sql)
        self.assertNotIn('api_info_mcp_config', sql)
        self.assertNotIn('posterior_func', query.query.deferred_loading[0])
        self.assertFalse(query.query.deferred_loading[1])

    def test_summary_sql_executes_against_isolated_rows_and_preserves_publication_state(self):
        # 只创建内存 SQLite 表，不连接部署环境，也不运行迁移。
        compiler_connection = DatabaseWrapper({'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}, alias='summary_sql')
        query = ApiInfoSummarySerializers.setup_eager_loading(ApiInfo.objects.all()[:20])
        compiler = query.query.get_compiler(connection=compiler_connection)
        sql, params = compiler.as_sql()
        with closing(sqlite3.connect(':memory:')) as database:
            for model in (ApiInfo, ApiInfoHttpConfig, ApiInfoRevision, ApiInfoRelease, Project, ProjectProduct, ProductModule, User):
                columns = ', '.join(f'"{field.column}"' + (' INTEGER PRIMARY KEY' if field.primary_key else '')
                                    for field in model._meta.concrete_fields)
                database.execute(f'CREATE TABLE "{model._meta.db_table}" ({columns})')
            for table in ('project', 'project_product', 'product_module'):
                database.execute(f'INSERT INTO "{table}" (id) VALUES (1)')
            database.execute('UPDATE project_product SET project_id=1')
            for index in range(1, 22):
                database.execute('INSERT INTO api_info (id, name, url, protocol_type, status, project_product_id, module_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                 (index, f'示例 {index}', '/example', 'http', 1, 1, 1))
                database.execute('INSERT INTO api_info_http_config (id, api_info_id, method) VALUES (?, ?, ?)', (index, index, MethodEnum.POST.value))
            database.execute('INSERT INTO api_info_revision (id, api_info_id, revision_no) VALUES (9, 21, 1)')
            database.execute('INSERT INTO api_info_release (id, api_info_id, revision_id, version_no, version_label, is_current, status) VALUES (3, 21, 9, 1, ?, 1, ?)', ('v1', 'published'))
            cursor = database.execute(sql.replace('%s', '?'), params)
            fields = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            records = [{**dict(zip(fields, row)), '_api_id': row[0]} for row in rows]
        self.assertEqual(len(records), 20)
        self.assertEqual(records[0]['_api_id'], 21)
        self.assertEqual(records[0]['publication_status'], 'published')
        self.assertEqual(records[0]['method'], MethodEnum.POST.value)
        self.assertEqual(records[1]['publication_status'], 'unpublished')
        selected = compiler.klass_info['select_fields']
        start, end = selected[0], selected[-1] + 1
        names = [item[0].target.attname for item in compiler.select[start:end]]
        related = get_related_populators(compiler.klass_info, compiler.select, 'summary_sql')
        instances = []
        for row in rows:
            instance = ApiInfo.from_db('summary_sql', names, row[start:end])
            for populator in related:
                populator.populate(row, instance)
            for name, position in compiler.annotation_col_map.items():
                setattr(instance, name, row[position])
            instances.append(instance)
        # 没有注册 summary_sql 连接：任何遗漏预加载或 only 字段都会在序列化时失败。
        result = ApiInfoSummarySerializers(instances, many=True).data
        self.assertEqual(len(result), 20)
        self.assertEqual(result[0]['method'], MethodEnum.POST.value)
        self.assertEqual(result[0]['project_product']['project']['id'], 1)

    def test_pagination_caps_before_expensive_eager_loading(self):
        serializer = Mock()
        serializer.return_value.data = []
        def prepare(page):
            self.assertLessEqual(len(page), ApiInfoCRUD.max_page_size)
            return page
        serializer.setup_eager_loading.side_effect = prepare
        for size, page, expected in ((10000, 1, 200), (20, 2, 20), (0, -1, 1), (20, 99999, 3)):
            with self.subTest(size=size, page=page):
                ApiInfoCRUD.paging_list(size, page, list(range(403)), serializer)
                self.assertEqual(len(serializer.setup_eager_loading.call_args.args[0]), expected)

    def test_paging_query_rejects_invalid_formats_and_accepts_missing_defaults(self):
        for data in ({}, {'page': '2'}, {'pageSize': '10000', 'summary': 'true'}):
            self.assertTrue(ApiInfoListQuery(data=data).is_valid())
        for data in ({'page': '0'}, {'page': '-1'}, {'pageSize': '0'}, {'page': 'invalid'}, {'pageSize': '1.5'}):
            self.assertFalse(ApiInfoListQuery(data=data).is_valid())

    def test_sync_drops_preloaded_protocol_configs_before_writing(self):
        info = self.info(config=ApiInfoHttpConfig(method=MethodEnum.GET.value))
        with patch('src.apps.auto_api.services.api_info.runtime.ApiInfoHttpConfig.objects'), \
                patch('src.apps.auto_api.services.api_info.runtime.ApiInfoWebSocketConfig.objects'), \
                patch('src.apps.auto_api.services.api_info.runtime.ApiInfoMcpConfig.objects'), \
                patch('src.apps.auto_api.services.api_info.runtime.ApiInfoGrpcConfig.objects'):
            ApiInfoRuntimeService.sync_protocol_config(info)
        for key in ('http_config', 'websocket_config', 'mcp_protocol_config', 'grpc_protocol_config'):
            self.assertNotIn(key, info._state.fields_cache)

    def test_read_binding_does_not_prepare_descriptors_but_execution_does(self):
        info = self.info('grpc')
        file = SimpleNamespace(test_file=True, id=1)
        service = SimpleNamespace(id=1, name='example', package='example', service_name='Example',
                                  descriptor_file=file, descriptor_file_id=1, proto_content_hash='hash', tls_enabled=False)
        method = SimpleNamespace(id=2, name='Get', client_streaming=False, server_streaming=False,
                                 request_json_schema={}, response_json_schema={})
        info._state.fields_cache['grpc_protocol_config'] = SimpleNamespace(
            grpc_service=service, grpc_method=method, full_method='/Example/Get', request_message='Request',
            response_message='Response', proto_hash='hash', request_json_schema={}, response_json_schema={}, grpc_config={})
        with patch.object(ApiInfoRuntimeService, '_materialize_descriptor_file', return_value='/example.desc') as prepare:
            data = ApiInfoListSerializersC(info).data
            prepare.assert_not_called()
            self.assertIsNone(data['grpc_binding']['descriptor_file_path'])
            runtime = ApiInfoRuntimeService.current_payload(info)
            prepare.assert_called_once_with(file)
            self.assertEqual(runtime['grpc_binding']['descriptor_file_path'], '/example.desc')

    def test_mcp_snapshot_is_copied_and_captured_once(self):
        info = self.info('mcp')
        config = SimpleNamespace(binding_snapshot={'tool_name': 'example'}, mcp_config={'body_config': {}},
                                 input_schema={'type': 'object'}, output_schema=None, schema_hash='hash')
        info._state.fields_cache['mcp_protocol_config'] = config
        with patch.object(ApiInfoRuntimeService, 'capture_mcp_binding', wraps=ApiInfoRuntimeService.capture_mcp_binding) as capture:
            data = ApiInfoListSerializersC(info).data
        capture.assert_called_once_with(info)
        data['mcp_binding']['input_schema']['type'] = 'changed'
        self.assertEqual(config.input_schema['type'], 'object')
