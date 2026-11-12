from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import serializers

from src.apps.auto_api.enums.assertion import ApiDefaultAssertionCheck as Check
from src.apps.auto_api.schemas.case_schema import merge_scenario_protocol_config, unpack_scenario_body_config
from src.apps.auto_api.schemas.execution import ApiExecutionResponse
from src.apps.auto_api.services.api_case.mutation_io import ApiCaseParameterMutationService
from src.apps.auto_api.services.protocols.outcome import ProtocolCallOutcomeService as Outcome
from src.apps.auto_api.services.execution.cases.test_case_parts.protocol import ApiTestCaseProtocolMixin


class ScenarioProtocolChecksTests(SimpleTestCase):
    def response(self, protocol='http', **values):
        return ApiExecutionResponse(code=values.pop('code', 200), headers={}, time=0,
                                    request_protocol_type=protocol, response_mode=protocol, **values)

    def test_partial_protocol_update_preserves_request_body_and_metadata_is_not_sent(self):
        original = {'source_type': 'value', 'body': {'id': '${{example_id}}'}, 'grpc_config': {'timeout_seconds': 5}}
        config = {'inherit_system': False, 'checks': ['http_status', 'http_status']}
        result = ApiCaseParameterMutationService.clean_payload({'protocol_expectation': config}, original)
        self.assertEqual(original.keys(), {'source_type', 'body', 'grpc_config'})
        self.assertEqual(result['body_config']['body'], original['body'])
        self.assertEqual(result['body_config']['grpc_config'], original['grpc_config'])
        self.assertEqual(result['body_config']['protocol_expectation']['checks'], ['http_status'])
        body, _, _ = unpack_scenario_body_config('http', result['body_config'])
        self.assertNotIn('protocol_expectation', body)

    def test_nested_mcp_input_is_validated_and_inherit_clears_custom_selection(self):
        result = merge_scenario_protocol_config({'arguments': {'id': 1}, 'protocol_expectation': {'inherit_system': True, 'checks': ['mcp_result']}})
        self.assertEqual(result['protocol_expectation']['checks'], [])
        body, _, _ = unpack_scenario_body_config('mcp', result)
        self.assertEqual(body, {'id': 1})
        for invalid in ({'inherit_system': 'false'}, {'inherit_system': False, 'checks': ['unknown']},
                        {'inherit_system': False, 'checks': [True]}, {'inherit_system': False, 'checks': 'http_status'}):
            with self.subTest(invalid=invalid), self.assertRaises(serializers.ValidationError):
                merge_scenario_protocol_config({'protocol_expectation': invalid})

    def test_inherit_reads_global_and_custom_does_not_merge_global(self):
        with patch.object(Outcome, 'default_checks', return_value=frozenset({Check.HTTP_STATUS})):
            self.assertFalse(Outcome.evaluate(self.response(code=400), default_checks=Outcome.scenario_checks({})).success)
            self.assertFalse(Outcome.evaluate(self.response(code=400), default_checks=Outcome.scenario_checks({'inherit_system': True})).success)
            self.assertTrue(Outcome.evaluate(self.response(code=400), default_checks=Outcome.scenario_checks({'inherit_system': False, 'checks': []})).success)
        with patch.object(Outcome, 'default_checks', return_value=frozenset()):
            self.assertFalse(Outcome.evaluate(self.response(code=400), default_checks=Outcome.scenario_checks({'inherit_system': False, 'checks': ['http_status']})).success)

    def test_custom_http_check_is_not_bypassed_by_business_assertions(self):
        parameter = SimpleNamespace(body_config={'protocol_expectation': {'inherit_system': False, 'checks': ['http_status']}})
        self.assertEqual(ApiTestCaseProtocolMixin.resolve_protocol_expectation(parameter, self.response()), ([], False))
        parameter.body_config['protocol_expectation']['checks'] = []
        self.assertEqual(ApiTestCaseProtocolMixin.resolve_protocol_expectation(parameter, self.response()), ([], True))

    def test_all_registered_checks_use_same_runtime_and_transport_errors_still_fail(self):
        checks = Outcome.scenario_checks({'inherit_system': False, 'checks': [item.value for item in Check]})
        self.assertEqual(checks, frozenset(Check))
        self.assertFalse(Outcome.evaluate(self.response('graphql', json={'errors': ['invalid']}), default_checks=checks).success)
        self.assertFalse(Outcome.evaluate(self.response(code=None), default_checks=frozenset()).success)
        self.assertFalse(Outcome.evaluate(self.response(error_msg='timeout'), default_checks=frozenset()).success)
