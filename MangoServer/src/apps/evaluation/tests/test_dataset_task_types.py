from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from pydantic import ValidationError

from src.apps.evaluation.api.serializers.dataset import DatasetSerializer
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.models import EvaluationDataset
from src.apps.evaluation.schemas.assets import EvaluationDatasetAssetCreate, EvaluationDatasetTaskTypes
from src.apps.evaluation.services.assets.assets import ensure_dataset
from src.apps.evaluation.services.assets.validation import validate_dataset
from src.apps.evaluation.api.views.dataset import DatasetCRUD
from src.apps.evaluation.selectors.assets import filter_dataset_task_types
from src.apps.evaluation.selectors.scope import ensure_dataset_access, scope_dataset_queryset
from src.apps.evaluation.selectors.dataset_version import get_dataset_version
from src.apps.user.services.authorization.permission import PermissionMenuService


class DatasetTaskTypesTests(SimpleTestCase):
    def test_dataset_contract_has_no_project_product_or_module(self):
        fields = {field.name for field in EvaluationDataset._meta.fields}
        self.assertFalse({'project_product', 'module', 'tags'} & fields)
        self.assertFalse({'project_product', 'module', 'tags', 'project_product_data', 'module_data'} & set(DatasetSerializer().fields))
        data = EvaluationDatasetAssetCreate(name='跨产品题库', task_type=['记忆'])
        self.assertEqual(data.task_type, ['记忆'])
        for key in ('project_product_id', 'module_id'):
            with self.assertRaises(ValidationError):
                EvaluationDatasetAssetCreate.model_validate({'name': '题库', 'task_type': ['记忆'], key: 1})

    def test_global_dataset_access_requires_dataset_permission_even_with_project_access(self):
        user, queryset = Mock(), Mock()
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'evaluation.case:read'}):
            self.assertIs(scope_dataset_queryset(queryset, user), queryset.none.return_value)
            with self.assertRaises(EvaluationError):
                ensure_dataset_access(user)
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'evaluation.dataset'}):
            self.assertIs(scope_dataset_queryset(queryset, user), queryset)
            ensure_dataset_access(user)
        self.assertIs(scope_dataset_queryset(queryset, None), queryset.none.return_value)

    def test_global_version_access_uses_dataset_permission(self):
        from types import SimpleNamespace
        version = SimpleNamespace(dataset=EvaluationDataset(pk=3))
        with patch('src.apps.evaluation.selectors.dataset_version.EvaluationQuerySelector.dataset_versions') as query, \
                patch('src.apps.evaluation.selectors.dataset_version.ensure_dataset_access') as access:
            query.return_value.filter.return_value.first.return_value = version
            self.assertIs(get_dataset_version(5, 'user'), version)
            access.assert_called_once_with('user')

    def test_global_dataset_creation_never_creates_project_relations(self):
        with patch('src.apps.evaluation.services.assets.assets.ensure_dataset_access'), \
                patch('src.apps.evaluation.services.assets.assets.EvaluationDataset.objects') as manager:
            manager.filter.return_value.first.return_value = None
            user = Mock()
            ensure_dataset.__wrapped__({'name': '题库', 'task_type': ['记忆，问答']}, user)
            values = manager.create.call_args.kwargs
            self.assertEqual(values['task_type'], ['记忆', '问答'])
            self.assertNotIn('project_product', values)
            self.assertNotIn('module', values)

    def test_task_search_applies_membership_after_data_scope(self):
        request = Mock(query_params={'task_types': '["记忆", "问答"]'})
        original, scoped, filtered = Mock(), Mock(), Mock()
        with patch('src.apps.evaluation.api.views.dataset.scope_dataset_queryset', return_value=scoped) as scope, \
                patch('src.apps.evaluation.api.views.dataset.filter_dataset_task_types', return_value=filtered) as membership:
            result = DatasetCRUD().filter_queryset_by_data_scope(request, original)
        scope.assert_called_once_with(original, request.user.user_obj)
        membership.assert_called_once_with(scoped, ['记忆', '问答'])
        self.assertIs(result, filtered)

    def test_task_search_rejects_invalid_json_filters(self):
        with patch('src.apps.evaluation.api.views.dataset.scope_dataset_queryset', return_value=Mock()):
            for value in ('记忆', '{"type":"记忆"}', '[1]'):
                with self.assertRaises(EvaluationError):
                    DatasetCRUD().filter_queryset_by_data_scope(Mock(query_params={'task_types': value}), Mock())

    def test_multiple_task_labels_match_any_whole_array_member(self):
        queryset = filter_dataset_task_types(EvaluationDataset.objects.all(), ['记忆', '问答'])
        condition = queryset.query.where.children[0]
        self.assertEqual(condition.connector, 'OR')
        self.assertEqual([lookup.lookup_name for lookup in condition.children], ['contains', 'contains'])
        self.assertEqual([lookup.rhs for lookup in condition.children], [['记忆'], ['问答']])

    def test_task_types_are_free_json_labels_at_both_boundaries(self):
        values = [' 记忆，问答 ', '记忆', '自定义能力', '']
        expected = ['记忆', '问答', '自定义能力']
        self.assertEqual(EvaluationDatasetTaskTypes(task_type=values).task_type, expected)
        self.assertEqual(DatasetSerializer().validate_task_type(values), expected)
        self.assertEqual(EvaluationDataset().task_type, [])
        self.assertEqual(EvaluationDataset._meta.get_field('task_type').get_internal_type(), 'JSONField')

    def test_task_types_reject_legacy_scalar_and_arbitrary_json(self):
        for value in ([], [' ', '，'], 'generation', {'记忆': True}, [1], [None], ['x' * 65]):
            with self.assertRaises(ValidationError):
                EvaluationDatasetTaskTypes(task_type=value)
            with self.assertRaises(EvaluationError):
                DatasetSerializer().validate_task_type(value)

    def test_published_dataset_can_update_task_labels_without_modifying_version_contents(self):
        record = Mock(project_product=None, module=Mock())
        record.versions.exists.return_value = True
        values = {'task_type': ['记忆', '问答']}
        self.assertEqual(validate_dataset(values, record), values)
