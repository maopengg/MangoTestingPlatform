"""Real ORM scenarios, called only from the isolated SQLite test process."""


def verify_workflow_flow(user, product):
    from src.apps.evaluation.models import EvaluationDataset
    from src.apps.evaluation.services.dataset_version import EvaluationDatasetVersionService
    from src.apps.evaluation.services.dataset_item import EvaluationDatasetItemService
    from src.apps.evaluation.services.versioning import EvaluationVersionService
    from src.apps.evaluation.services.case import EvaluationCaseService
    from src.apps.evaluation.services.execution import EvaluationCaseExecutionService
    dataset = EvaluationDataset.objects.create(name="workflow regression", task_type=["问答"])
    steps = [
        {"id": "prepare", "name": "隔离用户", "stage": "prepare", "scope": "group", "action": "script", "code": 'def main(input, context): return {"id": context["session"]["id"]}'},
        {"id": "ready", "name": "等待完成", "stage": "ready", "scope": "group", "action": "script", "code": 'def main(input, context): return {"ready": True}', "until_path": "$.ready"},
        {"id": "gold", "name": "独立参考答案", "stage": "reference", "scope": "item", "action": "script", "input_data": {"question": "${{question}}", "attachment": "${{attachment}}"},
         "code": 'def main(input, context): return {"expected_output": {"answer": input["question"], "citations": [input["attachment"]]}}'},
        {"id": "clean", "name": "清理用户", "stage": "cleanup", "scope": "group", "action": "script", "code": 'def main(input, context): return {"cleaned": context["session"]["id"]}'},
    ]
    version = EvaluationDatasetVersionService.create(dataset_id=dataset.id, user=user, values={"schema_snapshot": {
        "input_variables": [{"name": "question", "path": "$.question"}, {"name": "attachment", "path": "$.attachment"}],
        "workflow": {"sequence": "conversation", "preparation": "create", "steps": steps}}})
    for key in ("A", "B"):
        EvaluationDatasetItemService.save(version=version, values={"input_data": {"question": "初始问题", "attachment": "example.txt"}, "expected_output": {"answer": "初始标准"},
            "scenario": {"group_key": "user", "order": 1 if key == "A" else 2, "turns": [
                {"input_data": {"question": "第一轮", "attachment": "example.txt"}, "expected_output": {}, "score": False},
                {"input_data": {"question": "第二轮", "attachment": "example.txt"}, "expected_output": {"answer": "独立参考步骤覆盖此值"}, "score": True},
            ]}})
    EvaluationVersionService.publish_dataset_version(version.id, user)
    config = {"target": {"type": "script", "parameters": {"code": 'def main(input, context):\n    assert "gold" not in input["steps"]\n    assert "expected_output" not in input\n    return {"answer": input["question"], "citations": [input["attachment"]]}'}},
        "grading": {"default_graders": [{"grader_key": "exact_match", "metric_key": "answer", "parameters": {"actual_path": "answer", "expected_path": "answer"}},
            {"grader_key": "set_match", "metric_key": "citation", "parameters": {"actual_path": "citations", "expected_path": "citations"}}]}}
    version.refresh_from_db()
    case = EvaluationCaseService.save(values={"name": "workflow case", "project_product": product, "dataset_version": version, "status": "enabled", "config": config})
    record = EvaluationCaseExecutionService.create({"case_id": case.id, "test_env": 1}, user)
    EvaluationCaseExecutionService.execute(record.id)
    record.refresh_from_db()
    assert record.verdict == "passed", (record.details, record.summary, list(record.item_results.values("details", "error_category")))
    assert record.summary["valid"] == 2
    assert len([step for step in record.details["workflow"] if step["step_id"] == "prepare"]) == 1
    assert len([step for step in record.details["workflow"] if step["step_id"] == "clean"]) == 1
    assert all(len(item.details["turns"]) == 2 and item.grade_results.count() == 4 for item in record.item_results.all())
    assert record.snapshot["dataset_config"]["input_variables"][1]["name"] == "attachment"
    timeline = EvaluationDatasetVersionService.create(dataset_id=dataset.id, user=user, values={"schema_snapshot": {
        "workflow": {"sequence": "timeline", "preparation": "create", "steps": [
            {"id": "write", "name": "按时间写入材料", "stage": "before_turn", "turn_kind": "material", "scope": "item", "action": "script", "input_data": {"material": "${{turn.input}}"},
             "code": 'def main(input, context): return {"memory": input["material"]["fact"]}'},
            {"id": "cleanup", "name": "清理时序空间", "stage": "cleanup", "scope": "group", "action": "script", "code": 'def main(input, context): return {"cleaned": True}'},
        ]}}})
    for index, city in enumerate(("上海", "北京"), 1):
        EvaluationDatasetItemService.save(version=timeline, values={"input_data": {"question": "目前住哪里"}, "expected_output": {"answer": city},
            "scenario": {"group_key": "person", "order": index, "turns": [
                {"kind": "material", "input_data": {"fact": city}, "score": False},
                {"input_data": {"question": "目前住哪里"}, "expected_output": {"answer": city}, "score": True}]}})
    EvaluationVersionService.publish_dataset_version(timeline.id, user)
    timeline.refresh_from_db()
    first, second = list(timeline.items.order_by("id"))
    timeline_config = {"target": {"type": "script", "parameters": {"code": 'def main(input, context): return {"answer": input["steps"]["write"]["memory"]}'}},
        "data_selection": {"item_ids": [second.id]}, "grading": {"default_graders": [{"grader_key": "exact_match", "metric_key": "answer"}]}}
    timeline_case = EvaluationCaseService.save(values={"name": "timeline case", "project_product": product, "dataset_version": timeline, "status": "enabled", "config": timeline_config})
    run = EvaluationCaseExecutionService.create({"case_id": timeline_case.id, "test_env": 1}, user)
    EvaluationCaseExecutionService.execute(run.id)
    run.refresh_from_db()
    assert run.verdict == "passed", (run.summary, list(run.item_results.values("details")))
    assert run.summary["total"] == 1 and run.summary["dependency_count"] == 1
    assert run.item_results.get(dataset_item_id=first.id).verdict == "not_evaluated"
    assert run.item_results.get(dataset_item_id=first.id).execution_status == "success"
    assert run.item_results.get(dataset_item_id=second.id).actual_output == {"answer": "北京"}
    failed = run.item_results.get(dataset_item_id=second.id)
    failed.verdict = "failed"
    failed.save()
    retry = EvaluationCaseExecutionService.retry_failed(run.id, user)
    assert retry.item_results.count() == 2
    EvaluationCaseExecutionService.execute(retry.id)
    retry.refresh_from_db()
    assert retry.verdict == "passed" and retry.summary["dependency_count"] == 1
    from src.apps.evaluation.exceptions import EvaluationError
    try:
        EvaluationDatasetVersionService.delete(timeline.id, user)
    except EvaluationError:
        pass
    else:
        raise AssertionError("Published version was deleted")
    draft = EvaluationDatasetVersionService.create(dataset_id=dataset.id, user=user, values={})
    draft_item = EvaluationDatasetItemService.save(version=draft, values={"input_data": {}, "expected_output": {}})
    draft_id, item_id = draft.id, draft_item.id
    EvaluationDatasetVersionService.delete(draft_id, user)
    from src.apps.evaluation.models import EvaluationDatasetVersion, EvaluationDatasetItem
    assert not EvaluationDatasetVersion.objects.filter(pk=draft_id).exists()
    assert not EvaluationDatasetItem.objects.filter(pk=item_id).exists()
