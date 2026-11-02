from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.apps import apps
from django.http import QueryDict
from django.test import SimpleTestCase

from src.apps.auto_api.models import ApiCase, ApiCaseDetailed
from src.apps.user.constants import RELATED_PRODUCT_SCOPE_PATHS
from src.apps.user.services.model_crud_scope import ModelCrudDataScopePolicy as Policy


class CrudDataScopeTests(SimpleTestCase):
    def setUp(self):
        self.request = SimpleNamespace(method='PUT', data={}, query_params=QueryDict(),
                                       user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
        unrestricted = patch.object(Policy, '_unrestricted', return_value=False)
        unrestricted.start()
        self.addCleanup(unrestricted.stop)

    def test_all_declared_parent_scope_paths_are_valid_orm_queries(self):
        for label, paths in RELATED_PRODUCT_SCOPE_PATHS.items():
            model = apps.get_model(label)
            for path in paths:
                with self.subTest(label=label, path=path):
                    # Constructing a query resolves every relationship without executing SQL.
                    self.assertIn('SELECT', str(model.objects.filter(**{f'{path}__in': [1]}).query))

    def test_child_lists_filter_by_their_parent_product(self):
        queryset = Mock()
        with patch.object(Policy, '_allowed_ids', return_value=[11, 12]):
            Policy.filter_queryset(ApiCaseDetailed, self.request, queryset, set())
        predicate = queryset.filter.call_args.args[0]
        self.assertEqual(predicate.children, [('case__project_product_id__in', [11, 12])])

    def test_child_creation_cannot_attach_to_an_inaccessible_parent(self):
        self.request.method = 'POST'
        with patch.object(Policy, 'filter_queryset') as visible, patch.object(ApiCase.objects, 'filter'):
            visible.return_value.exists.return_value = False
            self.assertFalse(Policy.has_data_permission(ApiCaseDetailed, self.request, {'case': 9}, set()))
            self.assertFalse(Policy.has_data_permission(ApiCaseDetailed, self.request, {}, set()))
            visible.return_value.exists.return_value = True
            self.assertTrue(Policy.has_data_permission(ApiCaseDetailed, self.request, {'case': 9}, set()))

    def test_direct_and_batch_ids_must_all_be_visible(self):
        self.request.query_params = QueryDict('id[]=1&id[]=2')
        with patch.object(Policy, 'has_data_permission', return_value=True), \
                patch.object(ApiCaseDetailed.objects, 'filter'), patch.object(Policy, 'filter_queryset') as visible:
            visible.return_value.count.return_value = 1
            self.assertFalse(Policy.has_request_permission(ApiCaseDetailed, self.request, set()))
            visible.return_value.count.return_value = 2
            self.assertTrue(Policy.has_request_permission(ApiCaseDetailed, self.request, set()))

    def test_instance_checks_use_the_actual_parent_model(self):
        parent = ApiCase(id=4, project_product_id=11)
        with patch.object(Policy, 'has_data_permission', return_value=True) as check:
            self.assertTrue(Policy.has_instance_permission(ApiCaseDetailed, self.request, parent, set()))
        self.assertIs(check.call_args.args[0], ApiCase)
