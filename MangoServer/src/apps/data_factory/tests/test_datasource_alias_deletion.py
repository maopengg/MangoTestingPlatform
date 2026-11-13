from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import models
from django.db.models.deletion import Collector, ProtectedError
from django.test import SimpleTestCase

from src.apps.data_factory.models import (
    DataFactoryDatasourceAlias, DataFactoryDatasourceBinding, DataFactoryEntity, DataFactoryExecutionItem, SqlExecutionRecord,
)
from src.apps.system.api.serializers.sql_execution import SqlExecutionRecordSerializer


class DatasourceAliasDeletionTests(SimpleTestCase):
    def test_audit_is_optional_but_business_entity_still_protects_alias(self):
        field = SqlExecutionRecord._meta.get_field('datasource_alias')
        self.assertIs(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        database_field = SqlExecutionRecord._meta.get_field('database')
        self.assertIs(database_field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(database_field.null)
        self.assertIs(DataFactoryExecutionItem._meta.get_field('database').remote_field.on_delete, models.PROTECT)
        self.assertIs(DataFactoryEntity._meta.get_field('datasource_alias').remote_field.on_delete, models.PROTECT)
        self.assertIs(DataFactoryDatasourceBinding._meta.get_field('datasource_alias').remote_field.on_delete,
                      models.CASCADE)

    def collect(self, *, blocked=False):
        alias = DataFactoryDatasourceAlias(id=1, project_product_id=2, name='示例数据源')
        audit = SqlExecutionRecord(id=11, datasource_alias=alias, project_product_id=2, sql_text='SELECT 1')
        entity = DataFactoryEntity(id=21, datasource_alias=alias, project_product_id=2)

        class Rows(list):
            def __init__(self, model, values):
                super().__init__(values)
                self.model = model
                self.query = SimpleNamespace(select_related=True)
                self.delete = MagicMock()
                self._raw_delete = MagicMock()

        def related(model, fields, batch):
            values = [audit] if model is SqlExecutionRecord else [entity] if blocked and model is DataFactoryEntity else []
            return Rows(model, values)

        collector = Collector(using='default')
        with patch.object(collector, 'can_fast_delete', return_value=False), \
                patch.object(collector, 'get_del_batches', side_effect=lambda objs, fields: [objs]), \
                patch.object(collector, 'related_objects', side_effect=related):
            if blocked:
                with self.assertRaises(ProtectedError):
                    collector.collect([alias])
            else:
                collector.collect([alias])
        return collector, audit

    def test_deletion_schedules_null_reference_without_deleting_audit(self):
        collector, audit = self.collect()
        field = SqlExecutionRecord._meta.get_field('datasource_alias')
        batches = collector.field_updates[(field, None)]
        self.assertIn(audit, [row for batch in batches for row in batch])
        self.assertNotIn(SqlExecutionRecord, collector.data)
        self.assertEqual(audit.project_product_id, 2)
        self.assertEqual(audit.sql_text, 'SELECT 1')

    def test_business_entity_blocks_deletion_without_destroying_audit(self):
        collector, audit = self.collect(blocked=True)
        self.assertNotIn(SqlExecutionRecord, collector.data)
        self.assertEqual(audit.datasource_alias_id, 1)

    def test_audit_remains_serializable_after_alias_deletion(self):
        record = SqlExecutionRecord(
            id=1, datasource_alias=None, project_product=None, database=None, source_detail={},
            sql_text='SELECT 1', request_id='example-audit', datasource_type=0,
        )
        result = SqlExecutionRecordSerializer(record).data
        self.assertIsNone(result['datasource_alias'])
        self.assertEqual(result['sql_text'], 'SELECT 1')
