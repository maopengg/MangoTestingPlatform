from contextlib import ExitStack, nullcontext
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from pydantic import ValidationError

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.enums.resource_cleanup import ApiResourceCleanupStatus as State
from src.apps.auto_api.schemas.resource_cleanup import (
    ApiResourceCleanupRule, ApiResourceProof, ApiResourceTargetSnapshot, ApiResourceCleanupRules,
)
from src.apps.auto_api.services.resource_cleanup import (
    ApiResourceCleanupService as Service, ApiResourceExecutionManager as Manager,
    ApiResourceCleanupRetryService as Retry,
)
from src.apps.auto_api.services.resource_cleanup_io import ApiResourceCleanupIO as IO
from src.apps.data_factory.services.cleanup_resource import DataFactoryCleanupResourceService as ES
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor


def rule_data(**changes):
    return {'key': 'project', 'trigger_step_key': 'step-10', 'api_info_id': 20,
            'sql_datasource_alias_id': 1, 'es_datasource_alias_id': 2, 'table': 'project',
            'version_field': 'version', 'request_unique_path': 'name',
            'tenant_cache_key': 'tenant', 'creator_cache_key': 'employee',
            'index_template': 'project_{tenant}', 'children': [
                {'table': name, 'foreign_key': 'project_id', 'root_field': 'id', 'tenant_field': 'tenant_id'}
                for name in ('project_member', 'project_field_value', 'project_contract_relation')], **changes}


def proof_data(**changes):
    target = ApiResourceTargetSnapshot(binding_id=11, database_id=21, connection_version='v1',
                                       database_name='test_db', schema_name='')
    return ApiResourceProof(unique_name='AUTO_once', tenant='123', creator='456',
        sql_target=target, es_target=target.model_copy(update={'binding_id': 12, 'database_id': 22}),
        index='project_123', index_uuid='uuid', request_sent=True,
        root={'_id': '7', 'id': '9001', 'group_id': '8001', 'version': '2',
              'tenant_id': '123', 'create_employee_id': '456', 'name': 'AUTO_once'}, **changes)


def document(**changes):
    return {'_index': 'project_123', '_id': '8001', '_seq_no': 5, '_primary_term': 2,
            '_source': {'tenantId': '123', 'projectId': '9001', 'groupId': '8001', 'sourceVersion': '2'}, **changes}


class ApiResourceRuleTests(SimpleTestCase):
    def test_rules_frozen_in_revision_and_empty_rules_preserve_snapshot_shape(self):
        from src.apps.auto_api.models import ApiCase
        from src.apps.auto_api.services.api_case.snapshot import ApiExecutableSnapshotService as Snapshots
        case = ApiCase(id=1, project_product_id=3, module_id=4, case_people_id=5, name='AUTO_fixture')
        with patch.object(Snapshots, 'current_case_config', return_value={}), \
             patch.object(Snapshots, 'resolve_case_headers', return_value=({}, [])), \
             patch('src.apps.auto_api.services.api_case.snapshot.ApiCaseDetailed.objects') as steps, \
             patch('src.apps.auto_api.services.api_case.snapshot.ApiConfigSnapshotService.serialize_data_factory_configs',
                   return_value=[]):
            steps.filter.return_value.select_related.return_value.order_by.return_value = []
            empty = Snapshots.capture_case(case, Mock())
            self.assertNotIn('resource_cleanup', empty['api_case'])
            case.resource_cleanup = [rule_data()]
            frozen = Snapshots.capture_case(case, Mock())
            case.resource_cleanup[0]['document_id_field'] = 'changed'
            self.assertEqual(frozen['api_case']['resource_cleanup'][0].get('document_id_field', 'group_id'), 'group_id')

    def test_three_identifiers_and_children_are_distinct(self):
        rule = ApiResourceCleanupRule.model_validate(rule_data())
        self.assertEqual([rule.primary_key, rule.business_id_field, rule.document_id_field], ['_id', 'id', 'group_id'])
        self.assertEqual(len(rule.children), 3)

    def test_unsafe_rules_rejected(self):
        for change in ({'table': 'project;DELETE'}, {'index_template': 'project_*'},
                       {'creator_cache_key': 'access_token'}, {'observation_seconds': 1},
                       {'document_id_field': 'id'}, {'delete_by_query': True},
                       {'children': [{'table': 'members', 'foreign_key': 'tenant_id',
                                      'root_field': 'tenant_id', 'tenant_field': 'tenant_id'}]}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ApiResourceCleanupRule.model_validate(rule_data(**change))

    def test_duplicate_trigger_and_key_rejected(self):
        with self.assertRaises(ValidationError):
            ApiResourceCleanupRules.model_validate({'rules': [rule_data(), rule_data(key='other')]})

    def test_rejection_requires_explicit_false_contract_and_distinct_source(self):
        for change in ({'rejection_response': {'success': True}}, {'rejection_response': {'success': 0}},
                       {'rejection_response': {'success': 'false'}}, {'name_source_key': 'project'}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ApiResourceCleanupRule.model_validate(rule_data(**change))
        rule = ApiResourceCleanupRule.model_validate(rule_data(rejection_response={'success': False}))
        self.assertIs(rule.rejection_response['success'], False)

    def test_owner_and_external_version_strict(self):
        rule, proof = ApiResourceCleanupRule.model_validate(rule_data()), proof_data()
        IO.check_document(document(), rule, proof)
        for key in ('tenantId', 'projectId', 'groupId', 'sourceVersion'):
            doc = document()
            doc['_source'][key] = 'different'
            with self.subTest(field=key), self.assertRaises(AutoApiError):
                IO.check_document(doc, rule, proof)
        with self.assertRaises(AutoApiError):
            IO.check_document(document(_id='9001'), rule, proof)

    def test_response_and_sql_correspondence(self):
        rule, proof = ApiResourceCleanupRule.model_validate(rule_data()), proof_data()
        proof.response_identity = {'business_id': '9001', 'document_id': '8001', 'version': '2'}
        Service.verify_response(rule, proof, proof.root)
        for key in ('id', 'group_id', 'version', 'create_employee_id', 'tenant_id', 'name'):
            row = {**proof.root, key: 'other'}
            with self.subTest(field=key), self.assertRaises(AutoApiError):
                Service.verify_response(rule, proof, row)

    def test_array_owner_and_version_are_checked_on_same_single_element(self):
        rule = ApiResourceCleanupRule.model_validate(rule_data(
            es_business_id_path='projects[].projectId', es_version_path='projects[].projectVersion'))
        proof = proof_data()
        doc = document(_source={'tenantId': '123', 'groupId': '8001',
            'projects': [{'projectId': '9001', 'projectVersion': '2'}]})
        IO.check_document(doc, rule, proof)
        for elements in ([], [{'projectId': 'other', 'projectVersion': '2'}],
                         [{'projectId': '9001', 'projectVersion': '3'}],
                         [{'projectId': '9001', 'projectVersion': '2'}, {'projectId': 'other', 'projectVersion': '2'}],
                         [{'projectId': '9001'}, {'projectVersion': '2'}], [None]):
            changed = deepcopy(doc)
            changed['_source']['projects'] = elements
            with self.subTest(elements=elements), self.assertRaises(AutoApiError):
                IO.check_document(changed, rule, proof)

    def test_array_paths_cannot_miscombine_or_guess(self):
        for paths in (('projects[].projectId', 'sourceVersion'),
                      ('projects[].projectId', 'others[].projectVersion'),
                      ('projects[0].projectId', 'projects[0].projectVersion'),
                      ('projects[*].projectId', 'projects[*].projectVersion')):
            with self.subTest(paths=paths), self.assertRaises(ValidationError):
                ApiResourceCleanupRule.model_validate(rule_data(
                    es_business_id_path=paths[0], es_version_path=paths[1]))
        # 已冻结的旧规则不自动猜测数组路径。
        with self.assertRaises(AutoApiError):
            IO.check_document(document(_source={'tenantId': '123', 'groupId': '8001', 'sourceVersion': '2',
                'projects': [{'projectId': '9001', 'projectVersion': '2'}]}),
                ApiResourceCleanupRule.model_validate(rule_data()), proof_data())

    def test_es_source_filter_removes_only_array_marker(self):
        rule = ApiResourceCleanupRule.model_validate(rule_data(
            es_business_id_path='projects[].projectId', es_version_path='projects[].projectVersion'))
        with patch.object(ES, 'document') as read:
            IO.document(Mock(), rule, proof_data())
        self.assertEqual(read.call_args.kwargs['tenant_path'],
                         'tenantId,projects.projectId,groupId,projects.projectVersion')

    def test_read_only_user_cannot_amend_cleanup_mapping(self):
        with patch('src.apps.user.services.permission.PermissionMenuService.permission_keys_for_user',
                   return_value={'api.case:read'}), self.assertRaises(AutoApiError):
            Retry.retry(user=SimpleNamespace(id=99), case_id=1, resource_id=5,
                identity_mapping={'es_business_id_path': 'projects[].projectId',
                                  'es_version_path': 'projects[].projectVersion'})

    def test_missing_child_table_blocks_before_request_with_business_error(self):
        from sqlalchemy.exc import ProgrammingError
        error = ProgrammingError('statement', {}, Exception(1146, 'private database detail'))
        connection = Mock()
        connection.execute.side_effect = error
        with self.assertRaises(AutoApiError) as caught:
            IO.validate_children(connection, ApiResourceCleanupRule.model_validate(rule_data()))
        self.assertIn('创建请求尚未发送', caught.exception.msg)
        self.assertNotIn('private database detail', caught.exception.msg)

    def test_binding_environment_is_fail_closed(self):
        for env in (None, 1, 2, 4, 5):
            with self.subTest(env=env), self.assertRaises(AutoApiError):
                IO.binding(1, 3, env, sql=True)


class ApiResourceObservationTests(SimpleTestCase):
    def setUp(self):
        self.rule = ApiResourceCleanupRule.model_validate(rule_data())
        self.proof = proof_data()
        self.record = SimpleNamespace(id=1, cleanup_token='f' * 32)
        self.now = 0
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Service, 'check'))
        self.persist = self.stack.enter_context(patch.object(Service, 'persist'))
        self.resolve = self.stack.enter_context(patch.object(ES, 'resolve_index', return_value=('project_123', 'uuid')))
        self.read = self.stack.enter_context(patch.object(IO, 'document', return_value=None))
        self.delete = self.stack.enter_context(patch.object(ES, 'document'))
        self.release = self.stack.enter_context(patch.object(Governor, 'release'))

    def pause(self, seconds):
        self.now += seconds

    def observe(self, **kwargs):
        Service.observe(self.record, self.rule, self.proof, SimpleNamespace(),
                        clock=lambda: self.now, pause=self.pause, elapsed_wait=lambda: 0, **kwargs)

    def test_absence_covers_full_window_and_two_final_checks(self):
        self.observe()
        self.assertGreaterEqual(self.now, 16)
        self.assertGreaterEqual(self.read.call_count, 34)
        self.delete.assert_not_called()

    def test_timeout_after_applied_delete_rechecks_and_releases_exact_owner(self):
        self.proof.unknown_permits = [{'group': 'a' * 32, 'owner': 'b' * 32}]
        def read(*args, **kwargs):
            return document() if self.now == 0 else None
        self.read.side_effect = read
        error = TimeoutError()
        error._datasource_unknown_permit = ('a' * 32, 'c' * 32)
        self.delete.side_effect = error
        self.observe()
        self.assertEqual(self.delete.call_count, 1)
        self.assertCountEqual([call.args[0] for call in self.release.call_args_list],
                              [('a' * 32, 'b' * 32), ('a' * 32, 'c' * 32)])
        self.assertEqual(self.proof.unknown_permits, [])
        self.assertGreaterEqual(self.now, 16)

    def test_search_visible_residual_is_not_success(self):
        self.read.side_effect = lambda *a, **kw: document() if kw.get('realtime') is False else None
        self.proof.unknown_permits = [{'group': 'a' * 32, 'owner': 'b' * 32}]
        with self.assertRaises(AutoApiError):
            self.observe()
        self.release.assert_not_called()

    def test_delay_and_reappearance_are_observed(self):
        def read(*args, **kwargs):
            return document() if self.now in (4, 10) else None
        self.read.side_effect = read
        self.observe()
        self.assertEqual(self.delete.call_count, 2)
        self.assertGreaterEqual(self.now, 16)

    def test_reappearance_after_window_fails(self):
        self.read.side_effect = lambda *a, **kw: document() if self.now >= 15 else None
        with self.assertRaises(AutoApiError):
            self.observe()
        self.delete.assert_not_called()

    def test_version_mismatch_no_delete(self):
        self.read.return_value = document(_source={'tenantId': '123', 'projectId': '9001',
                                                  'groupId': '8001', 'sourceVersion': '3'})
        with self.assertRaises(AutoApiError):
            self.observe()
        self.delete.assert_not_called()

    def test_409_no_blind_retry(self):
        self.read.return_value = document()
        from src.apps.data_factory.exceptions import DataFactoryError, DATA_FACTORY_ES_CLEANUP_TARGET_CHANGED
        self.delete.side_effect = DataFactoryError(DATA_FACTORY_ES_CLEANUP_TARGET_CHANGED)
        with self.assertRaises(DataFactoryError):
            self.observe()
        self.assertEqual(self.delete.call_count, 1)

    def test_index_recreation_rejected(self):
        self.resolve.return_value = ('project_123', 'recreated')
        with self.assertRaises(AutoApiError):
            self.observe()
        self.read.assert_not_called()

    def test_interruption_restarts_observation(self):
        def pause(seconds):
            self.now += 50 if self.now == 3 else seconds
        Service.observe(self.record, self.rule, self.proof, SimpleNamespace(),
                        clock=lambda: self.now, pause=pause, elapsed_wait=lambda: 0)
        self.assertGreaterEqual(self.now, 69)

    def test_pool_wait_is_not_observation_time(self):
        wait = [0]
        def read(*a, **kw):
            if self.now == 2:
                self.now += 100
                wait[0] += 100
            return None
        self.read.side_effect = read
        Service.observe(self.record, self.rule, self.proof, SimpleNamespace(),
                        clock=lambda: self.now, pause=self.pause, elapsed_wait=lambda: wait[0])
        self.assertGreaterEqual(self.now, 116)

    def test_settlement_failure_keeps_owner(self):
        self.proof.unknown_permits = [{'group': 'a' * 32, 'owner': 'b' * 32}]
        self.release.side_effect = OSError('offline')
        with self.assertRaises(OSError):
            self.observe()
        self.assertEqual(len(self.proof.unknown_permits), 1)

    def test_sql_unknown_not_released_by_es_success(self):
        # ES只捕获自己的请求异常，不从SQL异常中接管任何名额。
        self.observe()
        self.release.assert_not_called()


class ApiResourceLifecycleTests(SimpleTestCase):
    def setUp(self):
        self.rule = ApiResourceCleanupRule.model_validate(rule_data())
        self.proof = proof_data()
        self.record = SimpleNamespace(id=5, case_id=1, step_id=10, parameter_id=30, test_env=0,
            case=SimpleNamespace(id=1, project_product_id=3),
            trace=SimpleNamespace(id=1, trace_id='trace', test_suite_id=1, test_suite_detail_id=2),
            cleanup_token='c' * 32, rule=self.rule.model_dump(mode='json'), proof=self.proof.model_dump(mode='json'))
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Service, 'claim', return_value=nullcontext(True)))
        self.stack.enter_context(patch.object(Service, 'check'))
        def save(record, proof, **changes):
            record.proof = proof.model_dump(mode='json')
            record.__dict__.update(changes)
        self.persist = self.stack.enter_context(patch.object(Service, 'persist', side_effect=save))
        self.binding = self.stack.enter_context(patch.object(IO, 'binding', return_value=(SimpleNamespace(), None)))
        self.stack.enter_context(patch.object(IO, 'sql', side_effect=lambda *a, **kw: nullcontext(Mock())))
        self.sql_delete = self.stack.enter_context(patch.object(IO, 'delete_sql'))
        self.sql_verify = self.stack.enter_context(patch.object(IO, 'verify_sql'))
        self.stack.enter_context(patch.object(ES, 'resolve_index', return_value=('project_123', 'uuid')))
        self.stack.enter_context(patch.object(IO, 'document', return_value=None))
        self.observe = self.stack.enter_context(patch.object(Service, 'observe'))
        self.stack.enter_context(patch('src.apps.data_factory.services.infrastructure.DatasourceInfrastructureService.resolve_verified_requests'))

    def test_cleanup_success_records_both_proofs(self):
        Service.cleanup(self.record)
        self.assertEqual(self.record.status, State.CLEANED.value)
        self.assertTrue(self.record.proof['sql_cleaned'])
        self.assertTrue(self.record.proof['es_verified'])
        self.sql_delete.assert_called_once()
        self.sql_verify.assert_called_once()

    def test_sql_failure_blocks_es_delete(self):
        from src.apps.auto_api.exceptions import API_RESOURCE_CLEANUP_FAILED
        self.sql_delete.side_effect = AutoApiError(API_RESOURCE_CLEANUP_FAILED, value=('SQL仍有残留',))
        with self.assertRaises(AutoApiError):
            Service.cleanup(self.record)
        self.observe.assert_not_called()
        self.assertFalse(self.record.proof['sql_cleaned'])
        self.assertEqual(self.record.status, State.FAILED.value)

    def test_identity_correction_is_verified_and_audited_without_rewriting_snapshot(self):
        mapping = {'es_business_id_path': 'projects[].projectId', 'es_version_path': 'projects[].projectVersion'}
        doc = document(_source={'tenantId': '123', 'groupId': '8001',
            'projects': [{'projectId': '9001', 'projectVersion': '2'}]})
        original = deepcopy(self.record.rule)
        with patch.object(IO, 'find', return_value=dict(self.proof.root)), \
             patch.object(IO, 'document', return_value=doc):
            Service.correct_identity(self.record, self.rule, self.proof, mapping, 4, persist=False)
            self.assertIsNone(self.proof.es_identity_correction)
            self.persist.assert_not_called()
            Service.correct_identity(self.record, self.rule, self.proof, mapping, 4)
        self.assertEqual(self.record.rule, original)
        self.assertEqual(self.proof.es_identity_correction.operator_id, 4)
        self.assertTrue(self.proof.es_identity_correction.corrected_at)

    def test_identity_correction_cannot_change_targets_or_accept_foreign_sql(self):
        from src.apps.auto_api.schemas.resource_cleanup import ApiResourceEsIdentityMapping
        with self.assertRaises(ValidationError):
            ApiResourceEsIdentityMapping.model_validate({'es_business_id_path': 'projects[].projectId',
                'es_version_path': 'projects[].projectVersion', 'document_id': 'other'})
        with patch.object(IO, 'find', return_value={**self.proof.root, 'version': '999'}), \
             self.assertRaises(AutoApiError):
            Service.correct_identity(self.record, self.rule, self.proof,
                {'es_business_id_path': 'projects[].projectId', 'es_version_path': 'projects[].projectVersion'}, 4)
        self.persist.assert_not_called()

    def test_shared_document_correction_does_not_persist(self):
        doc = document(_source={'tenantId': '123', 'groupId': '8001', 'projects': [
            {'projectId': '9001', 'projectVersion': '2'}, {'projectId': 'foreign', 'projectVersion': '2'}]})
        with patch.object(IO, 'find', return_value=dict(self.proof.root)), \
             patch.object(IO, 'document', return_value=doc), self.assertRaises(AutoApiError):
            Service.correct_identity(self.record, self.rule, self.proof,
                {'es_business_id_path': 'projects[].projectId', 'es_version_path': 'projects[].projectVersion'}, 4)
        self.persist.assert_not_called()

    def test_child_correction_preserves_frozen_root_tenant_order_and_limits(self):
        mapping = [{'original_table': 'project_field_value', 'table': 'field_value', 'foreign_key': 'business_id'}]
        original = deepcopy(self.record.rule)
        with patch.object(IO, 'find', return_value=dict(self.proof.root)), \
             patch.object(IO, 'verify_child_mapping') as verify:
            Service.correct_children(self.record, self.rule, self.proof, mapping, 4, persist=False)
            self.persist.assert_not_called()
            Service.correct_children(self.record, self.rule, self.proof, mapping, 4)
            self.assertEqual(verify.call_count, 2)
        self.assertEqual(self.record.rule, original)
        changed = Service.children_rule(self.rule, self.proof.child_corrections)
        self.assertEqual(changed.children[1].table, 'field_value')
        self.assertEqual(changed.children[1].foreign_key, 'business_id')
        self.assertEqual(changed.children[1].root_field, self.rule.children[1].root_field)
        self.assertEqual(changed.children[1].tenant_field, self.rule.children[1].tenant_field)
        self.assertEqual(changed.children[1].max_rows, self.rule.children[1].max_rows)

    def test_rejection_observation_does_not_skip_window_or_accept_created_row(self):
        rule = ApiResourceCleanupRule.model_validate(rule_data(rejection_response={'success': False}))
        proof = proof_data()
        proof.root = {}
        proof.rejection_confirmed = True
        now = [0]
        with patch.object(IO, 'find', return_value=None):
            Service.observe_rejection(self.record, rule, proof, Mock(), clock=lambda: now[0],
                pause=lambda seconds: now.__setitem__(0, now[0] + seconds))
        self.assertGreaterEqual(now[0], 16)
        with patch.object(IO, 'find', return_value={'id': 'new'}), self.assertRaises(AutoApiError):
            Service.observe_rejection(self.record, rule, proof, Mock(), clock=lambda: 0, pause=Mock())

    def test_retry_clean_sql_only_verifies_original_targets(self):
        self.record.proof['sql_cleaned'] = True
        Service.cleanup(self.record)
        self.sql_delete.assert_not_called()
        self.sql_verify.assert_called_once()
        self.observe.assert_called_once()

    def test_claim_idempotence(self):
        with patch.object(Service, 'claim', return_value=nullcontext(False)):
            Service.cleanup(self.record)
        self.binding.assert_not_called()

    def test_api_assertion_failure_still_runs_cleanup_and_stays_failure(self):
        from src.apps.auto_api.services.test_case.test_case_parts.execution import ApiTestCaseExecutionMixin
        runtime = SimpleNamespace(resource_cleanup_manager=Mock(), api_case_result=SimpleNamespace(
            status=0, error_message='业务断言失败', resource_cleanup_results=[]))
        runtime.resource_cleanup_manager.trace.id = 8
        with patch('src.apps.auto_api.selectors.resource_cleanup.ApiResourceCleanupSelector.trace_summary',
                   return_value=[{'id': 5, 'status': 'cleaned'}]):
            ApiTestCaseExecutionMixin.run_resource_cleanup(runtime)
        runtime.resource_cleanup_manager.cleanup.assert_called_once()
        self.assertEqual(runtime.api_case_result.status, 0)
        self.assertEqual(runtime.api_case_result.error_message, '业务断言失败')

    def test_active_execution_not_retryable(self):
        record = SimpleNamespace(proof={}, trace=SimpleNamespace(finished_at=None, worker_name='worker',
                                                       summary={}, started_at=None))
        with patch('src.apps.system.services.runtime_center.heartbeat.ServiceHeartbeatService.get_online_instances',
                   return_value=[]), self.assertRaises(AutoApiError):
            Retry.require_execution_ended(record)

    def test_finalizer_storage_failure_does_not_skip_other_finally_cleanup(self):
        from src.apps.auto_api.services.test_case.test_case_parts.execution import ApiTestCaseExecutionMixin
        runtime = SimpleNamespace(resource_cleanup_manager=Mock(), api_case_result=SimpleNamespace(
            status=1, error_message='', resource_cleanup_results=[]))
        runtime.resource_cleanup_manager.cleanup.side_effect = OSError('must not be exposed')
        with patch('src.apps.auto_api.selectors.resource_cleanup.ApiResourceCleanupSelector.trace_summary',
                   side_effect=OSError('must not be exposed')), \
             patch('src.apps.data_factory.services.infrastructure.DatasourceInfrastructureService.log_reference',
                   return_value='safe-reference'):
            ApiTestCaseExecutionMixin.run_resource_cleanup(runtime)
        self.assertTrue(runtime._resource_cleanup_finished)
        self.assertEqual(runtime.api_case_result.status, 0)
        self.assertIn('safe-reference', runtime.api_case_result.error_message)
        self.assertNotIn('must not be exposed', runtime.api_case_result.error_message)


class ApiResourceRequestTests(SimpleTestCase):
    def test_rejection_captured_before_assertions_but_partial_identity_is_not_accepted(self):
        rule = ApiResourceCleanupRule.model_validate(rule_data(rejection_response={'success': False}))
        proof = proof_data()
        proof.root = {}
        record = SimpleNamespace(rule=rule.model_dump(mode='json'), proof=proof.model_dump(mode='json'))
        manager = Manager(Mock(), Mock(), Mock(), [rule.model_dump()])
        with patch.object(Service, 'persist') as save:
            manager.after_response(record, SimpleNamespace(code=200, json={'success': False, 'data': None}))
            self.assertTrue(save.call_args.args[1].rejection_confirmed)
        for response in ({'success': True}, {'success': False, 'data': {'projectId': '9001'}}):
            with patch.object(Service, 'persist') as save:
                manager.after_response(record, SimpleNamespace(code=200, json=response))
                save.assert_not_called()

    def test_reused_name_requires_preceding_current_execution_marker(self):
        setup = SimpleNamespace(test_data=Mock())
        manager = Manager(Mock(), Mock(), setup, [rule_data(key='seed', trigger_step_key='step-9'),
                                                rule_data(name_source_key='seed')])
        with self.assertRaises(AutoApiError):
            manager.activate(10, 30)
        manager.markers['seed'] = 'AUTO_same_execution'
        manager.activate(10, 30)
        self.assertEqual(manager.markers['project'], manager.markers['seed'])

    def test_registration_does_not_require_es_absent(self):
        setup = SimpleNamespace(test_data=Mock())
        setup.test_data.get_cache.side_effect = lambda key: {'tenant': '123', 'employee': '456'}[key]
        manager = Manager(SimpleNamespace(id=1, project_product_id=3), Mock(), setup, [rule_data()])
        manager.activate(10, 30)
        marker = manager.markers['project']
        request = SimpleNamespace(method='POST', protocol_type='http', request_body={'name': marker})
        target = proof_data().sql_target
        record = SimpleNamespace(id=8, cleanup_token='')
        with patch.object(IO, 'binding', return_value=(Mock(), target)), \
             patch.object(IO, 'validate_children'), \
             patch.object(IO, 'sql', return_value=nullcontext(Mock())), \
             patch.object(IO, 'find', return_value=None), \
             patch.object(ES, 'resolve_index', return_value=('project_123', 'uuid')), \
             patch.object(ES, 'document') as es_document, \
             patch('src.apps.auto_api.services.resource_cleanup.ApiCaseExecutionResource.objects') as objects, \
             patch.object(Service, 'persist') as persist:
            objects.filter.return_value.exists.return_value = False
            objects.create.return_value = record
            self.assertIs(manager.before_request(request, 20, 0), record)
            self.assertTrue(persist.call_args.args[1].request_sent)
            self.assertEqual(objects.create.call_args.kwargs['proof']['unique_name'], marker)
            es_document.assert_not_called()

    def test_retry_disabled_and_unique_marker_required(self):
        manager = Manager(SimpleNamespace(id=1), Mock(), SimpleNamespace(test_data=Mock()), [rule_data()])
        with self.assertRaises(AutoApiError):
            manager.activate(10, 30, retries=2)
        manager.activate(10, 30)
        with self.assertRaises(AutoApiError):
            manager.before_request(SimpleNamespace(method='POST', protocol_type='http',
                                                   request_body={'name': 'AUTO_old'}), 20, 0)

    def test_registration_hook_runs_before_physical_request(self):
        from src.apps.auto_api.services.base.api_base_test_setup.base_request import BaseRequest
        from src.apps.auto_api.schemas.execution import ApiExecutionRequest
        setup = BaseRequest.__new__(BaseRequest)
        setup.timeout = 5
        setup.test_data = None
        setup.resource_cleanup_manager = Mock()
        setup.resource_cleanup_api_info_id, setup.resource_cleanup_test_env = 20, 0
        order = []
        setup.resource_cleanup_manager.before_request.side_effect = lambda *a: order.append('registered') or Mock()
        setup.resource_cleanup_manager.after_response.side_effect = lambda *a: order.append('captured')
        response = Mock()
        with patch('src.apps.auto_api.services.base.api_base_test_setup.base_request.HttpSseProtocolClient') as client:
            client.return_value.request.side_effect = lambda *a: order.append('sent') or response
            setup.http(ApiExecutionRequest(method='POST', url='https://example.com/create',
                       body_type='json', body_config={'body': {'name': 'AUTO_unique'}}), 3)
        self.assertEqual(order, ['registered', 'sent', 'captured'])


class ApiResourcePermissionTests(SimpleTestCase):
    def test_selector_rejects_missing_permissions_including_admin(self):
        from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector as Selector
        with patch('src.apps.user.services.permission.PermissionMenuService.permission_keys_for_user', return_value=set()):
            with self.assertRaises(AutoApiError):
                Selector.records(SimpleNamespace(is_super_admin=True), 1)

    def test_selector_requires_case_scope(self):
        from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector as Selector
        with patch('src.apps.user.services.permission.PermissionMenuService.permission_keys_for_user',
                   return_value={'api.case:read'}), \
             patch('src.apps.auto_api.selectors.case_configuration.ApiCaseConfigurationSelector.scoped_cases') as cases:
            cases.return_value.exists.return_value = False
            with self.assertRaises(AutoApiError):
                Selector.records(SimpleNamespace(), 1)

    def test_http_and_mcp_share_read_permission_for_execution_control(self):
        from src.apps.user.services.http_permission_registry import HTTP_PERMISSION_RULES
        from src.interfaces.mcp.authentication import component_policy
        for tool in ('get_api_case_resource_cleanup_schema', 'get_api_case_resource_cleanup_results',
                     'cleanup_api_case_resources'):
            self.assertEqual(component_policy(tool).permission_key, 'api.case:read')
        for action, method in (('resource_cleanup_results', 'get'), ('resource_cleanup_retry', 'post')):
            self.assertEqual(HTTP_PERMISSION_RULES[(
                'src.apps.auto_api.api.views.api_case.ApiCaseViews', action, method)], 'api.case:read')

    def test_demo_cleanup_is_a_write(self):
        from src.interfaces.mcp.server import _tool_operation
        self.assertIn(_tool_operation('cleanup_api_case_resources'), ('delete', 'write', 'cleanup'))
