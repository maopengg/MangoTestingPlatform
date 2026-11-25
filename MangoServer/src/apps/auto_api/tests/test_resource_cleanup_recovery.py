from contextlib import ExitStack, nullcontext
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch

from django.test import SimpleTestCase
from pydantic import ValidationError

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.schemas.resource_cleanup import ApiResourceCleanupRule, ApiResourceRejectionRecovery
from src.apps.auto_api.services.resource_cleanup.resource_cleanup import ApiResourceCleanupService as Service, ApiResourceExecutionManager as Manager
from src.apps.auto_api.services.resource_cleanup.resource_cleanup_io import ApiResourceCleanupIO as IO
from src.apps.auto_api.tests.test_resource_cleanup import rule_data, proof_data, document
from src.apps.test_center.services.results.execution_result import ExecutionResultService as Results

SQL_CONTEXT = IO.sql


class HistoricalRejectionTests(SimpleTestCase):
    def setUp(self):
        history = patch("src.apps.data_factory.services.cleanup.cleanup_history.ResourceCleanupHistoryService.append")
        history.start()
        self.addCleanup(history.stop)
        self.rule = ApiResourceCleanupRule.model_validate(rule_data())
        self.proof = proof_data()
        self.proof.root = {}
        self.record = SimpleNamespace(id=19, case_id=1, step_id=10, parameter_id=30,
            test_env=0, trace=SimpleNamespace(trace_id='AUTO_trace', finished_at='ended', user_id=4))
        self.payload = {'id': 1, 'trace_id': 'AUTO_trace', 'test_env': 0, 'user_id': 4, 'steps': [
            {'id': 10, 'parameter_id': 30, 'api_info_id': 20,
             'request': {'protocol_type': 'http', 'method': 'POST', 'request_body': {'name': 'AUTO_once'}},
             'response': {'code': 200, 'json': {'success': False, 'data': None}}}]}
        self.result = SimpleNamespace(id=55, result_checksum=Results.calc_result_checksum(self.payload))
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('src.apps.test_center.selectors.execution_result.ExecutionResultAccessSelector.api_resource_evidence_result', return_value=self.result))
        self.stack.enter_context(patch.object(Results, 'load_result_data', side_effect=lambda _: self.payload))
        self.persist = self.stack.enter_context(patch.object(Service, 'persist'))
        self.stack.enter_context(patch.object(Service, 'check'))
        self.stack.enter_context(patch.object(Service, 'context', return_value={}))

    def recover(self, persist=False):
        return Service.recover_rejection(self.record, self.rule, self.proof,
            {'rejection_response': {'success': False}}, 4, persist=persist)

    def test_preview_does_not_modify_and_apply_preserves_original_rule(self):
        original = self.rule.model_dump()
        evidence = self.recover()
        self.assertEqual(evidence.execution_result_id, 55)
        self.assertFalse(self.proof.rejection_confirmed)
        self.persist.assert_not_called()
        self.recover(persist=True)
        self.assertTrue(self.proof.rejection_confirmed)
        self.assertEqual(self.proof.rejection_evidence.operator_id, 4)
        self.assertEqual(self.rule.model_dump(), original)
        self.assertEqual(self.proof.root, {})
        evidence = self.proof.rejection_evidence
        self.recover(persist=True)
        self.assertEqual(self.proof.rejection_evidence, evidence)
        self.assertEqual(self.persist.call_count, 1)

    def test_recovered_rejection_still_requires_full_observation_and_rejects_new_rows(self):
        self.recover(persist=True)
        now = [0.0]
        with patch.object(IO, 'sql', side_effect=lambda *a, **k: nullcontext(Mock())), \
                patch.object(IO, 'find', return_value=None):
            Service.observe_rejection(self.record, self.rule, self.proof, Mock(),
                clock=lambda: now[0], pause=lambda seconds: now.__setitem__(0, now[0] + seconds))
        self.assertGreaterEqual(now[0], 16)
        with patch.object(IO, 'sql', side_effect=lambda *a, **k: nullcontext(Mock())), \
                patch.object(IO, 'find', return_value={'id': 'unexpected'}), self.assertRaises(AutoApiError):
            Service.observe_rejection(self.record, self.rule, self.proof, Mock(), clock=lambda: 0, pause=Mock())

    def test_read_only_user_cannot_request_historical_recovery(self):
        from src.apps.auto_api.services.resource_cleanup.resource_cleanup import ApiResourceCleanupRetryService
        with patch('src.apps.user.services.authorization.permission.PermissionMenuService.permission_keys_for_user',
                   return_value={'api.case:read'}), self.assertRaises(AutoApiError):
            ApiResourceCleanupRetryService.retry(user=SimpleNamespace(id=99), case_id=1, resource_id=19,
                rejection_recovery={'rejection_response': {'success': False}})

    def test_modified_or_wrong_execution_results_are_rejected(self):
        for key, value in (('trace_id', 'other'), ('id', 2), ('test_env', 1), ('user_id', 9)):
            with self.subTest(key=key):
                data = deepcopy(self.payload)
                data[key] = value
                with patch.object(Results, 'load_result_data', return_value=data), self.assertRaises(AutoApiError):
                    self.recover()
        self.payload['steps'][0]['response']['json']['success'] = True
        with self.assertRaises(AutoApiError):
            self.recover()
        self.persist.assert_not_called()

    def test_matching_checksum_does_not_allow_partial_ids_timeouts_or_wrong_marker(self):
        changes = [({'code': 500, 'json': {'success': False}}, 'AUTO_once'),
                   ({'code': 200, 'json': {'success': False, 'data': {'group_id': '8001'}}}, 'AUTO_once'),
                   ({'code': 200, 'json': {'success': False}}, 'other')]
        for response, name in changes:
            self.payload['steps'][0]['response'] = response
            self.payload['steps'][0]['request']['request_body']['name'] = name
            self.result.result_checksum = Results.calc_result_checksum(self.payload)
            with self.subTest(response=response), self.assertRaises(AutoApiError):
                self.recover()
        self.persist.assert_not_called()

    def test_unknown_permit_active_execution_and_missing_result_are_not_accepted(self):
        self.proof.unknown_permits = [{'group': 'g', 'owner': 'o'}]
        with self.assertRaises(AutoApiError):
            self.recover()
        self.proof.unknown_permits = []
        self.record.trace.finished_at = None
        with self.assertRaises(AutoApiError):
            self.recover()
        self.record.trace.finished_at = 'ended'
        with patch.object(Results, 'load_result_data', return_value=None), self.assertRaises(AutoApiError):
            self.recover()

    def test_contract_rejects_true_string_and_numeric_false(self):
        for value in (True, 'false', 0):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ApiResourceRejectionRecovery.model_validate({'rejection_response': {'success': value}})


class VersionEvidenceTests(SimpleTestCase):
    def setUp(self):
        history = patch("src.apps.data_factory.services.cleanup.cleanup_history.ResourceCleanupHistoryService.append")
        history.start()
        self.addCleanup(history.stop)
        self.update = {'trigger_step_key': 'step-11', 'api_info_id': 21, 'request_id_in_url': True,
                       'response_id_path': 'data.id', 'response_version_path': 'data.version',
                       'success_response': {'success': True}}
        self.rule = ApiResourceCleanupRule.model_validate(rule_data(version_updates=[self.update]))
        self.proof = proof_data()
        self.record = SimpleNamespace(id=1, case_id=1, test_env=0, rule=self.rule.model_dump(),
                                      proof=self.proof.model_dump(), trace=Mock())
        self.query = Mock()
        self.query.filter.return_value.select_related.return_value.first.return_value = self.record
        self.manager = Manager(SimpleNamespace(id=1, project_product_id=3), Mock(), Mock(), [self.rule.model_dump()])
        self.manager.activate(11, 31)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('src.apps.auto_api.services.resource_cleanup.resource_cleanup.ApiCaseExecutionResource.objects', self.query))
        self.stack.enter_context(patch.object(Service, 'claim', return_value=nullcontext(True)))
        self.stack.enter_context(patch.object(Service, 'context', return_value={}))
        self.stack.enter_context(patch.object(IO, 'binding', return_value=(Mock(), self.proof.sql_target)))
        self.stack.enter_context(patch.object(IO, 'sql', side_effect=lambda *a, **k: nullcontext(Mock())))
        self.find = self.stack.enter_context(patch.object(IO, 'find', return_value=dict(self.proof.root)))
        self.persist = self.stack.enter_context(patch.object(Service, 'persist'))

    def attempt(self):
        return self.manager.before_request(SimpleNamespace(protocol_type='http', method='POST',
            url='https://example.com/projects/9001/update', request_body={}), 21, 0)

    def test_version_advances_only_with_matching_response_and_sql(self):
        attempt = self.attempt()
        self.find.return_value = {**self.proof.root, 'version': '3'}
        self.manager.after_response(attempt, SimpleNamespace(code=200, json={'success': True, 'data': {'id': '9001', 'version': 3}}))
        proof = self.persist.call_args.args[1]
        self.assertEqual(proof.root['version'], '2')
        self.assertEqual(IO.owned_root(proof, self.rule)['version'], '3')
        self.assertEqual(proof.version_transitions[0].step_id, 11)
        IO.check_document(document(_source={'tenantId': '123', 'projectId': '9001', 'groupId': '8001', 'sourceVersion': 3}), self.rule, proof)
        with self.assertRaises(AutoApiError):
            IO.check_document(document(), self.rule, proof)

    def test_unaccounted_change_or_response_conflict_cannot_advance_version(self):
        self.find.return_value = {**self.proof.root, 'version': '99'}
        with self.assertRaises(AutoApiError):
            self.attempt()
        self.find.return_value = dict(self.proof.root)
        attempt = self.attempt()
        for identity, version, sql_version in (('other', 3, '3'), ('9001', 2, '2'), ('9001', 3, '4')):
            self.find.return_value = {**self.proof.root, 'version': sql_version}
            with self.subTest(identity=identity, version=version), self.assertRaises(AutoApiError):
                self.manager.after_response(attempt, SimpleNamespace(code=200,
                    json={'success': True, 'data': {'id': identity, 'version': version}}))
        self.persist.assert_not_called()

    def test_es_lag_accepts_only_owned_history_and_never_deletes_old_version(self):
        from src.apps.data_factory.services.datasource.elasticsearch import ElasticsearchDatasourceService as ES
        attempt = self.attempt()
        self.find.return_value = {**self.proof.root, 'version': '3'}
        self.manager.after_response(attempt, SimpleNamespace(code=200,
            json={'success': True, 'data': {'id': '9001', 'version': 3}}))
        proof = self.persist.call_args.args[1]
        self.assertFalse(Service.confirm_document(document(), self.rule, proof))
        with self.assertRaises(AutoApiError):
            Service.confirm_document(document(_source={'tenantId': '123', 'projectId': '9001',
                'groupId': '8001', 'sourceVersion': 99}), self.rule, proof)
        now, deleted = [0], [False]
        def read(*args, **kwargs):
            if deleted[0]:
                return None
            return document(_source={'tenantId': '123', 'projectId': '9001', 'groupId': '8001',
                                     'sourceVersion': 2 if now[0] < 3 else 3})
        def delete(*args, **kwargs):
            self.assertEqual(kwargs['expected']['_source']['sourceVersion'], 3)
            deleted[0] = True
        with patch.object(Service, 'check'), patch.object(ES, 'resolve_index', return_value=('project_123', 'uuid')), \
                patch.object(IO, 'document', side_effect=read), patch.object(ES, 'document', side_effect=delete):
            Service.observe(self.record, self.rule, proof, Mock(), clock=lambda: now[0],
                pause=lambda seconds: now.__setitem__(0, now[0] + seconds), elapsed_wait=lambda: 0)
        self.assertTrue(deleted[0])
        self.assertGreaterEqual(now[0], 16)

    def test_tampered_identity_in_version_chain_cannot_be_used(self):
        attempt = self.attempt()
        self.find.return_value = {**self.proof.root, 'version': '3'}
        self.manager.after_response(attempt, SimpleNamespace(code=200,
            json={'success': True, 'data': {'id': '9001', 'version': 3}}))
        proof = self.persist.call_args.args[1]
        proof.version_transitions[0].root_after['tenant_id'] = 'foreign'
        with self.assertRaises(AutoApiError):
            IO.owned_root(proof, self.rule)

    def test_failed_response_and_multi_scenario_do_not_prove_mutation(self):
        attempt = self.attempt()
        self.manager.after_response(attempt, SimpleNamespace(code=200, json={'success': False}))
        self.persist.assert_not_called()
        with self.assertRaises(AutoApiError):
            self.manager.activate(11, 31, scenarios=2)

    def test_lease_is_returned_even_on_sql_error(self):
        engine = MagicMock()
        engine.connect.return_value.__enter__ = Mock(side_effect=RuntimeError('fixture'))
        with patch('src.apps.auto_api.services.resource_cleanup.resource_cleanup_io.DataFactoryDatasource.create_engine', return_value=engine):
            with self.assertRaises(RuntimeError):
                with SQL_CONTEXT(Mock(), {}):
                    pass
        engine.dispose.assert_called_once()
