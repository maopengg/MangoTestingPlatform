from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import SimpleTestCase
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.services.item_source import validate_item_source, freeze_item_source, resolve_item_source


class ItemDataSourceTests(SimpleTestCase):
    def api_source(self, **values):
        return {"kind": "api_info", "module_id": 5,
                "binding": {"resource": "item_source", "project_product_id": 1, "ref_id": 10},
                "parameters": {"query_id": 101},
                "variables": [{"name": "contract_id", "path": "$.json.data.id"},
                              {"name": "contract_owner", "path": "$.json.data.owner"},
                              {"name": "contract_evidence", "path": "$.json.data.evidence"}], **values}

    def test_reference_api_requires_named_variables_and_rejects_reserved_names(self):
        self.assertEqual(validate_item_source(self.api_source()).kind.value, 'api_info')
        for variables in ([], [{"name": "session", "path": "$"}], [{"name": "x", "path": "$"}] * 2,
                          [{"name": "x", "path": "data.id"}], [{"name": "x", "path": "$.id "}]):
            with self.subTest(variables=variables), self.assertRaises(EvaluationError):
                validate_item_source(self.api_source(variables=variables))
        with self.assertRaises(EvaluationError):
            validate_item_source(self.source(variables=[{"name": "x", "path": "$"}]))

    def test_reference_api_freezes_published_revision_and_rejects_scope_or_content_changes(self):
        with patch('src.apps.evaluation.services.item_source.resource_configuration', return_value=(12, {'checksum': 'fixed'})) as configuration:
            result = freeze_item_source(self.api_source(), SimpleNamespace(), product_id=1)
            self.assertEqual(configuration.call_args.args[0].value, 'api_info')
            self.assertEqual(result['binding']['revision_id'], 12)
            self.assertTrue(result['binding']['content_hash'])
            with self.assertRaises(EvaluationError):
                freeze_item_source(self.api_source(), SimpleNamespace(), product_id=2)
        with patch('src.apps.evaluation.services.item_source.resource_configuration', return_value=(12, {'checksum': 'changed'})):
            with self.assertRaises(EvaluationError):
                freeze_item_source(result, SimpleNamespace(), product_id=1)

    def test_reference_api_extracts_private_typed_variables_and_does_not_mutate_templates(self):
        from src.apps.evaluation.services.workflow import replace_workflow_values
        response = {'json': {'data': {'id': 101, 'owner': '张三', 'evidence': [{'excerpt': '负责人是张三'}]}}}
        runner = SimpleNamespace(execution=SimpleNamespace(created_by=None, case=SimpleNamespace(project_product_id=1)),
            bindings={}, records=[], persist=Mock(), call_until=Mock(return_value=response))
        row = SimpleNamespace(dataset_item_id=9, item_snapshot={'data_source': self.api_source()})
        with patch('src.apps.evaluation.services.item_source.freeze_item_source'):
            variables = resolve_item_source(runner, row, SimpleNamespace(input_data={}), {'session': {}, 'execution': {}, 'factories': []})
        self.assertEqual(variables, {'contract_id': 101, 'contract_owner': '张三', 'contract_evidence': [{'excerpt': '负责人是张三'}]})
        self.assertEqual(runner.call_until.call_args.args[0].action.value, 'api_info')
        self.assertEqual(runner.call_until.call_args.args[1], {'query_id': 101})
        self.assertEqual(runner.bindings, {})
        template = {'input_data': {'id': '${{contract_id}}'}, 'expected_output': {'answer': '${{contract_owner}}'},
                    'context': {'source_evidence': '${{contract_evidence}}'}}
        result = replace_workflow_values(template, variables)
        self.assertEqual(result['input_data'], {'id': 101})
        self.assertEqual(result['expected_output'], {'answer': '张三'})
        self.assertEqual(result['context'], {'source_evidence': [{'excerpt': '负责人是张三'}]})
        self.assertEqual(template['expected_output']['answer'], '${{contract_owner}}')

    def test_missing_reference_path_marks_preparation_failed(self):
        runner = SimpleNamespace(execution=SimpleNamespace(created_by=None, case=SimpleNamespace(project_product_id=1)),
            bindings={}, records=[], persist=Mock(), call_until=Mock(return_value={'json': {'data': {}}}))
        row = SimpleNamespace(dataset_item_id=9, item_snapshot={'data_source': self.api_source()})
        with patch('src.apps.evaluation.services.item_source.freeze_item_source'), self.assertRaises(EvaluationError):
            resolve_item_source(runner, row, SimpleNamespace(input_data={}), {'session': {}, 'execution': {}, 'factories': []})
        self.assertEqual(runner.records[0]['status'], 'failed')
        self.assertEqual(runner.bindings, {})

    def source(self, **values):
        return {"kind": "sql", "query": "SELECT id FROM contracts WHERE id = :id", "parameters": {"id": 101},
                "binding": {"resource": "item_source", "project_product_id": 1, "ref_id": 10}, **values}

    def test_source_requires_resource_and_rejects_write_sql(self):
        for value in (self.source(binding=None), self.source(query="DELETE FROM contracts"), self.source(query="SELECT 1; DELETE FROM contracts")):
            with self.subTest(value=value), self.assertRaises(EvaluationError):
                validate_item_source(value)

    def test_each_source_freezes_independently_and_checks_drift_and_product(self):
        user = SimpleNamespace()
        with patch("src.apps.evaluation.services.item_source.resource_configuration", return_value=(None, {"db_type": 2, "id": 10})):
            value = freeze_item_source(self.source(), user, product_id=1)
            self.assertTrue(value["binding"]["content_hash"])
            self.assertNotIn("content_hash", self.source()["binding"])
            with self.assertRaises(EvaluationError):
                freeze_item_source(value, user, product_id=2)
        with patch("src.apps.evaluation.services.item_source.resource_configuration", return_value=(None, {"db_type": 2, "id": 11})):
            with self.assertRaises(EvaluationError):
                freeze_item_source(value, user, product_id=1)

    def test_manual_rows_have_no_implicit_source(self):
        self.assertEqual(freeze_item_source({}, SimpleNamespace()), {})
        with self.assertRaises(EvaluationError):
            validate_item_source({"kind": "manual", "query": "SELECT 1"})

    def test_sql_keys_are_normalized_and_reject_collisions_and_invalid_references(self):
        self.assertEqual(validate_item_source(self.source(key=" contract_id, contract_name ")).key, "contract_id,contract_name")
        for key in ("contract-id", "contract.id", "session", "steps", "id,id", ","):
            with self.subTest(key=key), self.assertRaises(EvaluationError):
                validate_item_source(self.source(key=key))

    def test_sql_keys_use_the_api_case_cache_mapping_without_shared_state(self):
        first = {"id": 101, "name": "订单A"}
        for key, expected in (("contract_id,contract_name", {"contract_id": 101, "contract_name": "订单A"}),
                              ("name,id", {"name": "订单A", "id": 101}),
                              ("contract_id", {"contract_id": 101}), ("", {})):
            with self.subTest(key=key), patch("src.apps.evaluation.services.item_source.freeze_item_source"):
                runner = SimpleNamespace(execution=SimpleNamespace(created_by=None, case=SimpleNamespace(project_product_id=1)),
                    bindings={}, records=[], persist=Mock(), call_until=Mock(return_value={"rows": [first], "truncated": False}))
                row = SimpleNamespace(dataset_item_id=9, item_snapshot={"data_source": self.source(key=key)})
                values = resolve_item_source(runner, row, SimpleNamespace(input_data={}), {"session": {}, "execution": {}, "factories": []})
                self.assertEqual(values, expected)
                self.assertEqual(runner.bindings, {})

    def test_factory_values_resolve_input_expected_and_evidence_with_original_types(self):
        from src.apps.evaluation.services.workflow import replace_workflow_values
        output = {"id": 101, "owner": "张三", "evidence": [{"excerpt": "负责人是张三"}]}
        runner = SimpleNamespace(execution=SimpleNamespace(created_by=None, case=SimpleNamespace(project_product_id=1)),
            bindings={}, records=[], persist=Mock(), call_until=Mock(return_value={"output": output}))
        source = {"kind": "factory", "binding": {"resource": "item_source", "project_product_id": 1, "ref_id": 10}}
        row = SimpleNamespace(dataset_item_id=9, item_snapshot={"data_source": source})
        with patch("src.apps.evaluation.services.item_source.freeze_item_source"):
            variables = resolve_item_source(runner, row, SimpleNamespace(input_data={}), {"session": {}, "execution": {}, "factories": []})
        templates = {
            "input_data": {"query": "查询订单${{data.id}}", "id": "${{data.id}}"},
            "expected_output": {"answer": "${{data.owner}}"},
            "context": {"source_evidence": "${{data.evidence}}"},
        }
        resolved = replace_workflow_values(templates, variables)
        self.assertEqual(resolved, {
            "input_data": {"query": "查询订单101", "id": 101},
            "expected_output": {"answer": "张三"},
            "context": {"source_evidence": [{"excerpt": "负责人是张三"}]},
        })
        self.assertEqual(templates["context"]["source_evidence"], "${{data.evidence}}")
