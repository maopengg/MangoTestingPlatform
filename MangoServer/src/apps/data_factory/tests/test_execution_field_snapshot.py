from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from src.apps.data_factory.services.execution.execution_metadata import DataFactoryExecutionMetadata as Metadata


class ExecutionFieldSnapshotTests(SimpleTestCase):
    def test_609_rows_read_rules_once_but_generate_from_isolated_fields(self):
        entity = SimpleNamespace(pk=7, datafactoryfield_set=Mock())
        rules = entity.datafactoryfield_set.all.return_value.order_by
        rules.return_value = [SimpleNamespace(name='id', generator_config={'value': ['AUTO_ORIGINAL']})]
        with Metadata.scope():
            for _ in range(609):
                fields = Metadata.fields(entity)
                self.assertEqual(fields[0].generator_config, {'value': ['AUTO_ORIGINAL']})
                fields[0].generator_config['value'].append('AUTO_MUTATED')
        rules.assert_called_once_with('sort', 'id')
        with Metadata.scope():
            Metadata.fields(entity)
        self.assertEqual(rules.call_count, 2)

    def test_entities_and_nested_executions_do_not_share_rules(self):
        first, second = [SimpleNamespace(pk=pk, datafactoryfield_set=Mock()) for pk in (1, 2)]
        for entity in (first, second):
            entity.datafactoryfield_set.all.return_value.order_by.return_value = [entity.pk]
        with Metadata.scope():
            self.assertEqual(Metadata.fields(first), [1])
            self.assertEqual(Metadata.fields(second), [2])
            with Metadata.scope():
                Metadata.fields(first)
            Metadata.fields(first)
        self.assertEqual(first.datafactoryfield_set.all.call_count, 2)
        self.assertEqual(second.datafactoryfield_set.all.call_count, 1)

    def test_outside_execution_scope_does_not_cache(self):
        entity = SimpleNamespace(pk=7, datafactoryfield_set=Mock())
        entity.datafactoryfield_set.all.return_value.order_by.return_value = []
        Metadata.fields(entity)
        Metadata.fields(entity)
        self.assertEqual(entity.datafactoryfield_set.all.call_count, 2)
