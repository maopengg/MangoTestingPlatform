from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import models
from django.http import QueryDict
from django.test import SimpleTestCase

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.data_factory.api.views.template import DataFactoryTemplateCRUD
from src.apps.data_factory.exceptions import DATA_FACTORY_TEMPLATE_DELETE_REFERENCED, DataFactoryError
from src.apps.data_factory.models import DataFactoryTemplate
from src.apps.data_factory.models.template import DataFactoryTemplateQuerySet
from src.apps.data_factory.services.assets.template_deletion import DataFactoryTemplateDeletionService as Deletion
from src.interfaces.mcp.tools.data_factory.template import register_template_tools


class TemplateDeletionTests(SimpleTestCase):
    def impact(self, *, configs=None, parents=None, releases=None, items=0):
        configs = configs or []
        parents = parents or []
        query = Mock()
        query.values.return_value.__getitem__ = Mock(return_value=configs)
        query.count.return_value = len(configs)
        parent_query = Mock()
        parent_query.values.return_value.__getitem__ = Mock(return_value=parents)
        parent_query.count.return_value = len(parents)
        item_query = Mock()
        item_query.count.return_value = items
        with (
            patch('src.apps.data_factory.services.assets.template_deletion.DataFactoryCaseConfig.objects') as manager,
            patch('src.apps.data_factory.services.assets.template_deletion.DataFactoryTemplateItem.objects') as parent_manager,
            patch('src.apps.data_factory.services.assets.template_deletion.DataFactoryExecutionItem.objects') as item_manager,
            patch.object(ApiQuerySelector, 'data_factory_template_release_references', return_value=releases or []),
        ):
            manager.using.return_value.filter.return_value = query
            parent_manager.using.return_value.filter.return_value = parent_query
            item_manager.using.return_value.filter.return_value = item_query
            return Deletion.impact(SimpleNamespace(pk=4, name='模板'))

    def test_unreferenced_template_can_delete(self):
        self.assertTrue(self.impact()['can_delete'])

    def test_disabled_case_binding_also_blocks_delete(self):
        result = self.impact(configs=[{'id': 2, 'source_type': 1, 'source_id': 51, 'status': 0}])
        self.assertFalse(result['can_delete'])
        self.assertIn('Case 51', result['delete_blockers'][0])

    def test_parent_template_blocks_delete(self):
        result = self.impact(parents=[{'template_id': 12, 'template__name': '主场景'}])
        self.assertIn('主场景 / ID 12', result['delete_blockers'][0])

    def test_published_snapshot_blocks_without_current_binding(self):
        result = self.impact(releases=[{'id': 20, 'api_case_id': 51}])
        self.assertFalse(result['can_delete'])
        self.assertIn('Case 51 / 发布 20', result['delete_blockers'][0])

    def test_execution_item_protection_matches_preview(self):
        result = self.impact(items=2)
        self.assertFalse(result['can_delete'])
        self.assertEqual(result['protected_execution_item_count'], 2)

    def test_validation_returns_structured_business_error(self):
        impact = {'can_delete': False, 'delete_blockers': ['Case 51'], 'template_id': 4}
        with patch.object(Deletion, 'impact', return_value=impact), self.assertRaises(DataFactoryError) as caught:
            Deletion.validate(SimpleNamespace(name='模板'))
        self.assertEqual(caught.exception.details, impact)

    def test_model_delete_uses_shared_validation(self):
        template = DataFactoryTemplate(id=4, name='模板')
        with (
            patch('src.apps.data_factory.models.template.transaction.atomic', return_value=nullcontext()),
            patch.object(DataFactoryTemplate.objects, 'using'),
            patch.object(Deletion, 'validate', side_effect=DataFactoryError(
                DATA_FACTORY_TEMPLATE_DELETE_REFERENCED, value=('模板', 'Case 51'),
            )) as validate,
            patch.object(models.Model, 'delete') as delete,
            self.assertRaises(DataFactoryError),
        ):
            template.delete()
        validate.assert_called_once_with(template, using='default')
        delete.assert_not_called()

    def test_queryset_validates_all_before_deleting_any(self):
        queryset = DataFactoryTemplateQuerySet(model=DataFactoryTemplate)
        templates = [DataFactoryTemplate(id=4, name='可删'), DataFactoryTemplate(id=8, name='被引用')]
        with (
            patch('src.apps.data_factory.models.template.transaction.atomic', return_value=nullcontext()),
            patch.object(queryset, 'select_for_update') as lock,
            patch.object(Deletion, 'validate', side_effect=[None, RuntimeError('blocked')]) as validate,
            patch.object(models.QuerySet, 'delete') as delete,
            self.assertRaises(RuntimeError),
        ):
            lock.return_value.order_by.return_value = templates
            queryset.delete()
        self.assertEqual(validate.call_count, 2)
        delete.assert_not_called()

    def test_mcp_delete_only_calls_shared_service_after_confirmation(self):
        registered = {}
        mcp = Mock()

        def decorator(function):
            registered[function.__name__] = function
            return function

        mcp.tool.return_value = decorator
        register_template_tools(mcp)
        with (
            patch('src.interfaces.mcp.tools.data_factory.template.validate_dangerous_action_confirmation',
                  return_value=None),
            patch('src.interfaces.mcp.tools.data_factory.template.DataFactoryTemplateMutationService.delete') as delete,
        ):
            registered['delete_data_factory_template'](4, 'token', 'confirmation')
        delete.assert_called_once_with(4)

    def test_page_bulk_delete_uses_service_and_preserves_audit(self):
        template = SimpleNamespace(pk=4)
        view = SimpleNamespace(
            model=Mock(), has_instance_data_scope_permission=Mock(return_value=True),
            capture_config_snapshot=Mock(return_value=SimpleNamespace(snapshot={'id': 4})),
            record_config_delete=Mock(),
        )
        view.model.objects.filter.return_value.select_for_update.return_value.order_by.return_value = [template]
        request = SimpleNamespace(query_params=QueryDict('id[]=4&id[]=8'))
        with (
            patch('src.apps.data_factory.api.views.template.transaction.atomic', return_value=nullcontext()),
            patch('django.db.transaction.Atomic.__enter__'),
            patch('django.db.transaction.Atomic.__exit__', return_value=False),
            patch.object(Deletion, 'delete_many') as delete,
        ):
            DataFactoryTemplateCRUD.delete(view, request)
        delete.assert_called_once_with([4, 8])
        view.record_config_delete.assert_called_once_with(template, {'id': 4}, request=request)

    def test_page_returns_reference_details_without_recording_delete(self):
        view = SimpleNamespace(model=Mock(), record_config_delete=Mock())
        view.model.objects.filter.return_value.select_for_update.return_value.order_by.return_value = []
        request = SimpleNamespace(query_params=QueryDict('id=4'))
        error = DataFactoryError(DATA_FACTORY_TEMPLATE_DELETE_REFERENCED,
                                 value=('模板', 'Case 51'), details={'template_id': 4})
        with (
            patch('src.apps.data_factory.api.views.template.transaction.atomic', return_value=nullcontext()),
            patch('django.db.transaction.Atomic.__enter__'),
            patch('django.db.transaction.Atomic.__exit__', return_value=False),
            patch.object(Deletion, 'delete_many', side_effect=error),
        ):
            response = DataFactoryTemplateCRUD.delete(view, request)
        self.assertEqual(response.data['data'], {'template_id': 4})
        self.assertIn('Case 51', response.data['msg'])
        view.record_config_delete.assert_not_called()

    def test_release_selector_checks_old_and_new_snapshot_paths(self):
        rows = [
            {'id': 1, 'api_case_id': 51, 'revision__payload': {'data_factory_configs': [{'template': 4}]}},
            {'id': 2, 'api_case_id': 52, 'revision__payload': {
                'dependencies': {'data_factory_configs': [{'template': 4}]}}},
            {'id': 3, 'api_case_id': 53, 'revision__payload': {'data_factory_configs': [{'template': 5}]}},
        ]
        with (
            patch('src.apps.auto_api.selectors.querysets.ApiCaseRelease.objects') as manager,
            patch('django.db.connections') as connections,
        ):
            connections.__getitem__.return_value.features.supports_json_field_contains = False
            manager.using.return_value.filter.return_value.values.return_value.iterator.return_value = rows
            result = ApiQuerySelector.data_factory_template_release_references(4)
        self.assertEqual([row['id'] for row in result], [1, 2])
        self.assertIn('deprecated', manager.using.return_value.filter.call_args.kwargs['status__in'])
