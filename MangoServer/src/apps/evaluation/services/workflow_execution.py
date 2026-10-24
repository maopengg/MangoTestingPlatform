"""Run dataset scenarios serially while keeping per-turn grading evidence."""

from copy import deepcopy
from types import SimpleNamespace
from src.apps.evaluation.enums import EvaluationExecutionStatusEnum, EvaluationGradeStatusEnum, EvaluationVerdictEnum
from src.apps.evaluation.enums import EvaluationCaseExecutionStatusEnum
from src.apps.evaluation.enums.workflow import EvaluationWorkflowStageEnum as Stage, EvaluationWorkflowScopeEnum as Scope
from src.apps.evaluation.formatters.payload import mask_sensitive, decimal_score
from src.apps.evaluation.services.failure import failure_message
from src.apps.evaluation.services.item_detail import update_item_details
from src.apps.evaluation.services.validation import invalid_config
from src.apps.evaluation.services.workflow import EvaluationWorkflowRunner, replace_workflow_values


def execute_dataset_workflow(service, execution, config, adapter, target, mapping, rows, worker_id):
    if execution.details.get("workflow"):
        raise invalid_config("有状态流程中断后不能直接重放写入，请核实清理后重新执行")
    runner = EvaluationWorkflowRunner(execution, config)
    ordered = sorted(rows, key=lambda row: (row.repeat_index,
        (0, row.item_snapshot["scenario"]["group_key"]) if (row.item_snapshot.get("scenario") or {}).get("group_key") else (1, row.dataset_item_id),
        (row.item_snapshot.get("scenario") or {}).get("order", 0), row.id))
    try:
        with runner.execution_scope():
            execution.status = EvaluationCaseExecutionStatusEnum.RUNNING.value
            execution.save(update_fields=["status", "update_time"])
            for index, row in enumerate(ordered):
                if runner.stopped():
                    break
                data = row.item_snapshot
                sample = SimpleNamespace(input_data=deepcopy(data.get("input_data", {})), expected_output=deepcopy(data.get("expected_output", {})),
                    context=deepcopy(data.get("context", {})), metadata=deepcopy(data.get("metadata", {})),
                    input_variables=[item.model_dump() for item in config.dataset_config.input_variables])
                row.grade_results.all().delete()
                outcomes = []
                row._workflow_turn = 0
                record_start = len(runner.records)
                try:
                    with runner.item_scope(row, sample) as state:
                        from src.apps.evaluation.services.item_source import resolve_item_source
                        source_values = resolve_item_source(runner, row, sample, state)
                        turns = (data.get("scenario") or {}).get("turns") or [{"input_data": sample.input_data, "expected_output": sample.expected_output, "context": sample.context, "score": True}]
                        for turn_index, turn in enumerate(turns, 1):
                            if data.get("dependency_only"):
                                turn = {**turn, "score": False}
                            if runner.stopped():
                                raise invalid_config("执行已停止")
                            row._workflow_turn = turn_index
                            sample.input_data = deepcopy(turn.get("input_data", {}))
                            sample.expected_output = deepcopy(turn.get("expected_output", {}))
                            sample.context = deepcopy(turn.get("context", {}))
                            state["turn"] = {"index": turn_index, "kind": turn.get("kind", "test"), "input": sample.input_data}
                            sample.runtime_context = {key: value for key, value in state.items() if key != "factories"}
                            runner.run_stage(Stage.BEFORE_TURN, Scope.ITEM, state, sample, row)
                            visible_state = {**{key: value for key, value in state.items() if key != "factories"}, **source_values}
                            sample.input_data = replace_workflow_values(sample.input_data, visible_state)
                            if turn.get("kind") != "material":
                                runner.run_stage(Stage.REFERENCE, Scope.ITEM, state, sample, row)
                                sample.input_data = replace_workflow_values(sample.input_data, visible_state)
                                sample.expected_output = replace_workflow_values(sample.expected_output, visible_state)
                                sample.context = replace_workflow_values(sample.context, visible_state)
                                validate_runtime_sample(config.dataset_config, sample)
                            if turn.get("kind") == "material":
                                output = {"prepared": True}
                            elif turn.get("score", True):
                                service._execute_item_core(execution, row, config, adapter, target, mapping, sample)
                                if row.execution_status != EvaluationExecutionStatusEnum.SUCCESS.value:
                                    raise invalid_config("轮次调用失败，后续轮次不再执行")
                                output = row.actual_output
                            else:
                                output = adapter.execute(target=target, dataset_item=sample, mapping=mapping, execution=execution, user_id=execution.created_by_id)["output"]
                                if config.answering:
                                    from src.apps.evaluation.services.answer import generate_answer
                                    output = generate_answer(settings=config.answering, frozen_model=config.answer_model, dataset_item=sample, retrieved=output,
                                        timeout_seconds=config.execution.item_timeout_seconds)
                            state["turn"]["output"] = output
                            state["steps"]["previous_turn"] = output
                            outcomes.append({"index": turn_index, "name": turn.get("name") or f"第 {turn_index} 轮", "input": mask_sensitive(sample.input_data),
                                "expected": mask_sensitive(sample.expected_output), "context": mask_sensitive(sample.context),
                                "output": mask_sensitive(output), "scored": turn.get("score", True),
                                "score": float(row.score) if row.score is not None and turn.get("score", True) else None,
                                "verdict": row.verdict if turn.get("score", True) else EvaluationVerdictEnum.NOT_EVALUATED.value})
                            runner.run_stage(Stage.AFTER_TURN, Scope.ITEM, state, sample, row)
                    scored = [turn for turn in outcomes if turn["scored"]]
                    row.execution_status = EvaluationExecutionStatusEnum.SUCCESS.value
                    scores = [turn["score"] for turn in scored if turn["score"] is not None]
                    row.score = decimal_score(sum(scores) / len(scores)) if scores else None
                    invalid = any(turn["verdict"] == EvaluationVerdictEnum.INVALID.value for turn in scored)
                    row.grade_status = EvaluationGradeStatusEnum.INVALID.value if invalid else EvaluationGradeStatusEnum.GRADED.value
                    row.verdict = EvaluationVerdictEnum.NOT_EVALUATED.value if data.get("dependency_only") else EvaluationVerdictEnum.INVALID.value if invalid else EvaluationVerdictEnum.PASSED.value if all(turn["verdict"] == EvaluationVerdictEnum.PASSED.value for turn in scored) else EvaluationVerdictEnum.FAILED.value
                except Exception as error:
                    scenario = data.get("scenario") or {}
                    runner.failed_groups[(scenario.get("group_key") or row.dataset_item_id, row.repeat_index)] = failure_message(error)
                    row.execution_status = EvaluationExecutionStatusEnum.FAILED.value
                    row.grade_status = EvaluationGradeStatusEnum.INVALID.value
                    row.verdict = EvaluationVerdictEnum.INVALID.value
                    row.score = None
                    row.error_category = "workflow_failed"
                    update_item_details(row, error_message=failure_message(error))
                row.details = {**row.details, "workflow": deepcopy(runner.records[record_start:]), "turns": outcomes,
                    "cleanup_error": "; ".join(runner.cleanup_errors) or None}
                row.save()
                service._heartbeat(execution.id, worker_id, config.execution.item_timeout_seconds)
                if config.execution.stop_on_critical_failure and row.grade_results.filter(hard_gate=True, passed=False).exists():
                    service._cancel_pending_items(execution, "critical_gate_stopped")
                    break
                execution.progress = min(99, round((index + 1) / len(rows) * 100))
                execution.save(update_fields=["progress", "update_time"])
    except Exception:
        service._cancel_pending_items(execution, "preparation_failed")
        raise
    if runner.stopped():
        return service._finish_stopped(execution)
    return service.aggregate(execution, config)


def validate_runtime_sample(dataset_config, sample):
    from jsonschema import Draft202012Validator, ValidationError
    for label, schema, value in (("输入", dataset_config.input_schema, sample.input_data),
            ("标准答案", dataset_config.expected_schema, sample.expected_output), ("评分证据", dataset_config.context_schema, sample.context)):
        try:
            Draft202012Validator(schema).validate(value)
        except ValidationError as error:
            path = ".".join(str(item) for item in error.path)
            raise invalid_config(f"动态{label}字段 {path or '$'} 不符合数据集字段定义") from error
