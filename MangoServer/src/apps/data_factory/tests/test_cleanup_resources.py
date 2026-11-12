import io
import json
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.enums.cleanup_resource import EsCleanupModeEnum
from src.apps.data_factory.enums.cleanup import DataFactoryCleanupStatusEnum
from src.apps.data_factory.exceptions import (
    DataFactoryError, DATA_FACTORY_ES_CLEANUP_TIMEOUT, DATA_SOURCE_ELASTICSEARCH_REQUEST_TIMEOUT,
    DATASOURCE_AUDIT_COMPLETION_FAILED,
)
from src.apps.data_factory.schemas.cleanup_resource import CleanupResourceState, EsCleanupRule, EsCleanupSnapshot
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit, SqlExecutionAuditHandle
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


def owned_document(tenant='7'):
    return {'_id': '1001', '_index': 'example_template_7', '_source': {'tenant_id': tenant},
            '_seq_no': 0, '_primary_term': 1, 'found': True}


class CleanupResourceTests(SimpleTestCase):
    def setUp(self):
        persistence = patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionAuditService.confirm_resource_requests')
        persistence.start()
        self.addCleanup(persistence.stop)
        resolver = patch.object(Resources, 'resolve_index', side_effect=lambda target, name: (name, 'AUTO_INDEX_UUID'))
        resolver.start()
        self.addCleanup(resolver.stop)
        self.rule = EsCleanupRule(datasource_alias_id=8, index_template='example_template_{tenant}',
                                  mode='delete_and_verify', timeout_seconds=3)
        self.version = timezone.now().isoformat()
        self.snapshot = EsCleanupSnapshot(rule=self.rule, binding_id=9, connection_id=10,
                                          connection_version=self.version, environment=0,
                                          index='example_template_7', document_id='1001', tenant='7', baseline_absent=True)
        self.binding = SimpleNamespace(id=9, database_id=10, database=SimpleNamespace(
            db_type=20, update_time=timezone.datetime.fromisoformat(self.version)))
        self.entity = SimpleNamespace(id=2, primary_key='id')
        self.template = SimpleNamespace(id=3, entity=self.entity, cleanup_resources=[], project_product_id=4)
        self.execution = SimpleNamespace(id=5, execution_no='DFEXAMPLE', project_product_id=4, source_id=6,
                                         source_type=4, stage=2, cleanup_status=0, save=Mock())
        self.item = SimpleNamespace(id=11, primary_value='1001', execution=self.execution,
                                     data={'id': 1001, 'tenant_id': 7},
                                     database=SimpleNamespace(id=1), insert_sql_params={},
                                     template=self.template, alias='AUTO示例', cleanup_status=0,
                                     cleanup_strategy=1, save=Mock(),
                                     cleanup_resources=CleanupResourceState(snapshots=[self.snapshot], sql_cleaned=True).model_dump(mode='json'))

    def test_invalid_wildcard_arbitrary_query_and_unknown_mode_are_rejected(self):
        for values in ({'index_template': '*'}, {'index_template': 'example/_search'},
                       {'index_template': 'example,other'}, {'index_template': '_all'},
                       {'tenant_field': 'password'}, {'tenant_path': 'auth.access_token'},
                       {'mode': 'delete_all'}, {'query': {'match_all': {}}}):
            rules = {**self.rule.model_dump(mode='json'), **values}
            with self.subTest(values=values), self.assertRaises(DataFactoryError):
                Resources.normalize([rules])

    @patch.object(Resources, 'resolve_binding')
    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve')
    @patch.object(Resources, 'sample', return_value=True)
    def test_checkpoint_keeps_full_window_and_two_separated_terminal_samples(self, sample, target, binding):
        from datetime import datetime, timezone as dt_timezone
        binding.return_value = self.binding
        clock = lambda seconds: patch('src.apps.data_factory.services.cleanup.cleanup_resource.timezone.now',
                                      return_value=datetime.fromtimestamp(1800000000 + seconds, dt_timezone.utc))
        for seconds in (0, 2, 3):
            with clock(seconds):
                self.assertIsNotNone(Resources.advance(self.item, generation=0))
        self.assertFalse(self.item.cleanup_resources['results'])
        with clock(3.1):
            self.assertIsNotNone(Resources.advance(self.item, generation=0))
        self.assertEqual(sample.call_count, 3)
        with clock(4):
            self.assertIsNone(Resources.advance(self.item, generation=0))
        self.assertTrue(self.item.cleanup_resources['results'][0]['success'])

    @patch.object(Resources, 'resolve_binding')
    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve')
    @patch.object(Resources, 'sample', return_value=True)
    def test_recovery_generation_restarts_observation_not_assume_absence(self, sample, target, binding):
        from datetime import datetime, timezone as dt_timezone
        binding.return_value = self.binding
        for seconds, generation in ((0, 0), (20, 1)):
            with patch('src.apps.data_factory.services.cleanup.cleanup_resource.timezone.now',
                       return_value=datetime.fromtimestamp(1800000000 + seconds, dt_timezone.utc)):
                self.assertIsNotNone(Resources.advance(self.item, generation=generation))
        check = self.item.cleanup_resources['checkpoints'][0]
        self.assertEqual(check['started_at'], 1800000020)
        self.assertEqual(check['deadline'], 1800000023)
        self.assertFalse(self.item.cleanup_resources['results'])

    @patch.object(Resources, 'resolve_binding')
    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve')
    @patch.object(Resources, 'sample', return_value=True)
    def test_multiple_resources_interleave_full_windows_instead_of_serial_waits(self, sample, target, binding):
        from datetime import datetime, timezone as dt_timezone
        binding.return_value = self.binding
        other = self.snapshot.model_copy(update={
            'rule': self.rule.model_copy(update={'index_template': 'example_other_{tenant}'}),
            'index': 'example_other_7',
        })
        self.item.cleanup_resources['snapshots'].append(other.model_dump(mode='json'))
        for seconds in (0, 0, 2, 2, 3, 3, 4, 4):
            with patch('src.apps.data_factory.services.cleanup.cleanup_resource.timezone.now',
                       return_value=datetime.fromtimestamp(1800000000 + seconds, dt_timezone.utc)):
                result = Resources.advance(self.item, generation=0)
        self.assertIsNone(result)
        self.assertEqual({entry['snapshot_index'] for entry in self.item.cleanup_resources['results']}, {0, 1})
        self.assertEqual(sample.call_count, 8)

    def test_default_mode_is_verify_not_delete(self):
        value = Resources.normalize([{'datasource_alias_id': 8, 'index_template': 'example'}])
        self.assertEqual(value[0]['mode'], 'verify')
        self.assertIsNone(value[0]['document_id_field'])

    @patch.object(Resources, 'resolve_binding')
    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve')
    @patch.object(Resources, 'document', return_value=None)
    def test_business_id_mapping_is_separate_from_sql_primary_key(self, document, target, binding):
        binding.return_value = self.binding
        self.entity.primary_key = '_id'
        self.template.cleanup_resources = [{**self.rule.model_dump(mode='json'), 'document_id_field': 'id'}]
        created = {'_id': 41, 'id': 1001, 'tenant_id': 7}
        state = Resources.capture(self.template, self.entity, created, SimpleNamespace(environment=0))
        snapshot = state['snapshots'][0]
        self.assertEqual(snapshot['document_id'], '1001')
        self.assertEqual(snapshot['document_id_field'], 'id')
        self.assertEqual(snapshot['row_primary_value'], '41')
        self.assertEqual(document.call_args.args[2], '1001')
        self.item.primary_value = '41'
        self.item.data = created
        self.item.cleanup_resources = state
        Resources.validate_snapshot(self.item)
        self.assertEqual(self.item.primary_value, '41')
        self.item.data['id'] = 1002
        with self.assertRaises(DataFactoryError):
            Resources.validate_snapshot(self.item)

    @patch.object(Resources, 'resolve_binding')
    @patch.object(Resources, 'document')
    def test_explicit_mapping_missing_value_never_falls_back_to_sql_primary(self, document, binding):
        self.entity.primary_key = '_id'
        self.template.cleanup_resources = [{**self.rule.model_dump(mode='json'), 'document_id_field': 'id'}]
        for value in (None, '', 0, False, '../other'):
            with self.subTest(value=value), self.assertRaises(DataFactoryError) as error:
                Resources.capture(self.template, self.entity, {'_id': 41, 'id': value, 'tenant_id': 7},
                                  SimpleNamespace(environment=0))
            self.assertIn('禁止回退主键', error.exception.msg)
        document.assert_not_called()
        binding.assert_not_called()

    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.DataFactoryDatasourceAlias.objects')
    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.DataFactoryField.objects')
    def test_mapping_must_be_an_entity_field(self, fields, aliases):
        fields.filter.return_value.values_list.return_value = ['_id', 'tenant_id']
        with self.assertRaises(DataFactoryError):
            Resources.normalize([{**self.rule.model_dump(mode='json'), 'document_id_field': 'id'}],
                                entity=self.entity, project_product_id=4)
        fields.filter.return_value.values_list.return_value = ['_id', 'id', 'tenant_id']
        aliases.filter.return_value.exists.return_value = True
        rules = Resources.normalize([{**self.rule.model_dump(mode='json'), 'document_id_field': 'id'}],
                                    entity=self.entity, project_product_id=4)
        self.assertEqual(rules[0]['document_id_field'], 'id')

    def test_mapped_snapshot_missing_row_identity_cannot_be_adopted(self):
        self.item.cleanup_resources['snapshots'][0]['rule']['document_id_field'] = 'id'
        with self.assertRaises(DataFactoryError):
            Resources.validate_snapshot(self.item)

    def test_duplicate_rules_are_rejected(self):
        with self.assertRaises(DataFactoryError):
            Resources.normalize([self.rule.model_dump(mode='json')] * 2)

    @patch.object(Resources, 'resolve_binding')
    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve')
    @patch.object(Resources, 'document')
    def test_capture_uses_real_id_and_rejects_existing_document(self, document, target, binding):
        binding.return_value = self.binding
        self.template.cleanup_resources = [self.rule.model_dump(mode='json')]
        document.return_value = None
        state = Resources.capture(self.template, self.entity, {'id': 1001, 'tenant_id': 7}, SimpleNamespace(environment=0))
        self.assertEqual(state['snapshots'][0]['document_id'], '1001')
        self.assertEqual(state['snapshots'][0]['environment'], 0)
        self.assertFalse(state['sql_cleaned'])
        document.return_value = owned_document()
        with self.assertRaises(DataFactoryError) as error:
            Resources.capture(self.template, self.entity, {'id': 1001, 'tenant_id': 7}, SimpleNamespace(environment=0))
        self.assertEqual(error.exception.code, 34179)

    def test_baseline_failure_before_commit_rolls_back_the_insert(self):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select, func
        from src.apps.data_factory.services.execution.runner import DataFactoryRunner
        engine = create_engine('sqlite:///:memory:')
        table = Table('example', MetaData(), Column('id', Integer, primary_key=True), Column('name', String(32)))
        table.metadata.create_all(engine)
        entity = SimpleNamespace(table_name='example', primary_key='id')
        try:
            with patch('src.apps.data_factory.services.execution.parts.persistence.DataFactoryDatasource.get_worker_engine', return_value=(engine, True)):
                def reject(_):
                    raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_TIMEOUT)
                with self.assertRaises(DataFactoryError):
                    DataFactoryRunner.insert(entity, SimpleNamespace(schema_name='', db_type=DataSourceTypeEnum.SQLITE.value), {'name': 'AUTO回滚'}, before_commit=reject)
            with engine.connect() as connection:
                self.assertEqual(connection.execute(select(func.count()).select_from(table)).scalar_one(), 0)
        finally:
            engine.dispose()

    @patch.object(Resources, 'resolve_binding')
    def test_connection_rotation_and_primary_value_tampering_are_blocked(self, resolve):
        resolve.return_value = self.binding
        self.item.primary_value = '2002'
        with self.assertRaises(DataFactoryError):
            Resources.validate_snapshot(self.item)
        self.item.primary_value = '1001'
        self.binding.database_id = 12
        with self.assertRaises(DataFactoryError) as error:
            Resources.validate_snapshot(self.item)
        self.assertEqual(error.exception.code, 34181)

    def test_historical_data_cannot_be_adopted_by_new_template_rule(self):
        self.item.cleanup_resources = {}
        self.template.cleanup_resources = [self.rule.model_dump(mode='json')]
        with self.assertRaises(DataFactoryError) as error:
            Resources.validate_snapshot(self.item)
        self.assertIn('历史执行缺少', error.exception.msg)

    def test_other_tenant_cannot_be_deleted(self):
        with self.assertRaises(DataFactoryError):
            Resources.check_owner(owned_document('8'), self.snapshot)

    def test_recorded_tenant_drift_is_not_silently_ignored(self):
        self.item.data['tenant_id'] = 8
        with self.assertRaises(DataFactoryError):
            Resources.validate_snapshot(self.item)

    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.DataFactoryDatasourceResolver')
    def test_production_delete_is_forbidden_and_both_permissions_are_required(self, resolver):
        resolver.resolve_binding_by_env.return_value = self.binding
        from src.apps.test_center.enums.environment import EnvironmentEnum
        with self.assertRaises(DataFactoryError):
            Resources.resolve_binding(self.rule, 4, EnvironmentEnum.PRO.value)
        resolver.require_binding_permission.assert_not_called()
        Resources.resolve_binding(self.rule, 4, 0)
        self.assertEqual([call.kwargs['write'] for call in resolver.require_binding_permission.call_args_list], [False, True])

    def run_checks(self, responses, *, expect_failure=False, clock=None):
        clock = clock if clock is not None else [0]
        with patch.object(Resources, 'resolve_binding', return_value=self.binding), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve'), \
                patch.object(Resources, 'document', side_effect=responses) as document, \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.sleep', side_effect=lambda duration: clock.__setitem__(0, clock[0] + duration)), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.monotonic', side_effect=lambda: clock[0]):
            if expect_failure:
                with self.assertRaises(DataFactoryError):
                    Resources.verify(self.item)
            else:
                Resources.verify(self.item)
            return document.call_args_list

    def test_delete_uses_owned_version_then_requires_two_absent_reads(self):
        calls = self.run_checks([owned_document(), {'result': 'deleted'}] + [None] * 6)
        self.assertEqual(len(calls), 8)
        self.assertTrue(calls[1].kwargs['delete'])
        self.assertEqual(calls[1].kwargs['expected']['_seq_no'], 0)
        result = self.item.cleanup_resources['results'][0]
        self.assertTrue(result['success'])
        self.assertEqual(result['attempts'], 4)

    def test_late_indexed_document_is_not_missed_by_initial_absent_reads(self):
        calls = self.run_checks([None, None, None, None, owned_document(), {'result': 'deleted'}, None, None], expect_failure=True)
        # 窗口尾部只有一次消失不能证明稳定；第二轮重试继续验证。
        self.assertEqual(sum(bool(call.kwargs.get('delete')) for call in calls), 1)

    def test_wrong_tenant_fails_without_sending_delete(self):
        calls = self.run_checks([owned_document('8')], expect_failure=True)
        self.assertEqual(len(calls), 1)
        self.assertFalse(self.item.cleanup_resources['results'][0]['success'])

    def test_delete_timeout_is_reconciled_without_blind_delete_replay(self):
        clock = [0]
        calls_seen = []

        def document(*args, **kwargs):
            calls_seen.append(kwargs)
            if kwargs.get('delete'):
                clock[0] += 1
                error = DataFactoryError(DATA_SOURCE_ELASTICSEARCH_REQUEST_TIMEOUT)
                error.__cause__ = URLError(TimeoutError('read timed out'))
                raise error
            return owned_document() if len(calls_seen) == 1 else None

        calls = self.run_checks(document, clock=clock)
        self.assertEqual(sum(bool(call.kwargs.get('delete')) for call in calls), 1)
        self.assertTrue(self.item.cleanup_resources['results'][0]['success'])
        self.assertGreaterEqual(clock[0], self.rule.timeout_seconds)
        self.assertTrue(all(call.kwargs['timeout'] == 5 for call in calls))
        self.assertTrue(any(call.kwargs.get('realtime') is False for call in calls))

    def test_verified_timeout_resolves_only_its_request_and_keeps_original_audit(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        record = SimpleNamespace(request_id='AUTO_DELETE', database_id=10, source_detail={}, slow_threshold_ms=20000)
        handle = SqlExecutionAuditHandle(record, 0)
        timeout = DataFactoryError(DATA_SOURCE_ELASTICSEARCH_REQUEST_TIMEOUT)
        timeout.__cause__ = TimeoutError()
        with Infrastructure.scope(), patch.object(Audit, 'save_completion'), patch.object(Audit, 'notify_slow'):
            Audit.finish_failure(handle, timeout, 5001)
            unrelated = TimeoutError()
            unrelated._datasource_audit_request_id = 'AUTO_OTHER'
            Infrastructure.capture(unrelated, result_unknown=True)
            Infrastructure.capture(DataFactoryError(DATASOURCE_AUDIT_COMPLETION_FAILED))
            self.assertEqual(len(Infrastructure.current()), 3)
            self.run_checks([owned_document(), timeout] + [None] * 6)
            self.assertEqual({issue.request_id for issue in Infrastructure.current()}, {'AUTO_OTHER', None})
            self.assertEqual(record.status, 'timeout')
            self.assertIn('34183', record.error_message)
            self.assertEqual(self.item.cleanup_resources['uncertain_requests'][0]['request_id'], 'AUTO_DELETE')

    def test_failed_verification_and_pending_permit_cannot_resolve_timeout(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        from src.apps.data_factory.schemas.cleanup_resource import EsUncertainRequest, EsCleanupCheckResult, EsUnknownPermit
        state = Resources.state(self.item)
        state.uncertain_requests.append(EsUncertainRequest(
            request_id='AUTO_DELETE', index=self.snapshot.index, document_id=self.snapshot.document_id))
        with Infrastructure.scope():
            timeout = TimeoutError()
            timeout._datasource_audit_request_id = 'AUTO_DELETE'
            Infrastructure.capture(timeout, result_unknown=True)
            Resources.resolve_verified(state)
            self.assertEqual(len(Infrastructure.current()), 1)
            state.results.append(EsCleanupCheckResult(index=self.snapshot.index, document_id='1001',
                success=True, checked_at=timezone.now().isoformat(), attempts=4))
            state.unknown_permits.append(EsUnknownPermit(group='a' * 32, owner='b' * 32,
                index=self.snapshot.index, document_id='1001'))
            Resources.resolve_verified(state)
            self.assertEqual(len(Infrastructure.current()), 1)
            state.unknown_permits.clear()
            Resources.resolve_verified(state)
            self.assertFalse(Infrastructure.current())

    def test_alias_retarget_or_recreated_index_blocks_before_document_read(self):
        self.snapshot.requested_index = self.snapshot.index
        self.snapshot.index_uuid = 'AUTO_ORIGINAL'
        with patch.object(Resources, 'resolve_index', return_value=(self.snapshot.index, 'AUTO_RECREATED')), \
                patch.object(Resources, 'document') as document:
            with self.assertRaises(DataFactoryError) as raised:
                Resources.sample(self.snapshot, Mock(), allow_delete=True)
        self.assertEqual(raised.exception.code, 34181)
        document.assert_not_called()

    @patch.object(Resources, 'resolve_binding')
    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve')
    @patch.object(Resources, 'document', return_value=None)
    def test_capture_freezes_alias_target_and_keeps_original_rule(self, document, target, binding):
        binding.return_value = self.binding
        self.template.cleanup_resources = [self.rule.model_dump(mode='json')]
        with patch.object(Resources, 'resolve_index', return_value=('example_template_7_new', 'AUTO_UUID')):
            raw = Resources.capture(self.template, self.entity, self.item.data, SimpleNamespace(environment=0))
        self.item.cleanup_resources = raw
        state = Resources.validate_snapshot(self.item)
        self.assertEqual(state.snapshots[0].index, 'example_template_7_new')
        self.assertEqual(state.snapshots[0].requested_index, 'example_template_7')
        self.assertEqual(state.snapshots[0].index_uuid, 'AUTO_UUID')
        self.assertEqual(document.call_args.args[1], 'example_template_7_new')
        self.assertEqual(state.snapshots[0].rule.index_template, self.rule.index_template)

    def test_http_timeout_keeps_failed_write_audit_and_verifies_both_read_views(self):
        clock = [0]
        requests = []
        target = SimpleNamespace(id=10, db_type=20, extra_config={}, host='es.example.com', port=9200,
                                 user='', password='')

        def open_request(request, **kwargs):
            requests.append(request)
            if request.method == 'DELETE':
                raise URLError(TimeoutError())
            if len(requests) == 1:
                response = Mock()
                response.__enter__ = Mock(return_value=response)
                response.__exit__ = Mock(return_value=False)
                response.read.return_value = json.dumps(owned_document()).encode()
                return response
            body = json.dumps({'_index': 'example_template_7', '_id': '1001', 'found': False}).encode()
            raise HTTPError(request.full_url, 404, '', {}, io.BytesIO(body))

        with patch.object(Resources, 'resolve_binding', return_value=self.binding), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve', return_value=target), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.open_elasticsearch_request', side_effect=open_request), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.sleep', side_effect=lambda duration: clock.__setitem__(0, clock[0] + duration)), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.monotonic', side_effect=lambda: clock[0]), \
                patch.object(Audit, 'start', side_effect=lambda **kwargs: SqlExecutionAuditHandle(
                    SimpleNamespace(database_id=10, datasource_type=20), 0)), \
                patch.object(Audit, 'finish_success'), \
                patch.object(Audit, 'finish_failure') as failed:
            Resources.verify(self.item)
        failed.assert_called_once()
        self.assertEqual(failed.call_args.args[1].code, 34183)
        self.assertEqual(sum(request.method == 'DELETE' for request in requests), 1)
        self.assertTrue(any('realtime=false' in request.full_url for request in requests))
        self.assertTrue(self.item.cleanup_resources['results'][0]['success'])

    def test_read_failure_after_delete_timeout_stays_failed(self):
        calls = self.run_checks([owned_document(), TimeoutError(), OSError('unreachable')], expect_failure=True)
        self.assertEqual(sum(bool(call.kwargs.get('delete')) for call in calls), 1)
        self.assertFalse(self.item.cleanup_resources['results'][0]['success'])

    def test_delete_permission_or_version_failure_is_not_retried(self):
        for status in (403, 409):
            with self.subTest(status=status):
                calls = self.run_checks([owned_document(), HTTPError('https://es.example.com', status, '', {}, None)],
                                        expect_failure=True)
                self.assertEqual(len(calls), 2)

    def test_audit_completion_timeout_cannot_be_reconciled_as_transport_timeout(self):
        error = DataFactoryError(DATASOURCE_AUDIT_COMPLETION_FAILED)
        error.__cause__ = TimeoutError()
        error.__cause__._datasource_unknown_permit = ('a' * 32, 'b' * 32)
        calls = self.run_checks([owned_document(), error], expect_failure=True)
        self.assertEqual(len(calls), 2)

    def test_real_time_absence_does_not_hide_search_visible_document(self):
        calls = self.run_checks([None, owned_document()] * 4, expect_failure=True)
        self.assertFalse(self.item.cleanup_resources['results'][0]['success'])
        self.assertTrue(all(not call.kwargs.get('delete') for call in calls))

    def test_late_search_visibility_disappears_but_requires_two_paired_reads(self):
        self.run_checks([None, owned_document(), None, owned_document(), None, None, None, None])
        self.assertTrue(self.item.cleanup_resources['results'][0]['success'])

    def test_timeout_does_not_allow_recreated_document_with_other_tenant(self):
        calls = self.run_checks([owned_document(), TimeoutError(), owned_document('8')], expect_failure=True)
        self.assertEqual(sum(bool(call.kwargs.get('delete')) for call in calls), 1)

    def test_recreated_document_requires_fresh_version_before_next_delete(self):
        recreated = {**owned_document(), '_seq_no': 8}
        # 两次删除必须来自不同轮的实时 GET，而非直接重放超时写请求。
        calls = self.run_checks([owned_document(), TimeoutError(), recreated, {'result': 'deleted'},
                                None, None, None, None])
        deletes = [call for call in calls if call.kwargs.get('delete')]
        self.assertEqual([call.kwargs['expected']['_seq_no'] for call in deletes], [0, 8])

    def test_verify_only_times_out_without_delete_and_retains_error(self):
        self.item.cleanup_resources['snapshots'][0]['rule']['mode'] = 'verify'
        clock = iter(range(100))
        with patch.object(Resources, 'resolve_binding', return_value=self.binding), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve'), \
                patch.object(Resources, 'document', return_value=owned_document()) as document, \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.sleep'), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.monotonic', side_effect=lambda: next(clock)):
            with self.assertRaises(DataFactoryError):
                Resources.verify(self.item)
        self.assertTrue(self.item.cleanup_resources['sql_cleaned'])
        self.assertFalse(self.item.cleanup_resources['results'][0]['success'])
        self.assertTrue(all(not call.kwargs.get('delete') for call in document.call_args_list))

    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.open_elasticsearch_request')
    def test_conditional_delete_has_no_free_query_and_no_unconditional_fallback(self, open_request):
        target = SimpleNamespace(extra_config={}, host='es.example.com', port=9200, user='', password='')
        response = open_request.return_value.__enter__.return_value
        response.read.return_value = json.dumps({'_id': '1001', '_index': 'example_template_7', 'result': 'deleted'}).encode()
        Resources.request_document(target, 'example_template_7', '1001', delete=True, timeout=2, expected=owned_document())
        request = open_request.call_args.args[0]
        self.assertEqual(request.method, 'DELETE')
        self.assertIn('if_seq_no=0&if_primary_term=1', request.full_url)
        self.assertIn('refresh=wait_for', request.full_url)
        self.assertNotIn('_delete_by_query', request.full_url)
        with self.assertRaises(DataFactoryError):
            Resources.request_document(target, 'example_template_7', '1001', delete=True, timeout=2, expected={})
        self.assertEqual(open_request.call_count, 1)

    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.open_elasticsearch_request')
    def test_search_visible_check_is_exact_document_get_without_forcing_refresh(self, open_request):
        target = SimpleNamespace(extra_config={}, host='es.example.com', port=9200, user='', password='')
        response = open_request.return_value.__enter__.return_value
        response.read.return_value = json.dumps(owned_document()).encode()
        Resources.request_document(target, 'example_template_7', '1001', delete=False, timeout=5,
                                   tenant_path='tenant_id', realtime=False)
        request = open_request.call_args.args[0]
        self.assertEqual(request.method, 'GET')
        self.assertIn('/example_template_7/_doc/1001?', request.full_url)
        self.assertIn('realtime=false', request.full_url)
        self.assertNotIn('refresh=', request.full_url)

    def test_wrapped_transport_timeout_is_distinct_from_tls_failure(self):
        from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
        target = SimpleNamespace(password='')
        for error in (TimeoutError(), URLError(TimeoutError())):
            with self.subTest(error=type(error).__name__), self.assertRaises(DataFactoryError) as result:
                DataSourceErrorService.raise_elasticsearch_transport_error(target, error)
            self.assertEqual(result.exception.code, 34183)
            self.assertTrue(Audit.is_timeout(result.exception))

    @patch('src.apps.data_factory.services.cleanup.cleanup_resource.open_elasticsearch_request')
    def test_missing_index_is_not_mistaken_for_missing_document(self, open_request):
        target = SimpleNamespace(extra_config={}, host='es.example.com', port=9200, user='', password='')
        open_request.side_effect = HTTPError('https://es.example.com', 404, '', {}, io.BytesIO(b'{"error":{"type":"index_not_found_exception"}}'))
        with self.assertRaises(DataFactoryError):
            Resources.request_document(target, 'example_template_7', '1001', delete=False, timeout=2)
        body = json.dumps({'_index': 'example_template_7', '_id': '1001', 'found': False}).encode()
        open_request.side_effect = HTTPError('https://es.example.com', 404, '', {}, io.BytesIO(body))
        self.assertIsNone(Resources.request_document(target, 'example_template_7', '1001', delete=False, timeout=2))

    @patch.object(Audit, 'start')
    @patch.object(Audit, 'finish_success')
    def test_es_baseline_inside_sql_scope_still_gets_its_own_audit(self, finish, start):
        parent = SqlExecutionAuditHandle(SimpleNamespace(database_id=1, datasource_type=0), 0)
        with Audit.scope(parent):
            Audit.call(SimpleNamespace(id=2, db_type=20), {'operation': 'get_document'}, lambda: {'found': False})
        start.assert_called_once()
        finish.assert_called_once()

    @patch('src.apps.data_factory.services.cleanup.cleanup.DataFactoryExecutionItem.objects')
    @patch('src.apps.data_factory.services.cleanup.cleanup.DataFactoryExecution.objects')
    def test_resource_failure_stays_failed_and_retry_does_not_delete_sql_again(self, executions, items):
        self.item.cleanup_resources['sql_cleaned'] = False
        executions.get.return_value = self.execution
        items.select_related.return_value.filter.return_value.order_by.return_value = [self.item]
        with patch.object(Resources, 'validate_snapshot', side_effect=lambda item: Resources.state(item)), \
                patch.object(DataFactoryCleanup, 'validate_cleanup_item'), \
                patch('src.apps.data_factory.services.cleanup.cleanup.DatasourceTargetService.from_snapshot', return_value=SimpleNamespace(cache_key='target')), \
                patch.object(DataFactoryCleanup, 'cleanup_items_in_database_transaction') as delete_sql, \
                patch.object(Resources, 'verify', side_effect=DataFactoryError(DATA_FACTORY_ES_CLEANUP_TIMEOUT)) as verify, \
                patch('src.apps.data_factory.services.cleanup.cleanup.transaction.on_commit', side_effect=lambda callback: callback()), \
                patch.object(DataFactoryCleanup, 'sync_workbench_todo') as todo:
            first = DataFactoryCleanup.cleanup_execution(5, defer_resources=True)
            self.assertEqual(first['pending'], 1)
            self.assertEqual(first['success'], 0)
            self.assertTrue(self.item.cleanup_resources['sql_cleaned'])
            with self.assertRaises(DataFactoryError):
                DataFactoryCleanup.finish_resource_cleanup(self.item)
            DataFactoryCleanup.mark_failed(self.item, DATA_FACTORY_ES_CLEANUP_TIMEOUT.message)
            self.assertEqual(self.item.cleanup_status, DataFactoryCleanupStatusEnum.FAIL.value)
            verify.side_effect = None
            second = DataFactoryCleanup.cleanup_execution(5, defer_resources=True)
            self.assertEqual(second['fail'], 0)
            self.assertEqual(second['pending'], 1)
            DataFactoryCleanup.finish_resource_cleanup(self.item)
            self.assertEqual(self.item.cleanup_status, 1)
            self.assertEqual(delete_sql.call_count, 1)
            self.assertEqual(todo.call_count, 2)
