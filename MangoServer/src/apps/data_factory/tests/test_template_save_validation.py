from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.api.serializers.template import DataFactoryTemplateSerializer
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.models import DataFactoryTemplate, DataFactoryTemplateItem
from src.apps.data_factory.services.runner import DataFactoryRunner
from src.apps.data_factory.services.template import (
    DataFactoryTemplateMutationService,
    DataFactoryTemplateService,
)


class TemplateSaveValidationTests(SimpleTestCase):
    @contextmanager
    def mutation_validation_context(self):
        template = SimpleNamespace(id=9, status=1, project_product_id=1, module_id=4, entity_id=2, name='场景')
        queryset = Mock()
        queryset.exists.return_value = False
        queryset.exclude.return_value = queryset
        with (
            patch('src.apps.data_factory.services.template.ProductModule.objects.get',
                  return_value=SimpleNamespace(project_product_id=1)),
            patch('src.apps.data_factory.services.template.DataFactoryEntity.objects.get',
                  return_value=SimpleNamespace(project_product_id=1, module_id=4)),
            patch.object(DataFactoryTemplate.objects, 'filter', return_value=queryset),
            patch.object(DataFactoryTemplate.objects, 'select_for_update') as locked,
            patch.object(DataFactoryTemplateService, 'configuration_snapshot', return_value={}),
            patch('src.apps.data_factory.services.template.save_model') as save,
        ):
            locked.return_value.get.return_value = template
            yield template, save

    @staticmethod
    def mutation_payload(items):
        return {'project_product': 1, 'module': 4, 'entity': 2, 'name': '场景', 'items': items}

    def test_invalid_child_overrides_are_business_errors_before_create_or_update(self):
        payload = self.mutation_payload([
            {'child_template': 3, 'field_overrides': {}},
            {'child_template': 5, 'field_overrides': {
                'source_type': {'generator_type': 1, 'generator_config': {}, 'value': 1},
            }},
        ])
        for operation in ('create', 'update'):
            with self.subTest(operation=operation), self.mutation_validation_context() as (template, save):
                with self.assertRaises(DataFactoryError) as raised:
                    method = getattr(DataFactoryTemplateMutationService, operation).__wrapped__
                    if operation == 'create':
                        method(DataFactoryTemplateMutationService, payload)
                    else:
                        method(DataFactoryTemplateMutationService, template.id, payload)
                self.assertEqual(raised.exception.code, 34005)
                self.assertIn('关联模板第 2 项', str(raised.exception))
                self.assertIn('source_type.value', str(raised.exception))
                save.assert_not_called()

    def test_valid_child_overrides_preserve_zero_and_do_not_mutate_request(self):
        payload = self.mutation_payload([{'child_template': 3, 'field_overrides': {
            'source_type': {'generator_type': 1, 'generator_config': {'value': 0}},
        }}])
        original = deepcopy(payload)
        with self.mutation_validation_context():
            _, items = DataFactoryTemplateMutationService._validated_payload(payload)
        self.assertEqual(items[0]['field_overrides']['source_type']['generator_config']['value'], 0)
        self.assertEqual(payload, original)
        self.assertIsNot(items[0], payload['items'][0])

    def test_child_with_no_overrides_and_omitted_items_keep_existing_semantics(self):
        with self.mutation_validation_context():
            _, items = DataFactoryTemplateMutationService._validated_payload(
                self.mutation_payload([{'child_template': 3}]),
            )
            self.assertEqual(items, [{'child_template': 3, 'field_overrides': {}}])
            _, items = DataFactoryTemplateMutationService._validated_payload(self.mutation_payload(None))
            self.assertIsNone(items)
            _, items = DataFactoryTemplateMutationService._validated_payload(self.mutation_payload([]))
            self.assertEqual(items, [])

    def test_activation_ignores_page_environment_and_uses_global_configuration(self):
        bindings = Mock()
        bindings.all.return_value = [
            SimpleNamespace(environment=0, test_object_id=None),
            SimpleNamespace(environment=2, test_object_id=None),
        ]
        template = SimpleNamespace(entity=SimpleNamespace(datasource_alias=SimpleNamespace(
            datafactorydatasourcebinding_set=bindings,
        )))
        with patch(
                "src.apps.data_factory.services.template.SystemConfigService."
                "get_data_factory_validation_environments", return_value=[0],
        ):
            self.assertEqual(DataFactoryTemplateService.activation_environments(template, 2), [0])

    def test_unconfigured_activation_checks_all_bound_environments(self):
        bindings = Mock()
        bindings.all.return_value = [
            SimpleNamespace(environment=0, test_object_id=None),
            SimpleNamespace(environment=3, test_object_id=None),
        ]
        template = SimpleNamespace(entity=SimpleNamespace(datasource_alias=SimpleNamespace(
            datafactorydatasourcebinding_set=bindings,
        )))
        with patch(
                "src.apps.data_factory.services.template.SystemConfigService."
                "get_data_factory_validation_environments", return_value=None,
        ):
            self.assertEqual(DataFactoryTemplateService.activation_environments(template, 2), [0, 3])

    def test_metadata_save_preserves_readiness_without_business_database_validation(self):
        template = SimpleNamespace(id=4, status=1, config_status=1)
        snapshot = {"entity_id": 4, "field_overrides": {}, "items": []}
        with (
            patch.object(DataFactoryTemplateService, "configuration_snapshot", return_value=snapshot),
            patch.object(DataFactoryTemplateService, "mark_configuration_pending") as pending,
            patch.object(DataFactoryTemplateService, "set_status") as set_status,
            patch.object(DataFactoryTemplateService, "validate_activation") as validate,
        ):
            result = DataFactoryTemplateService.finish_configuration_save(
                template, before=snapshot, previous_status=1, target_status=1,
            )
        self.assertIs(result, template)
        self.assertEqual(result.config_status, 1)
        pending.assert_not_called()
        set_status.assert_not_called()
        validate.assert_not_called()

    def test_rule_changes_save_as_pending_without_reactivation(self):
        template = SimpleNamespace(id=4, status=1)
        with (
            patch.object(DataFactoryTemplateService, "configuration_snapshot", return_value={"rules": "new"}),
            patch.object(DataFactoryTemplateService, "mark_configuration_pending") as pending,
            patch.object(DataFactoryTemplateService, "set_status") as set_status,
        ):
            result = DataFactoryTemplateService.finish_configuration_save(
                template, before={"rules": "old"}, previous_status=1, target_status=1,
            )
        self.assertIs(result, template)
        pending.assert_called_once_with(template)
        set_status.assert_not_called()

    def test_activation_transition_uses_shared_status_service_without_page_environment(self):
        template = SimpleNamespace(id=4, status=0)
        with (
            patch.object(DataFactoryTemplateService, "configuration_snapshot", return_value={}),
            patch.object(DataFactoryTemplateService, "set_status", return_value=template) as status,
        ):
            DataFactoryTemplateService.finish_configuration_save(
                template, before={}, previous_status=0, target_status=1, operator_id=7,
            )
        status.assert_called_once_with(4, 1, update_user_id=7)

    def test_rule_changes_invalidate_recursive_parents_without_disabling(self):
        template = SimpleNamespace(id=4, config_status=1)
        parents = Mock()
        parents.values_list.side_effect = [[8], [12], [4]]
        queryset = Mock()
        with (
            patch.object(DataFactoryTemplateItem.objects, "filter", return_value=parents),
            patch.object(DataFactoryTemplate.objects, "filter", return_value=queryset) as query,
        ):
            affected = DataFactoryTemplateService.mark_configuration_pending(template)
        self.assertEqual(affected, {4, 8, 12})
        query.assert_called_once_with(id__in={4, 8, 12})
        self.assertEqual(queryset.update.call_args.kwargs["config_status"], 0)
        self.assertNotIn("status", queryset.update.call_args.kwargs)
        self.assertEqual(template.config_status, 0)

    def test_pending_configuration_cannot_execute(self):
        template = SimpleNamespace(id=4, name="测试模板", status=1, config_status=0)
        with self.assertRaises(DataFactoryError):
            DataFactoryRunner.require_template_entities_available(template)

    def test_readiness_is_server_controlled(self):
        serializer = DataFactoryTemplateSerializer()
        self.assertTrue(serializer.fields["config_status"].read_only)

    def test_mcp_mutation_update_uses_same_save_transition(self):
        instance = SimpleNamespace(id=4, status=1)
        query = Mock()
        query.get.return_value = instance
        with (
            patch.object(DataFactoryTemplate.objects, "select_for_update", return_value=query),
            patch.object(DataFactoryTemplateService, "configuration_snapshot", return_value={}),
            patch.object(DataFactoryTemplateMutationService, "_validated_payload",
                         return_value=({"cleanup_strategy": 1, "status": 1, "config_status": 1}, None)),
            patch("src.apps.data_factory.services.template.save_model", return_value=instance) as save,
            patch.object(DataFactoryTemplateMutationService, "_sync_after_save"),
            patch.object(DataFactoryTemplateService, "finish_configuration_save", return_value=instance) as finish,
            patch("src.apps.data_factory.services.template.model_payload", return_value={"id": 4}),
        ):
            DataFactoryTemplateMutationService.update.__wrapped__(
                DataFactoryTemplateMutationService, 4, {"cleanup_strategy": 1},
            )
        self.assertNotIn("status", save.call_args.args[1])
        self.assertNotIn("config_status", save.call_args.args[1])
        finish.assert_called_once_with(
            instance, before={}, previous_status=1, target_status=1, operator_id=None,
        )
