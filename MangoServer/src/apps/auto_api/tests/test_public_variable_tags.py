from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch
from importlib import import_module

from django.test import SimpleTestCase

from src.apps.auto_api.api.serializers.api_pulic import ApiPublicSerializers
from src.apps.auto_api.api.views.api_pulic import ApiPublicCRUD
from src.apps.auto_api.services.api_public import ApiPublicMutationService
from src.apps.auto_api.services.api_auth_config import ApiAuthConfigService
from src.apps.auto_ui.api.serializers.ui_public import UiPublicSerializers
from src.apps.auto_ui.api.views.ui_public import UiPublicCRUD
from src.apps.auto_ui.services.asset_mutation import UiAssetMutationService
from src.common.database.variable_tags import update_variable_tags
from src.common.exceptions import MangoServerError
from src.common.utils.variable_tags import normalize_variable_tags, filter_variable_tags, summarize_variable_tags


class PublicVariableTagTests(SimpleTestCase):
    def test_normalize_and_validate_without_null_or_scalar_coercion(self):
        self.assertEqual(normalize_variable_tags([' tenant-a ', '', 'tenant-a', 'shared']), ['tenant-a', 'shared'])
        for invalid in (None, 'tenant', [1], ['a' * 33], [str(i) for i in range(21)]):
            with self.subTest(invalid=invalid), self.assertRaises(MangoServerError):
                normalize_variable_tags(invalid)
        for serializer in (ApiPublicSerializers(), UiPublicSerializers()):
            self.assertEqual(serializer.validate_tags(['a', ' a ']), ['a'])

    def test_missing_update_tags_is_not_clear_and_tags_are_metadata_only(self):
        record = SimpleNamespace(type=0, project_product_id=1, datasource_alias=None, test_envs=[], test_env=None)
        for validate in (ApiPublicMutationService._validated_payload, UiAssetMutationService._validate_public_variable):
            self.assertNotIn('tags', validate({'name': 'rename'}, record))
            self.assertEqual(validate({'tags': []}, record)['tags'], [])
        variable = SimpleNamespace(id=1, type=0, key='tenant', value='a', test_envs=[], tags=['a'])
        before = ApiAuthConfigService.public_variables_checksum([variable])
        variable.tags = ['b']
        self.assertEqual(ApiAuthConfigService.public_variables_checksum([variable]), before)

    def test_exact_json_filter_and_unclassified_are_mutually_exclusive(self):
        query = Mock()
        filter_variable_tags(query, ' a ')
        query.filter.assert_called_once_with(tags__contains=['a'])
        query.reset_mock()
        filter_variable_tags(query, untagged=True)
        query.filter.assert_called_once_with(tags=[])
        with self.assertRaises(MangoServerError):
            filter_variable_tags(query, 'a', True)

    def test_summary_is_unpaged_deduplicated_and_never_reads_values(self):
        query = Mock()
        query.values_list.return_value.iterator.return_value = iter([['a', 'a', 'b'], [], ['b']])
        result = summarize_variable_tags(query)
        self.assertEqual(result, {'total': 3, 'untagged': 1,
                                 'items': [{'name': 'a', 'count': 1}, {'name': 'b', 'count': 2}]})
        query.values_list.assert_called_once_with('tags', flat=True)

    def test_list_and_summary_use_same_scoped_queryset_before_pagination(self):
        for view_class, selector_path in (
                (ApiPublicCRUD, 'src.apps.auto_api.api.views.api_pulic.ApiPublicTagSelector'),
                (UiPublicCRUD, 'src.apps.auto_ui.api.views.ui_public.UiPublicTagSelector')):
            with patch(selector_path) as selector:
                view = view_class()
                queryset = Mock()
                selector.summarize.return_value = {'total': 3, 'untagged': 1, 'items': []}
                response = view.list_response(SimpleNamespace(query_params={'tag_summary': 'true'}), queryset, True)
                self.assertEqual(response.data['data']['total'], 3)
                selector.summarize.assert_called_once_with(queryset)
                selector.filter.assert_not_called()


class PublicVariableBatchTagTests(SimpleTestCase):
    def test_http_batch_uses_authorized_queryset_and_existing_menu(self):
        for view_class, service_path in (
                (ApiPublicCRUD, 'src.apps.auto_api.api.views.api_pulic.ApiPublicMutationService.set_tags'),
                (UiPublicCRUD, 'src.apps.auto_ui.api.views.ui_public.UiAssetMutationService.set_public_tags')):
            with patch(service_path, return_value={'count': 1}) as service:
                view = view_class()
                scoped = Mock()
                view.filter_queryset_by_data_scope = Mock(return_value=scoped)
                request = SimpleNamespace(data={'ids': [1], 'tags': ['a'], 'tag_operation': 0}, user={'id': 4})
                view.put(request)
                service.assert_called_once_with(scoped, [1], ['a'], 0, 4)
                self.assertIn(view.page_permission_key, ('api.public', 'ui.public'))

    def row(self, tags):
        return SimpleNamespace(tags=list(tags), save=Mock(), key='unchanged', value='unchanged', status=1)

    def apply(self, rows, ids, tags, operation):
        query = Mock()
        query.filter.return_value.select_for_update.return_value.order_by.return_value = rows
        return update_variable_tags.__wrapped__(query, ids, tags, operation, 4)

    def test_add_remove_replace_and_clear_only_change_tags(self):
        for operation, tags, expected in ((0, ['b'], ['a', 'b']), (1, ['a'], []), (2, ['b'], ['b']), (2, [], [])):
            row = self.row(['a'])
            self.apply([row], [1], tags, operation)
            self.assertEqual(row.tags, expected)
            self.assertEqual((row.key, row.value, row.status), ('unchanged', 'unchanged', 1))
            row.save.assert_called_once_with(update_fields=['tags', 'update_user', 'update_time'])

    def test_mixed_scope_missing_rows_rejected_without_any_write(self):
        row = self.row(['a'])
        with self.assertRaises(MangoServerError):
            self.apply([row], [1, 2], ['b'], 0)
        row.save.assert_not_called()

    def test_unchanged_is_noop_and_all_rows_validate_before_writes(self):
        row = self.row(['a'])
        self.apply([row], [1], ['a'], 0)
        row.save.assert_not_called()
        oversized = self.row([str(i) for i in range(20)])
        with self.assertRaises(MangoServerError):
            self.apply([row, oversized], [1, 2], ['extra'], 0)
        row.save.assert_not_called()


class PublicVariableMcpTagTests(SimpleTestCase):
    def tools(self, kind):
        tools = {}

        class Registry:
            def tool(self):
                def register(function):
                    tools[function.__name__] = function
                    return function
                return register

        module = import_module(f'src.interfaces.mcp.tools.{kind}.public_variable')
        module.register_public_variable_tools(Registry())
        return module, tools

    def test_existing_mcp_list_supports_tags_without_new_tools(self):
        for kind, prefix in (('api', 'Api'), ('ui', 'Ui')):
            module, tools = self.tools(kind)
            query = MagicMock()
            query.select_related.return_value = query
            query.filter.return_value = query
            query.order_by.return_value = query
            query.count.return_value = 1
            query.__getitem__.return_value = [SimpleNamespace(id=1, project_product_id=1, test_env=None,
                test_envs=[], type=0, name='fixture', key='key', value='value', datasource_alias_id=None,
                status=1, tags=['tenant-a'])]
            with patch.object(getattr(module, f'{prefix}QuerySelector'), f'{kind}_public', return_value=query), \
                    patch.object(getattr(module, f'{prefix}PublicTagSelector'), 'filter', return_value=query) as filtering, \
                    patch.object(getattr(module, f'{prefix}PublicTagSelector'), 'summarize', return_value={'total': 1}):
                result = tools[f'list_{kind}_public_variables'](1, tag='tenant-a', include_tag_summary=True)
                self.assertEqual(result['data']['items'][0]['tags'], ['tenant-a'])
                self.assertEqual(result['data']['tag_summary'], {'total': 1})
                filtering.assert_called_once_with(query, 'tenant-a', False)

    def test_existing_mcp_update_distinguishes_omitted_tags_and_clear(self):
        for kind, service_name, method_name in (('api', 'ApiPublicMutationService', 'update'),
                                                ('ui', 'UiAssetMutationService', 'update_public_variable')):
            module, tools = self.tools(kind)
            with patch.object(getattr(module, service_name), method_name, return_value={'id': 1}) as save, \
                    patch.object(module, 'mcp_current_user_id', return_value=4, create=True), \
                    patch.object(module, 'mcp_with_update_user', side_effect=lambda data: data, create=True):
                tools[f'update_{kind}_public_variable'](1, name='renamed')
                self.assertNotIn('tags', save.call_args.args[1])
                tools[f'update_{kind}_public_variable'](1, tags=[])
                self.assertEqual(save.call_args.args[1]['tags'], [])
