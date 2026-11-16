from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.cleanup_resource import CleanupResourceState, EsCleanupRule, EsCleanupSnapshot
from src.apps.data_factory.services.cleanup.cleanup_lineage import CleanupLineageService as Lineage
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.execution.execution_snapshot import DATA_FACTORY_INSERT_SNAPSHOT_KEY


class CleanupLineageTests(SimpleTestCase):
    def setUp(self):
        self.rule = EsCleanupRule(datasource_alias_id=8, index_template='example', tenant_field='tenant_id',
            tenant_path='baseInfo.tenantId', mode='delete_and_verify', tenant_lineage={
                'entity_id': 52, 'parent_field': 'parent_id', 'tenant_field': 'tenant_id',
                'id_field': 'id', 'collection_path': 'rounds', 'document_id_path': 'roundId'})
        self.snapshot = EsCleanupSnapshot(rule=self.rule, binding_id=9, connection_id=10,
            connection_version='AUTO_VERSION', environment=0, index='example', document_id='1001',
            row_primary_value='41', document_id_field='id', tenant='7', baseline_absent=True)
        self.source = {'version': 2, 'entity_id': 1, 'database_id': 49, 'database_name': 'example',
            'schema_name': '', 'environment': 0, 'datasource_binding_id': 3,
            'connection_version': 'AUTO_SQL_VERSION', 'primary_key': '_id'}
        self.root = SimpleNamespace(id=11, execution_id=5, database_id=49, datasource_binding_id=3,
            primary_value='41', data={'_id': 41, 'id': 1001, 'tenant_id': 7},
            insert_sql_params={DATA_FACTORY_INSERT_SNAPSHOT_KEY: self.source})
        self.child = SimpleNamespace(id=12, database_id=49, datasource_binding_id=3, primary_value='42',
            data={'_id': 42, 'id': 2001, 'parent_id': 1001, 'tenant_id': 7},
            insert_sql_params={DATA_FACTORY_INSERT_SNAPSHOT_KEY: {**self.source, 'entity_id': 52}})

    def rows(self):
        with patch('src.apps.data_factory.services.cleanup.cleanup_lineage.DataFactoryExecutionItem.objects') as objects:
            objects.filter.return_value.order_by.return_value = [self.root, self.child]
            rows = Lineage.rows(self.root, self.snapshot)
            objects.filter.assert_called_once_with(execution_id=5)
            return rows

    def document(self, ids=(2001,)):
        return {'_id': '1001', '_index': 'example', '_seq_no': 6, '_primary_term': 2,
                '_source': {'rounds': [{'roundId': value} for value in ids]}}

    def test_partial_document_requires_exact_frozen_sql_child_lineage(self):
        self.snapshot.lineage_rows = self.rows()
        Resources.check_owner(self.document(), self.snapshot)
        for ids in ((), (9999,), (2001, 9999), (2001, 2001)):
            with self.subTest(ids=ids), self.assertRaises(DataFactoryError):
                Resources.check_owner(self.document(ids), self.snapshot)

    def test_missing_tenant_does_not_adopt_legacy_or_missing_proof(self):
        with self.assertRaises(DataFactoryError):
            Resources.check_owner(self.document(), self.snapshot)
        self.snapshot.lineage_rows = self.rows()
        self.snapshot.rule = self.rule.model_copy(update={'tenant_lineage': None})
        with self.assertRaises(DataFactoryError):
            Resources.check_owner(self.document(), self.snapshot)

    def test_foreign_or_null_explicit_tenant_never_falls_back(self):
        self.snapshot.lineage_rows = self.rows()
        for tenant in ('8', None):
            doc = self.document()
            doc['_source']['baseInfo'] = {'tenantId': tenant}
            with self.subTest(tenant=tenant), self.assertRaises(DataFactoryError):
                Resources.check_owner(doc, self.snapshot)
        for value in (None, [], 'AUTO_INVALID'):
            doc = self.document()
            doc['_source']['baseInfo'] = value
            with self.subTest(base_info=value), self.assertRaises(DataFactoryError):
                Resources.check_owner(doc, self.snapshot)

    def test_other_database_binding_environment_tenant_parent_and_corrupt_pk_are_rejected(self):
        changes = [('database_id', 50), ('datasource_binding_id', 4), ('tenant_id', 8),
                   ('_id', 999)]
        for key, value in changes:
            with self.subTest(key=key):
                container = self.child.__dict__ if key in ('database_id', 'datasource_binding_id') else self.child.data
                old = container[key]
                container[key] = value
                with self.assertRaises(DataFactoryError):
                    self.rows()
                container[key] = old
        source = self.child.insert_sql_params[DATA_FACTORY_INSERT_SNAPSHOT_KEY]
        source['environment'] = 1
        with self.assertRaises(DataFactoryError):
            self.rows()

    def test_other_parent_or_uncreated_child_cannot_prove_partial_document_ownership(self):
        self.child.data['parent_id'] = 1002
        self.assertEqual(self.rows(), [])
        with self.assertRaises(DataFactoryError):
            Resources.check_owner(self.document(), self.snapshot)
        # 子节点创建前失败时，不妨碍继续使用原有根租户证明清理，不强求不存在的子行。
        document = self.document()
        document['_source']['baseInfo'] = {'tenantId': '7'}
        Resources.check_owner(document, self.snapshot)

    def test_changed_document_id_and_unproven_baseline_reject(self):
        self.snapshot.lineage_rows = self.rows()
        doc = self.document()
        doc['_id'] = '1002'
        with self.assertRaises(DataFactoryError):
            Resources.check_owner(doc, self.snapshot)
        self.snapshot.baseline_absent = False
        with self.assertRaises(DataFactoryError):
            Resources.check_owner(self.document(), self.snapshot)

    def test_validated_lineage_is_persisted_and_later_child_identity_changes_are_rejected(self):
        self.root.execution = SimpleNamespace(project_product_id=4)
        self.root.template = SimpleNamespace(cleanup_resources=[])
        self.root.cleanup_resources = CleanupResourceState(snapshots=[self.snapshot]).model_dump(mode='json')
        binding = SimpleNamespace(id=9, database_id=10,
            database=SimpleNamespace(update_time=SimpleNamespace(isoformat=lambda: 'AUTO_VERSION')))
        with patch.object(Resources, 'resolve_binding', return_value=binding), \
                patch('src.apps.data_factory.services.cleanup.cleanup_lineage.DataFactoryExecutionItem.objects') as objects, \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.CleanupPersistenceService.save') as save:
            objects.filter.return_value.order_by.return_value = [self.root, self.child]
            state = Resources.validate_snapshot(self.root)
            self.assertEqual(state.snapshots[0].lineage_rows[0].document_id, '2001')
            save.assert_called_once()
            self.child.data['id'] = 2002
            with self.assertRaises(DataFactoryError):
                Resources.validate_snapshot(self.root)
            self.assertEqual(save.call_count, 1)

    def test_partial_document_delete_keeps_original_version_and_requires_later_absence_verification(self):
        self.snapshot.lineage_rows = self.rows()
        document = self.document()
        with patch.object(Resources, 'document', side_effect=[document, {'result': 'deleted'}]) as request:
            self.assertFalse(Resources.sample(self.snapshot, SimpleNamespace(), allow_delete=True))
            self.assertEqual(request.call_args.kwargs['expected'], document)
            self.assertTrue(request.call_args.kwargs['delete'])
            self.assertIn('rounds.roundId', request.call_args_list[0].kwargs['tenant_path'])
        # 删除响应并非零残留；异步写回混入非本轮ID后，仍然拒绝继续删除。
        with patch.object(Resources, 'document', return_value=self.document((2001, 9999))):
            with self.assertRaises(DataFactoryError):
                Resources.sample(self.snapshot, SimpleNamespace(), allow_delete=True)

    def test_historical_rule_has_no_implicit_lineage_upgrade(self):
        legacy = self.snapshot.model_copy(deep=True)
        legacy.rule.tenant_lineage = None
        with patch.object(Resources, 'document', return_value=self.document()) as request:
            with self.assertRaises(DataFactoryError):
                Resources.sample(legacy, SimpleNamespace(), allow_delete=True)
            self.assertEqual(request.call_count, 1)

    def test_configuration_checks_same_product_datasource_and_required_child_fields(self):
        entity = SimpleNamespace(id=1, datasource_alias_id=6)
        with patch('src.apps.data_factory.services.cleanup.cleanup_resource.DataFactoryField.objects') as fields, \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.DataFactoryEntity.objects') as entities, \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.DataFactoryDatasourceAlias.objects') as aliases:
            fields.filter.return_value.values_list.side_effect = [
                ['id', 'tenant_id'], ['id', 'parent_id', 'tenant_id']]
            entities.filter.return_value.first.return_value = SimpleNamespace(id=52)
            aliases.filter.return_value.exists.return_value = True
            Resources.normalize([self.rule.model_dump(mode='json')], entity=entity, project_product_id=4)
            entities.filter.assert_called_once_with(id=52, project_product_id=4, datasource_alias_id=6)
            fields.filter.return_value.values_list.side_effect = None
            fields.filter.return_value.values_list.return_value = ['id', 'tenant_id']
            with self.assertRaises(DataFactoryError):
                Resources.normalize([self.rule.model_dump(mode='json')], entity=entity, project_product_id=4)

    def test_mcp_rule_schema_exposes_reference_fields_and_rejects_credential_or_wildcard_paths(self):
        schema = EsCleanupRule.model_json_schema()
        self.assertIn('tenant_lineage', schema['properties'])
        self.assertIn('collection_path', schema['$defs']['EsCleanupLineageRule']['properties'])
        for key, value in (('collection_path', '*'), ('id_field', 'password'),
                           ('document_id_path', 'nested.auth_token')):
            raw = self.rule.model_dump(mode='json')
            raw['tenant_lineage'][key] = value
            with self.subTest(key=key), self.assertRaises(DataFactoryError):
                Resources.normalize([raw])
