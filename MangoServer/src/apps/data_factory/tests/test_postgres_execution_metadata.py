from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from sqlalchemy import Column, Integer, MetaData, Table

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.execution.execution_metadata import DataFactoryExecutionMetadata as Metadata


class PostgresExecutionMetadataTests(SimpleTestCase):
    def setUp(self):
        self.target = SimpleNamespace(cache_key='binding-1-version-1', schema_name='fixture')
        self.entity = SimpleNamespace(table_name='example')
        self.engine, self.connection = Mock(), Mock()
        self.engine.dialect.name = 'postgresql'
        self.engine.connect.return_value = nullcontext(self.connection)
        self.definition = {'relation': [1, 'fixture', 'example'],
                           'columns': [[1, 'id', 'integer', False]], 'constraints': ['PRIMARY KEY (id)']}
        self.connection.execute.return_value.scalar_one_or_none.side_effect = lambda: deepcopy(self.definition)
        self.table = Table('example', MetaData(), Column('id', Integer, primary_key=True), schema='fixture')
        guard = patch('src.apps.data_factory.services.execution.execution_metadata.Table', return_value=self.table)
        self.reflect = guard.start()
        self.addCleanup(guard.stop)

    def test_609_inserts_reflect_once_but_check_live_structure_every_time(self):
        with Metadata.scope():
            for _ in range(609):
                table, kinds = Metadata.resolve(self.entity, self.target, self.engine, connection=self.connection)
                self.assertIs(table, self.table)
                self.assertEqual(kinds, {})
        self.assertEqual(self.reflect.call_count, 1)
        self.assertEqual(self.connection.execute.call_count, 610)
        self.engine.connect.assert_not_called()

    def test_any_structural_drift_and_recreated_table_are_rejected(self):
        for key in ('relation', 'columns', 'constraints', 'indexes', 'types'):
            with self.subTest(key=key), Metadata.scope():
                original = deepcopy(self.definition)
                Metadata.resolve(self.entity, self.target, self.engine)
                self.definition[key] = ['AUTO_CHANGED']
                with self.assertRaises(DataFactoryError):
                    Metadata.resolve(self.entity, self.target, self.engine)
                self.definition = original

    def test_schema_change_during_first_reflection_is_rejected(self):
        self.connection.execute.return_value.scalar_one_or_none.side_effect = [self.definition, {'relation': [2]}]
        with Metadata.scope(), self.assertRaises(DataFactoryError):
            Metadata.resolve(self.entity, self.target, self.engine)

    def test_missing_definition_does_not_fall_back_to_stale_metadata(self):
        with Metadata.scope():
            Metadata.resolve(self.entity, self.target, self.engine)
            self.connection.execute.return_value.scalar_one_or_none.side_effect = [None]
            with self.assertRaises(DataFactoryError):
                Metadata.resolve(self.entity, self.target, self.engine)

    def test_execution_engine_binding_and_schema_boundaries_do_not_share_reflection(self):
        other_engine = Mock()
        other_engine.dialect.name = 'postgresql'
        with Metadata.scope():
            Metadata.resolve(self.entity, self.target, self.engine, connection=self.connection)
            Metadata.resolve(self.entity, self.target, other_engine, connection=self.connection)
            Metadata.resolve(self.entity, SimpleNamespace(cache_key='binding-2', schema_name='fixture'),
                             self.engine, connection=self.connection)
            Metadata.resolve(self.entity, SimpleNamespace(cache_key=self.target.cache_key, schema_name='other'),
                             self.engine, connection=self.connection)
        with Metadata.scope():
            Metadata.resolve(self.entity, self.target, self.engine, connection=self.connection)
        self.assertEqual(self.reflect.call_count, 5)

    def test_definition_uses_bound_identifiers_and_includes_generated_and_unique_constraints(self):
        name = 'AUTO_quoted"name'
        Metadata.read_definition(self.connection, 'postgresql', name, 'fixture')
        statement, values = self.connection.execute.call_args.args
        self.assertEqual(values, {'schema_name': 'fixture', 'table_name': name})
        self.assertNotIn(name, str(statement))
        for token in ('attidentity', 'attgenerated', 'attnotnull', 'pg_get_constraintdef',
                      'pg_get_indexdef', 'pg_enum', 'typbasetype', 'typelem', 'to_regclass'):
            self.assertIn(token, str(statement))
