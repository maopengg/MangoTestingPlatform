from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from src.apps.user.services.mcp_permission_registry import MCP_PERMISSION_RULES
from src.apps.evaluation.exceptions import EVALUATION_DATASET_ACCESS_DENIED, EvaluationError
from src.apps.evaluation.services.graders import RankingGrader, EvaluationGraderRegistry
from src.apps.evaluation.services.assets import set_case_status
from src.apps.evaluation.presenters import case_summary
from src.apps.user.services.permission import PermissionMenuService
from src.interfaces.mcp.authentication import component_policy, permission_error
from src.interfaces.mcp.server import _tool_operation, McpDomainPathApp
from src.interfaces.mcp.tools.evaluation import register_evaluation_tools


class EvaluationMcpTests(SimpleTestCase):
    def test_dataset_item_creation_validates_payload_after_scoped_version_lookup(self):
        from src.apps.evaluation.services.assets import create_dataset_item
        user, version = SimpleNamespace(id=4), SimpleNamespace(id=8)
        path = 'src.apps.evaluation.services.assets'
        with patch(path + '.get_dataset_version', return_value=version) as lookup, \
             patch('src.apps.evaluation.services.dataset_item.EvaluationDatasetItemService.save', return_value=SimpleNamespace(id=9)) as save:
            result = create_dataset_item(8, {'input_data': {'query': '订单查询'}, 'expected_output': {'answer': '订单A'}}, user)
            self.assertEqual(result.id, 9)
            lookup.assert_called_once_with(8, user)
            self.assertEqual(save.call_args.kwargs['version'], version)
            self.assertEqual(save.call_args.kwargs['values']['input_data'], {'query': '订单查询'})
            save.reset_mock()
            with self.assertRaises(EvaluationError):
                create_dataset_item(8, {'dataset_version_id': 999}, user)
            save.assert_not_called()

    def test_item_update_uses_scoped_lookup_and_existing_draft_validation(self):
        functions = {}

        class Registry:
            def tool(self):
                def register(function):
                    functions[function.__name__] = function
                    return function
                return register

        register_evaluation_tools(Registry())
        item = SimpleNamespace(dataset_version=SimpleNamespace(id=7))
        user = SimpleNamespace(id=4)
        path = 'src.interfaces.mcp.tools.evaluation'
        with patch(path + '.current_user', return_value=user), \
             patch(path + '.get_dataset_item', return_value=item) as lookup, \
             patch(path + '.EvaluationDatasetItemService.save', return_value=item) as save, \
             patch(path + '.presenters.item_record', return_value={'id': 8}):
            functions['update_evaluation_dataset_item'](8, {'answer': '北京'})
            lookup.assert_called_once_with(8, user)
            save.assert_called_once_with(values={'expected_output': {'answer': '北京'}},
                                         version=item.dataset_version, instance=item)
            save.reset_mock()
            functions['update_evaluation_dataset_item'](8, {'answer': '北京'}, metadata={})
            save.assert_called_once_with(values={'expected_output': {'answer': '北京'}, 'metadata': {}},
                                         version=item.dataset_version, instance=item)
        with patch(path + '.current_user', return_value=user), \
             patch(path + '.get_dataset_item', side_effect=EvaluationError(EVALUATION_DATASET_ACCESS_DENIED)), \
             patch(path + '.EvaluationDatasetItemService.save') as save:
            with self.assertRaises(EvaluationError):
                functions['update_evaluation_dataset_item'](8, {'answer': '北京'})
            save.assert_not_called()

    def test_every_registered_tool_has_an_explicit_valid_permission(self):
        class Registry:
            def __init__(self):
                self.names = set()

            def tool(self):
                def register(function):
                    self.names.add(function.__name__)
                    return function
                return register
        registry = Registry()
        register_evaluation_tools(registry)
        evaluation_rules = {name: rule['permission_key'] for name, rule in MCP_PERMISSION_RULES.items()
                            if (rule['permission_key'] or '').startswith('evaluation.')}
        self.assertEqual(registry.names, set(evaluation_rules))
        for name, permission in evaluation_rules.items():
            self.assertEqual(component_policy(name).permission_key, permission)
            self.assertIn(permission, PermissionMenuService.all_permission_keys())

    def test_read_permission_does_not_grant_publish_or_asset_changes(self):
        with patch('src.interfaces.mcp.authentication.PermissionMenuService.is_effective_super_admin', return_value=False), \
             patch('src.interfaces.mcp.authentication.PermissionMenuService.permission_keys_for_user', return_value={'evaluation.case:read', 'evaluation.dataset'}):
            for name in ('publish_evaluation_dataset_version', 'update_evaluation_case_status', 'update_evaluation_dataset_item', 'create_evaluation_dataset_item'):
                self.assertIsNotNone(permission_error(SimpleNamespace(), name, {}))

    def test_stop_is_classified_as_a_write_for_demo_environments(self):
        self.assertEqual(_tool_operation('stop_evaluation_case_execution'), 'execute')
        self.assertEqual(_tool_operation('update_evaluation_dataset_item'), 'update')
        self.assertEqual(_tool_operation('create_evaluation_dataset_item'), 'create')

    async def test_domain_endpoint_preserves_the_outer_mount_prefix(self):
        scopes = []

        async def application(scope, receive, send):
            scopes.append(scope)
        await McpDomainPathApp(application)({'type': 'http', 'path': '/evaluation', 'root_path': '/mcp'}, None, None)
        self.assertEqual(scopes[0]['path'], '/mcp/evaluation/')

    def test_read_permission_grants_case_execution_without_asset_edits(self):
        with patch('src.interfaces.mcp.authentication.PermissionMenuService.is_effective_super_admin', return_value=False), \
             patch('src.interfaces.mcp.authentication.PermissionMenuService.permission_keys_for_user', return_value={'evaluation.case:read'}):
            self.assertIsNone(permission_error(SimpleNamespace(), 'get_evaluation_case_execution', {}))
            self.assertIsNone(permission_error(SimpleNamespace(), 'run_evaluation_case', {}))
            self.assertIsNotNone(permission_error(SimpleNamespace(), 'update_evaluation_case', {}))

    def test_status_service_rejects_read_only_permission(self):
        with patch('src.apps.evaluation.services.assets.PermissionMenuService.is_effective_super_admin', return_value=False), \
             patch('src.apps.evaluation.services.assets.PermissionMenuService.permission_keys_for_user', return_value={'evaluation.case:read'}):
            with self.assertRaises(EvaluationError):
                set_case_status(1, 'enabled', SimpleNamespace())

    def test_case_list_does_not_expose_configuration(self):
        row = SimpleNamespace(id=1, name='Case', project_product_id=1, module_id=None, dataset_version_id=1,
                              description='', status='draft', config={'private': 'not-a-list-field'})
        self.assertNotIn('config', case_summary(row))

    def test_ranked_false_positives_are_not_perfect_when_gold_is_empty(self):
        for actual, expected_score in (([], 100), (['unrelated'], 0)):
            result = self.rank([], actual)
            self.assertTrue(all(metric.score == expected_score for metric in result.metrics))

    def test_changed_ranking_semantics_have_a_new_fixed_version(self):
        self.assertEqual(RankingGrader.version, 2)
        self.assertTrue(any(row['grader_key'] == 'ranking' and row['grader_version'] == 2 for row in EvaluationGraderRegistry.catalog()))

    def test_duplicates_keep_their_original_rank_and_cannot_inflate_dcg(self):
        result = self.rank(['A', 'B'], ['A', 'A', 'B'])
        self.assertLess(result.metrics[0].score, 100)
        self.assertGreaterEqual(result.metrics[0].score, 0)

    def test_structured_ids_are_supported_and_missing_array_is_invalid(self):
        self.assertEqual(self.rank([{'id': 'A'}], [{'id': 'A'}]).metrics[0].score, 100)
        with self.assertRaises(EvaluationError):
            self.rank(['A'], None)

    @staticmethod
    def rank(expected, actual):
        return RankingGrader.evaluate(dataset_item={'expected_output': {'ids': expected}}, actual={'ids': actual},
            config={'expected_path': 'ids', 'actual_path': 'ids', 'k': 5}, metric_key='ranking', threshold=80)
