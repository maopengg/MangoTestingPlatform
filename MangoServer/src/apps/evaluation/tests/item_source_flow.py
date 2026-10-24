"""Exercise two different per-item SQL queries in the isolated ORM flow."""


def verify_item_source_flow(user, product):
    import sqlite3
    from unittest.mock import patch
    from src.apps.evaluation.models import EvaluationDataset
    from src.apps.evaluation.services.dataset_version import EvaluationDatasetVersionService
    from src.apps.evaluation.services.dataset_item import EvaluationDatasetItemService
    from src.apps.evaluation.services.versioning import EvaluationVersionService
    from src.apps.evaluation.services.case import EvaluationCaseService
    from src.apps.evaluation.services.execution import EvaluationCaseExecutionService
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE contracts(id INTEGER, name TEXT, owner TEXT)")
    db.execute("INSERT INTO contracts VALUES(101, '订单A', '隐藏标准答案')")
    calls = []
    def query(**kwargs):
        calls.append((kwargs["operation_config"], kwargs["parameters"]))
        rows = [dict(row) for row in db.execute(kwargs["operation_config"], kwargs["parameters"])]
        return {"rows": rows, "truncated": False}
    try:
        with patch("src.apps.evaluation.services.item_source.resource_configuration", return_value=(None, {"db_type": 2, "id": 42})), \
             patch("src.apps.data_factory.services.data_source_execution.DataSourceExecutionService.execute", side_effect=query):
            dataset = EvaluationDataset.objects.create(name="per-item contracts", task_type=["问答"])
            version = EvaluationDatasetVersionService.create(dataset_id=dataset.id, user=user, values={})
            items = {}
            for key, sql, parameters, text in [
                ("by-id", "SELECT id, name, owner FROM contracts WHERE id = :id", {"id": 101}, "订单ID=${{contract_id}}"),
                ("by-name", "SELECT name, owner FROM contracts WHERE name = :name", {"name": "订单A"}, "订单名称=${{contract_name}}"),
                ("empty", "SELECT id FROM contracts WHERE id = :id", {"id": 999}, "不可调用"),
            ]:
                items[key] = EvaluationDatasetItemService.save(version=version, values={
                    "scenario": {"group_key": "contract" if key == "by-id" else ""},
                    "data_source": {"kind": "sql", "binding": {"resource": "item_source", "project_product_id": product.id, "ref_id": 42}, "query": sql, "parameters": parameters, "key": "contract_id,contract_name,owner" if key == "by-id" else "contract_name,owner"},
                    "input_data": {"question": text}, "expected_output": {"answer": text, "evidence": "${{owner}}"},
                    "context": {"source_evidence": [{"excerpt": "订单负责人：${{owner}}"}]}})
            EvaluationVersionService.publish_dataset_version(version.id, user)
            version.refresh_from_db()
            case = EvaluationCaseService.save(values={"name": "per-item source case", "project_product": product, "dataset_version": version, "status": "enabled", "config": {
                "target": {"type": "script", "parameters": {"code": 'def main(input, context):\n    assert "data" not in input and "rows" not in input\n    assert "item_source" not in input["steps"]\n    assert "隐藏标准答案" not in str(input)\n    return {"answer": input["case_input"]["question"]}'}},
                "grading": {"default_graders": [{"grader_key": "exact_match", "metric_key": "answer"}]}}})
            run = EvaluationCaseExecutionService.create({"case_id": case.id, "test_env": 1}, user)
            from src.apps.evaluation.services.graders import ExactMatchGrader
            with patch.object(ExactMatchGrader, "evaluate", wraps=ExactMatchGrader.evaluate) as grading:
                EvaluationCaseExecutionService.execute(run.id)
            assert grading.call_count == 2
            for call in grading.call_args_list:
                sample = call.kwargs["dataset_item"]
                assert sample["expected_output"]["evidence"] == "隐藏标准答案"
                assert sample["context"]["source_evidence"] == [{"excerpt": "订单负责人：隐藏标准答案"}]
                assert "${{" not in str(sample["input_data"])
            run.refresh_from_db()
            assert run.summary["valid"] == 2 and run.summary["invalid"] == 1, (run.summary, list(run.item_results.values("details")))
            assert run.item_results.get(dataset_item_id=items["by-id"].id).actual_output == {"answer": "订单ID=101"}
            assert run.item_results.get(dataset_item_id=items["by-name"].id).actual_output == {"answer": "订单名称=订单A"}
            resolved = run.item_results.get(dataset_item_id=items["by-id"].id)
            assert resolved.resolved_expected_output == {"answer": "订单ID=101", "evidence": "隐藏标准答案"}
            assert resolved.details["turns"][0]["context"] == {"source_evidence": [{"excerpt": "订单负责人：隐藏标准答案"}]}
            assert not run.item_results.get(dataset_item_id=items["empty"].id).attempts
            assert len(calls) == 3 and calls[0][0] != calls[1][0]
            original_query = run.item_results.get(dataset_item_id=items["by-name"].id).item_snapshot["data_source"]["query"]
            draft = EvaluationDatasetVersionService.create(dataset_id=dataset.id, user=user, source_version_id=version.id, values={})
            copied = draft.items.order_by("id")[1]
            assert copied.id != items["by-name"].id
            assert copied.data_source["query"] == original_query
        verify_reference_api_flow(user, product)
    finally:
        db.close()


def verify_reference_api_flow(user, product):
    from unittest.mock import patch
    from src.apps.evaluation.models import EvaluationDataset
    from src.apps.evaluation.services.dataset_version import EvaluationDatasetVersionService
    from src.apps.evaluation.services.dataset_item import EvaluationDatasetItemService
    from src.apps.evaluation.services.versioning import EvaluationVersionService
    from src.apps.evaluation.services.case import EvaluationCaseService
    from src.apps.evaluation.services.execution import EvaluationCaseExecutionService
    from src.apps.evaluation.services.graders import ExactMatchGrader
    with patch('src.apps.evaluation.services.item_source.resource_configuration', return_value=(12, {'checksum': 'api-fixed'})), \
         patch('src.apps.auto_api.services.test_case.test_api_info.TestApiInfo') as runtime:
        runtime.return_value.api_info_run.side_effect = [
            {'json': {'data': {'id': 101, 'owner': '隐藏标准答案'}}}, {'json': {'data': {}}},
        ]
        dataset = EvaluationDataset.objects.create(name='reference interface contracts', task_type=['问答'])
        version = EvaluationDatasetVersionService.create(dataset_id=dataset.id, user=user, values={})
        items = []
        for query_id in (101, 999):
            items.append(EvaluationDatasetItemService.save(version=version, values={
                'data_source': {'kind': 'api_info', 'binding': {'resource': 'item_source', 'project_product_id': product.id, 'ref_id': 42},
                    'parameters': {'query_id': query_id}, 'variables': [{'name': 'contract_id', 'path': '$.json.data.id'}, {'name': 'contract_owner', 'path': '$.json.data.owner'}]},
                'input_data': {'question': '订单ID=${{contract_id}}'},
                'expected_output': {'answer': '订单ID=${{contract_id}}'},
                'context': {'source_evidence': [{'excerpt': '${{contract_owner}}'}]},
            }))
        EvaluationVersionService.publish_dataset_version(version.id, user)
        version.refresh_from_db()
        case = EvaluationCaseService.save(values={'name': 'reference interface case', 'project_product': product, 'dataset_version': version, 'status': 'enabled', 'config': {
            'target': {'type': 'script', 'parameters': {'code': 'def main(input, context):\n    assert "隐藏标准答案" not in str(input)\n    assert "contract_owner" not in input\n    return {"answer": input["case_input"]["question"]}'}},
            'grading': {'default_graders': [{'grader_key': 'exact_match', 'metric_key': 'answer'}]},
        }})
        run = EvaluationCaseExecutionService.create({'case_id': case.id, 'test_env': 1}, user)
        with patch.object(ExactMatchGrader, 'evaluate', wraps=ExactMatchGrader.evaluate) as grading:
            EvaluationCaseExecutionService.execute(run.id)
        run.refresh_from_db()
        assert run.summary['valid'] == 1 and run.summary['invalid'] == 1, run.summary
        assert grading.call_count == 1
        assert grading.call_args.kwargs['dataset_item']['context'] == {'source_evidence': [{'excerpt': '隐藏标准答案'}]}
        result = run.item_results.get(dataset_item_id=items[0].id)
        assert result.actual_output == {'answer': '订单ID=101'}
        assert result.resolved_expected_output == {'answer': '订单ID=101'}
        assert result.details['turns'][0]['context'] == {'source_evidence': [{'excerpt': '隐藏标准答案'}]}
        assert not run.item_results.get(dataset_item_id=items[1].id).attempts
        assert runtime.return_value.api_info_run.call_count == 2
        assert all(call.kwargs['revision_id'] == 12 for call in runtime.return_value.api_info_run.call_args_list)
