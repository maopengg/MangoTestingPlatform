from mangotools.enums import TaskEnum

from src.apps.evaluation.enums import EvaluationCaseExecutionStatusEnum, EvaluationVerdictEnum
from src.apps.test_center.services.reporting.test_suite.evaluation import EvaluationReportService


def report_payload(execution):
    from src.apps.evaluation.services.grading.graders import EvaluationGraderRegistry
    snapshot = execution.snapshot
    target = {key: snapshot["target"][key] for key in ("type", "ref_id", "version_ref", "content_hash") if key in snapshot["target"]}
    return {
        "schema_version": 1, "execution_id": execution.id, "execution_no": execution.execution_no,
        "case": snapshot["case"], "dataset": snapshot["dataset"], "target": target,
        "selection": snapshot["selection"], "grader_bindings": snapshot["grader_bindings"],
        "signatures": snapshot["signatures"], "assessment": snapshot.get("assessment"),
        "environment": snapshot["environment"], "summary": execution.summary,
        "answer_model": snapshot.get("answer_model"), "summary_model": snapshot.get("summary_model"),
        "status": execution.status, "verdict": execution.verdict,
        "grader_names": {binding["grader_key"]: EvaluationGraderRegistry.names.get(binding["grader_key"], binding["grader_key"])
                         for binding in snapshot["grader_bindings"].values()},
        "error_message": (execution.details or {}).get("error_message"),
    }


def create_report(execution, case, user):
    execution.report_detail_id = EvaluationReportService.create(
        product_id=case.project_product_id, module_id=case.module_id, test_env=execution.test_env,
        user_id=user.id, case_id=case.id, name=execution.snapshot["case"]["name"],
        count=len(execution.snapshot["selection"]["item_ids"]) * execution.snapshot.get("execution", {}).get("repeat_count", 1), payload=report_payload(execution),
    )
    execution.save(update_fields=["report_detail", "update_time"])


def sync_report(execution):
    if not execution.report_detail_id:
        return
    states = EvaluationCaseExecutionStatusEnum
    if execution.status == states.PENDING.value:
        status = TaskEnum.STAY_BEGIN.value
    elif execution.status == states.STOPPED.value:
        status = TaskEnum.STOPPED.value
    elif execution.status == states.FAILED.value:
        status = TaskEnum.FAIL.value
    elif execution.status != states.COMPLETED.value:
        status = TaskEnum.PROCEED.value
    else:
        status = {
            EvaluationVerdictEnum.PASSED.value: TaskEnum.SUCCESS.value,
            EvaluationVerdictEnum.FAILED.value: TaskEnum.FAIL.value,
        }.get(execution.verdict, TaskEnum.WARNING.value)
    summary = execution.summary or {}
    EvaluationReportService.update(
        execution.report_detail_id, status=status, payload=report_payload(execution),
        count=summary.get("total", len(execution.snapshot["selection"]["item_ids"]) * execution.snapshot.get("execution", {}).get("repeat_count", 1)),
        success=summary.get("passed", 0), fail=summary.get("failed", 0),
        warning=summary.get("warning", 0) + summary.get("invalid", 0),
        error_message=(execution.details or {}).get("error_message"),
    )
