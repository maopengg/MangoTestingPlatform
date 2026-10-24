from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from sqlalchemy import BigInteger, Column, DateTime, Integer, JSON, MetaData, Numeric, String, Table, create_engine, \
    insert, select, text
from sqlalchemy.dialects.mysql import dialect as mysql_dialect
from sqlalchemy.dialects.postgresql import JSON as PostgreSQLJSON, JSONB, dialect as postgresql_dialect

from src.apps.data_factory.exceptions import DataFactoryError, DATA_FACTORY_RUNNER_PARTS_EXECUTION_PRIMARY_KEY_REQUIRED
from src.apps.data_factory.services.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.discover import DataFactoryDiscover
from src.apps.data_factory.services.execution_snapshot import DATA_FACTORY_INSERT_SNAPSHOT_KEY
from src.apps.data_factory.services.runner import DataFactoryRunner
from src.apps.data_factory.services.type_cast import DataFactoryTypeCast


class GeneratedColumnKindsTests(SimpleTestCase):
    def connection(self, ddl):
        connection = MagicMock()
        connection.dialect = mysql_dialect()
        connection.execute.return_value.first.return_value = ('factory_record', ddl)
        return connection

    def test_mysql_reads_distinct_generation_kinds_and_quotes_dotted_table_as_one_identifier(self):
        connection = self.connection(
            'CREATE TABLE `app.factory_record` (\n'
            ' `mango_id` bigint NOT NULL /*T![auto_rand] AUTO_RANDOM(5) */,\n'
            ' `mango_row_id` bigint NOT NULL AUTO_INCREMENT,\n'
            ' `title` varchar(64) DEFAULT \'AUTO_RANDOM\' COMMENT \'AUTO_INCREMENT\',\n'
            ' PRIMARY KEY (`mango_id`)\n)'
        )
        result = DataFactoryDiscover.get_mysql_generated_column_kinds(connection, 'app.factory_record', 'factory_db')
        self.assertEqual(result, {'mango_id': 'auto_random', 'mango_row_id': 'auto_increment'})
        statement = str(connection.execute.call_args.args[0])
        self.assertEqual(statement, 'SHOW CREATE TABLE factory_db.`app.factory_record`')

    def test_escaped_column_identifier_and_case_insensitive_attributes(self):
        connection = self.connection('CREATE TABLE `factory_record` (\n `row``id` bigint auto_increment\n)')
        self.assertEqual(
            DataFactoryDiscover.get_mysql_generated_column_kinds(connection, 'factory_record'),
            {'row`id': 'auto_increment'},
        )

    def test_other_dialects_do_not_execute_mysql_metadata_sql(self):
        connection = MagicMock()
        connection.dialect.name = 'postgresql'
        self.assertEqual(DataFactoryDiscover.get_mysql_generated_column_kinds(connection, 'factory_record'), {})
        connection.execute.assert_not_called()


class GeneratedKeyRecoveryTests(SimpleTestCase):
    primary_value = 7205759403792793686
    kinds = {'mango_id': 'auto_random', 'mango_row_id': 'auto_increment'}

    @contextmanager
    def storage(self, rows, *, unique_org=False):
        engine = create_engine('sqlite://')
        # SQLite stores fixture rows; TiDB generation and driver values are simulated separately.
        table = Table(
            'app.factory_record', MetaData(),
            Column('mango_id', BigInteger, primary_key=True, autoincrement=False),
            Column('mango_row_id', BigInteger),
            Column('title', String(128)),
            Column('org_id', BigInteger, unique=unique_org),
            Column('is_locked', Integer),
            Column('created_at', DateTime),
            Column('extra', JSON),
        )
        table.metadata.create_all(engine)
        try:
            with engine.begin() as connection:
                if rows:
                    connection.execute(insert(table), rows)
                yield connection, table
        finally:
            engine.dispose()

    def row(self, **overrides):
        return {
            'mango_id': self.primary_value, 'mango_row_id': 86,
            'title': 'AUTO_LOCKED_execution_1', 'org_id': 7, 'is_locked': 1,
            'created_at': datetime(2026, 10, 12, 12, 0, 0), **overrides,
        }

    def recover(self, connection, table, *, primary=None, lastrowid=86, payload=None, kinds=None, unique_key=''):
        payload = payload if payload is not None else {
            key: value for key, value in self.row().items() if key not in ('mango_id', 'mango_row_id')
        }
        created = dict(payload)
        DataFactoryRunner.merge_generated_values(
            connection=connection, table=table,
            result=SimpleNamespace(inserted_primary_key=(primary,), lastrowid=lastrowid),
            created=created, payload_fields=set(payload), unique_key=unique_key, select=select,
            generated_column_kinds=self.kinds if kinds is None else kinds,
        )
        return created

    def test_incorrect_primary_candidate_falls_back_to_generated_non_primary_column(self):
        with self.storage([self.row()]) as (connection, table):
            created = self.recover(connection, table, primary=86)
        self.assertEqual(created['mango_id'], self.primary_value)
        self.assertEqual(created['mango_row_id'], 86)

    def test_two_reflected_auto_columns_do_not_prevent_recovery(self):
        with self.storage([self.row()]) as (connection, table):
            table.c.mango_id.autoincrement = True
            table.c.mango_row_id.autoincrement = True
            created = self.recover(connection, table)
        self.assertEqual(created['mango_id'], self.primary_value)

    def test_auto_random_primary_return_is_not_assigned_to_row_number(self):
        rows = [self.row(), self.row(mango_id=90, mango_row_id=self.primary_value, title='OTHER_EXECUTION')]
        with self.storage(rows) as (connection, table):
            created = self.recover(connection, table, primary=self.primary_value, lastrowid=self.primary_value)
        self.assertEqual(created['mango_id'], self.primary_value)
        self.assertEqual(created['mango_row_id'], 86)
        self.assertEqual(DataFactoryTypeCast.to_jsonable(created)['mango_id'], str(self.primary_value))

    def test_single_auto_random_attribute_is_recognized_despite_missing_reflection_flag(self):
        with self.storage([self.row()]) as (connection, table):
            created = self.recover(
                connection, table, lastrowid=self.primary_value,
                kinds={'mango_id': 'auto_random'},
            )
        self.assertEqual(created['mango_id'], self.primary_value)

    def test_primary_collision_from_another_execution_is_rejected_then_fallback_continues(self):
        rows = [self.row(), self.row(mango_id=86, mango_row_id=12, title='OTHER_EXECUTION')]
        with self.storage(rows) as (connection, table):
            created = self.recover(connection, table, primary=86)
        self.assertEqual(created['mango_id'], self.primary_value)

    def test_same_title_in_wrong_tenant_is_not_accepted(self):
        with self.storage([self.row(org_id=8)]) as (connection, table):
            created = self.recover(connection, table, primary=self.primary_value)
        self.assertNotIn('mango_id', created)
        self.assertNotIn('mango_row_id', created)

    def test_identical_payload_with_two_distinct_candidate_records_is_ambiguous(self):
        rows = [self.row(), self.row(mango_id=86, mango_row_id=12)]
        with self.storage(rows) as (connection, table):
            created = self.recover(connection, table, primary=86)
        self.assertNotIn('mango_id', created)

    def test_non_unique_row_number_rejects_even_if_only_one_payload_matches(self):
        rows = [self.row(), self.row(mango_id=90, title='OTHER_EXECUTION')]
        with self.storage(rows) as (connection, table):
            created = self.recover(connection, table)
        self.assertNotIn('mango_id', created)

    def test_no_generated_value_does_not_use_a_non_unique_title(self):
        with self.storage([self.row()]) as (connection, table):
            created = self.recover(connection, table, lastrowid=0, unique_key='title')
        self.assertNotIn('mango_id', created)

    def test_zero_primary_candidate_is_discarded_without_losing_fallback(self):
        with self.storage([self.row()]) as (connection, table):
            created = self.recover(connection, table, primary=0)
        self.assertEqual(created['mango_id'], self.primary_value)

    def test_no_matching_record_does_not_leave_unverified_generated_values(self):
        with self.storage([]) as (connection, table):
            created = self.recover(connection, table, primary=86)
        self.assertNotIn('mango_id', created)
        self.assertNotIn('mango_row_id', created)

    def test_user_supplied_primary_is_not_replaced_by_driver_candidate(self):
        with self.storage([self.row()]) as (connection, table):
            created = self.recover(
                connection, table, primary=86, payload={'mango_id': self.primary_value, 'title': self.row()['title']},
            )
        self.assertEqual(created['mango_id'], self.primary_value)

    def test_ordinary_generated_primary_and_unique_constraint_recovery(self):
        engine = create_engine('sqlite://')
        table = Table('factory_record', MetaData(),
                      Column('id', Integer, primary_key=True), Column('title', String(64), unique=True))
        table.metadata.create_all(engine)
        try:
            with engine.begin() as connection:
                result = connection.execute(insert(table).values(title='AUTO_UNIQUE'))
                created = {'title': 'AUTO_UNIQUE'}
                DataFactoryRunner.merge_generated_values(
                    connection, table, result, created, {'title'}, '', select,
                )
                self.assertEqual(created['id'], 1)
                created = {'title': 'AUTO_UNIQUE'}
                DataFactoryRunner.merge_generated_values(
                    connection, table, SimpleNamespace(inserted_primary_key=(None,), lastrowid=0),
                    created, {'title'}, 'title', select,
                )
                self.assertEqual(created['id'], 1)
        finally:
            engine.dispose()

    def test_null_inserted_values_can_be_verified(self):
        with self.storage([self.row(title=None)]) as (connection, table):
            created = self.recover(connection, table, payload={'title': None, 'org_id': 7})
        self.assertEqual(created['mango_id'], self.primary_value)

    def test_json_values_and_json_null_can_be_verified(self):
        for value in ({'locked': True}, None):
            with self.subTest(value=value), self.storage([self.row(extra=value)]) as (connection, table):
                created = self.recover(connection, table, payload={'extra': value, 'title': self.row()['title']})
            self.assertEqual(created['mango_id'], self.primary_value)

    def test_mysql_timestamp_comparison_uses_the_storage_precision(self):
        from sqlalchemy.dialects.mysql import TIMESTAMP

        table = Table('factory_record', MetaData(),
                      Column('id', BigInteger, primary_key=True), Column('row_id', BigInteger),
                      Column('created_at', TIMESTAMP(fsp=0)))
        connection = MagicMock()
        connection.dialect = mysql_dialect()
        connection.execute.return_value.mappings.return_value.all.return_value = [{
            'id': self.primary_value, 'created_at': datetime(2026, 10, 12, 12, 0, 0),
        }]
        connection.execute.return_value.first.return_value = (self.primary_value,)
        created = {'created_at': datetime(2026, 10, 12, 12, 0, 0, 123456)}
        DataFactoryRunner.merge_generated_values(
            connection, table, SimpleNamespace(inserted_primary_key=(self.primary_value,), lastrowid=0),
            created, {'created_at'}, '', select,
            generated_column_kinds={'id': 'auto_random', 'row_id': 'auto_increment'},
        )
        statement = connection.execute.call_args.args[0].compile(dialect=mysql_dialect())
        self.assertIn('CAST(%s AS DATETIME)', str(statement))
        self.assertEqual(created['id'], self.primary_value)

    def test_reliable_insert_identity_accepts_database_normalized_values(self):
        for identity in ('primary', 'lastrowid', 'explicit', 'unique'):
            with self.subTest(identity=identity):
                engine = create_engine('sqlite://')
                table = Table('factory_record', MetaData(),
                              Column('id', Integer, primary_key=True, autoincrement=True),
                              Column('title', String(64), unique=True), Column('amount', Numeric(10, 2)))
                table.metadata.create_all(engine)
                try:
                    with engine.begin() as connection:
                        connection.execute(text(
                            'CREATE TRIGGER round_amount AFTER INSERT ON factory_record BEGIN '
                            'UPDATE factory_record SET amount=ROUND(NEW.amount,2) WHERE id=NEW.id; END'
                        ))
                        payload = {'title': 'AUTO_ROUND', 'amount': Decimal('1.239')}
                        if identity == 'explicit':
                            payload['id'] = 5
                        result = connection.execute(insert(table).values(**payload))
                        primary = result.inserted_primary_key[0]
                        driver_result = SimpleNamespace(
                            inserted_primary_key=(primary if identity == 'primary' else None,),
                            lastrowid=primary if identity == 'lastrowid' else 0,
                        )
                        created = dict(payload)
                        DataFactoryRunner.merge_generated_values(
                            connection, table, driver_result, created, set(payload),
                            'title' if identity == 'unique' else '', select,
                        )
                        self.assertEqual(created['id'], primary)
                        self.assertEqual(created['amount'], Decimal('1.24'))
                        connection.execute(table.delete().where(table.c.id == created['id']))
                        self.assertEqual(connection.execute(select(table)).all(), [])
                finally:
                    engine.dispose()

    def test_reliable_unique_key_precedes_ambiguous_driver_values(self):
        rows = [self.row(), self.row(mango_id=86, mango_row_id=12, org_id=8)]
        with self.storage(rows, unique_org=True) as (connection, table):
            created = self.recover(connection, table, primary=86, unique_key='org_id')
            self.assertEqual(created['mango_id'], self.primary_value)

    @patch('src.apps.data_factory.services.runner_parts.persistence.DataFactoryDatasource.get_worker_engine')
    def test_normalized_insert_passes_before_commit_and_commits_recovered_primary(self, get_engine):
        engine = create_engine('sqlite://')
        table = Table('factory_record', MetaData(),
                      Column('id', Integer, primary_key=True), Column('amount', Numeric(10, 2)))
        table.metadata.create_all(engine)
        get_engine.return_value = (engine, True)
        entity = SimpleNamespace(table_name='factory_record', primary_key='id', unique_key='')
        before_commit = MagicMock()

        try:
            with engine.begin() as connection:
                connection.execute(text(
                    'CREATE TRIGGER round_amount AFTER INSERT ON factory_record BEGIN '
                    'UPDATE factory_record SET amount=ROUND(NEW.amount,2) WHERE id=NEW.id; END'
                ))
            result = DataFactoryRunner.insert(
                entity, SimpleNamespace(schema_name=''), {'amount': Decimal('1.239')}, before_commit,
            )
            before_commit.assert_called_once()
            self.assertEqual(before_commit.call_args.args[0]['created']['id'], result['created']['id'])
            self.assertEqual(result['created']['amount'], Decimal('1.24'))
            with engine.connect() as connection:
                row = connection.execute(select(table)).mappings().one()
                self.assertEqual(row['id'], result['created']['id'])
                self.assertEqual(row['amount'], Decimal('1.24'))
        finally:
            engine.dispose()

    def test_postgresql_json_with_reliable_primary_does_not_require_payload_comparison(self):
        table = Table('factory_record', MetaData(),
                      Column('id', Integer, primary_key=True), Column('extra', PostgreSQLJSON))
        connection = MagicMock()
        connection.dialect = postgresql_dialect()
        connection.execute.return_value.mappings.return_value.all.return_value = [{'id': 1, 'extra': {'locked': True}}]
        created = {'extra': {'locked': True}}
        DataFactoryRunner.merge_generated_values(
            connection, table, SimpleNamespace(inserted_primary_key=(1,), lastrowid=None),
            created, {'extra'}, '', select,
        )
        self.assertEqual(created['id'], 1)
        connection.execute.assert_called_once()
        statement = str(connection.execute.call_args.args[0].compile(dialect=connection.dialect))
        self.assertNotIn('extra =', statement)

    def test_postgresql_returned_primary_remains_reliable_with_two_sequence_columns(self):
        table = Table('factory_record', MetaData(),
                      Column('id', Integer, primary_key=True, autoincrement=True),
                      Column('row_id', Integer, autoincrement=True), Column('amount', Numeric(10, 2)))
        connection = MagicMock()
        connection.dialect = postgresql_dialect()
        connection.execute.return_value.mappings.return_value.all.return_value = [{
            'id': 1, 'row_id': 2, 'amount': Decimal('1.24'),
        }]
        created = {'amount': Decimal('1.239')}
        DataFactoryRunner.merge_generated_values(
            connection, table, SimpleNamespace(inserted_primary_key=(1,), lastrowid=None),
            created, {'amount'}, '', select,
        )
        self.assertEqual(created, {'id': 1, 'row_id': 2, 'amount': Decimal('1.24')})
        connection.execute.assert_called_once()

    def test_postgresql_json_ownership_comparison_uses_jsonb_and_preserves_null_semantics(self):
        for json_type in (PostgreSQLJSON(), JSONB()):
            for value, sql_null in (({'locked': True}, False), (None, False), (None, True)):
                with self.subTest(json_type=type(json_type).__name__, value=value, sql_null=sql_null):
                    column_type = type(json_type)(none_as_null=sql_null)
                    table = Table('factory_record', MetaData(),
                                  Column('id', BigInteger, primary_key=True), Column('row_id', BigInteger),
                                  Column('extra', column_type))
                    connection = MagicMock()
                    connection.dialect = postgresql_dialect()
                    connection.execute.return_value.mappings.return_value.all.return_value = [{'id': 1, 'extra': value}]
                    connection.execute.return_value.first.return_value = (1,)
                    created = {'extra': value}
                    DataFactoryRunner.merge_generated_values(
                        connection, table, SimpleNamespace(inserted_primary_key=(1,), lastrowid=None),
                        created, {'extra'}, '', select,
                        generated_column_kinds={'id': 'auto_random', 'row_id': 'auto_increment'},
                    )
                    self.assertEqual(created['id'], 1)
                    statement = connection.execute.call_args.args[0].compile(dialect=connection.dialect)
                    sql = str(statement)
                    if sql_null:
                        self.assertIn('IS NULL', sql)
                    else:
                        self.assertIn('JSONB', sql)
                        self.assertNotIn('IS NULL', sql)
                        self.assertIn(value, statement.params.values())
                    if not isinstance(column_type, JSONB):
                        self.assertIn('CAST(factory_record.extra AS JSONB)', sql)

    def test_cleanup_uses_recovered_primary_and_preserves_other_execution_records(self):
        rows = [self.row(), self.row(mango_id=90, mango_row_id=12, title='OTHER_EXECUTION')]
        with self.storage(rows) as (connection, table):
            created = self.recover(connection, table, primary=86)
            item = SimpleNamespace(
                id=1, database=SimpleNamespace(), primary_value=str(created['mango_id']),
                data=DataFactoryTypeCast.to_jsonable(created), template_id=1,
                template=SimpleNamespace(entity=SimpleNamespace(table_name=table.name, primary_key='mango_id')),
                insert_sql_params={DATA_FACTORY_INSERT_SNAPSHOT_KEY: {
                    'table_name': table.name, 'primary_key': 'mango_id', 'schema_name': '',
                }},
            )
            DataFactoryCleanup.delete_by_primary_key(
                item, engine=connection, connection=connection, metadata=table.metadata,
            )
            self.assertEqual(connection.execute(select(table.c.mango_id)).scalars().all(), [90])

    @patch('src.apps.data_factory.services.runner_parts.persistence.DataFactoryDatasource.get_worker_engine')
    def test_unrecoverable_key_rolls_back_insert_before_commit(self, get_engine):
        engine = create_engine('sqlite://')
        table = Table('factory_record', MetaData(),
                      Column('id', Integer, primary_key=True), Column('title', String(64)))
        table.metadata.create_all(engine)
        get_engine.return_value = (engine, True)
        entity = SimpleNamespace(table_name='factory_record', primary_key='id', unique_key='')

        def before_commit(result):
            if result['created'].get('id') is None:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_EXECUTION_PRIMARY_KEY_REQUIRED,
                                       value=('factory_record', 'id'))

        try:
            with patch.object(DataFactoryRunner, 'merge_generated_values', return_value=None):
                with self.assertRaises(DataFactoryError):
                    DataFactoryRunner.insert(entity, SimpleNamespace(schema_name=''), {'title': 'AUTO_ROLLBACK'},
                                             before_commit)
            with engine.connect() as connection:
                self.assertEqual(connection.execute(select(table)).all(), [])
        finally:
            engine.dispose()
