# -*- coding: utf-8 -*-
from src.apps.ai.agent.base import BaseAgent
from src.apps.ai.agent.functional_case.generator import FunctionalCaseGenerator
from src.apps.ai.enums import AiAgentTaskStatusEnum, AiAgentTaskTypeEnum
from src.apps.ai.enums.role import AgentRole
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentArtifact, AiAgentTask
from src.apps.ai.services.agent.context import AgentContextService
from src.apps.ai.services.agent.document import AgentDocumentService
from src.apps.ai.services.agent.task_step import AiAgentTaskStepService
from src.apps.ai.services.core import AiTaskService
from src.apps.ai.services.harness.artifact import AgentArtifactService
from src.apps.ai.services.harness.definition import AgentDefinitionService
from src.apps.ai.services.skill.service import AgentSkillService
from src.apps.functional_test.enums import FunctionalTestContextKeyEnum, ManualTestChangeStatusEnum
from src.apps.functional_test.models import ManualTestSuite
from src.apps.functional_test.selectors.querysets import FunctionalTestQuerySelector
from src.apps.functional_test.services.case_sync import FunctionalTestCaseSyncService
from src.apps.functional_test.services.suite import ManualTestSuiteService


class FunctionalCaseAgent(BaseAgent):
    task_type = AiAgentTaskTypeEnum.MANUAL_CASE_SYNC.value
    agent_key = "functional_case"
    fixed_role = AgentRole.BUSINESS_TEST_EXPERT
    step_defs = [
        {"key": "collect_context", "name": "收集上下文", "order": 1},
        {"key": "understand_requirement", "name": "理解需求", "order": 2},
        {"key": "inventory_existing_cases", "name": "盘点已有用例", "order": 3},
        {"key": "analyze_coverage", "name": "分析覆盖缺口", "order": 4},
        {"key": "plan_cases", "name": "规划用例", "order": 5},
        {"key": "generate_case_batches", "name": "分批生成用例", "order": 6},
        {"key": "normalize_cases", "name": "规范化用例", "order": 7},
        {"key": "deduplicate_cases", "name": "用例去重", "order": 8},
        {"key": "evaluate_coverage", "name": "校验覆盖", "order": 9},
        {"key": "repair_cases", "name": "修复缺口", "order": 10},
        {"key": "plan_changes", "name": "规划变更", "order": 11},
        {"key": "commit_cases", "name": "写入平台用例", "order": 12},
        {"key": "post_validate", "name": "写入后校验", "order": 13},
    ]

    @classmethod
    def start(
            cls,
            suite_id: int,
            context_keys: list | None = None,
            current_resource_ids: list | None = None,
            historical_context: list | None = None,
            skill_id: int | None = None,
            ai_role: str | None = None,
            deep_check: bool = False,
            user_instruction: str = "",
            user_id: int | None = None,
    ) -> AiAgentTask:
        suite = FunctionalTestQuerySelector.manual_test_suite().get(id=suite_id)
        cls.ensure_no_active_task(suite.id)
        context_payload = AgentContextService.build_functional_suite_context(
            suite,
            context_keys,
            historical_context=historical_context,
            current_resource_ids=current_resource_ids,
        )
        skill = AgentSkillService.resolve_functional_case_skill(skill_id)
        ai_role = AgentDefinitionService.resolve_role(cls.agent_key, ai_role)
        task = cls.create_task(
            f"同步功能测试Case：{suite.requirement_name or suite.id}",
            {
                "suite_id": suite.id,
                "selected_context_keys": context_payload["context_keys"],
                "context_hash": context_payload["context_hash"],
                "reuse_context": context_payload["reuse_context"],
                "reuse_context_id": context_payload["reuse_context_id"],
                "preserve_case_no": FunctionalTestContextKeyEnum.PLATFORM_CASE.value in context_payload["context_keys"],
                "skill_id": skill.id if skill else None,
                "skill_snapshot": AgentSkillService.skill_snapshot(skill) if skill else {},
                "ai_role": ai_role,
                "role_snapshot": AgentRole.snapshot(ai_role),
                "deep_check": bool(deep_check),
                "user_instruction": user_instruction,
                "current_resource_ids": context_payload.get("current_resource_ids") or [],
                "historical_context": context_payload.get("historical_context_manifest") or [],
                "source_manifest": context_payload.get("source_manifest") or {},
            },
            user_id=user_id,
            skill=skill if getattr(skill, "id", None) else None,
        )
        cls.attach_context_snapshot(task, context_payload)
        cls.dispatch(task.id)
        return task

    @classmethod
    def run(cls, task: AiAgentTask):
        input_data = task.input_data or {}
        suite = FunctionalTestQuerySelector.manual_test_suite().get(id=input_data.get("suite_id"))
        context_snapshot = cls.load_context_snapshot(task)
        try:
            doc = cls.execute_checkpointed_step(
                task,
                "collect_context",
                lambda: AgentDocumentService.read_document(
                    "",
                    context_snapshot.get("source_content") or input_data.get("source_content") or "",
                ),
                input_data=input_data,
                summarize=lambda value: {
                    "context_hash": input_data.get("context_hash"),
                    "selected_context_keys": input_data.get("selected_context_keys") or [],
                    "source_size": len(value.get("content") or ""),
                },
            )

            skill = AgentSkillService.materialize_task_skill(
                task,
                AgentSkillService.resolve_functional_case_skill(input_data.get("skill_id") or None),
            )
            ai_role = AgentDefinitionService.resolve_role(cls.agent_key, input_data.get("ai_role"))

            confirmation = input_data.get("confirmation") or {}
            confirmation_text = str(confirmation.get("answer") or "").strip()
            user_instruction = input_data.get("user_instruction") or ""
            if confirmation_text:
                user_instruction = "\n".join(
                    part
                    for part in [
                        user_instruction,
                        "用户对关键需求歧义的确认：" + confirmation_text,
                    ]
                    if part
                )
            common = {
                "source_content": doc["content"],
                "requirement_context": context_snapshot.get("requirement_context") or input_data.get(
                    "requirement_context") or "",
                "user_instruction": user_instruction,
                "skill": skill,
                "ai_role": ai_role,
                "task": task,
            }

            requirement_model = cls.execute_checkpointed_step(
                task,
                "understand_requirement",
                lambda: FunctionalCaseGenerator.analyze_requirement(**common),
            )
            if cls.wait_for_critical_ambiguity_confirmation(task, requirement_model):
                return
            existing_inventory = cls.execute_checkpointed_step(
                task,
                "inventory_existing_cases",
                lambda: FunctionalCaseGenerator.analyze_existing_coverage(
                    requirement_analysis=requirement_model,
                    source_content="\n\n".join(
                        part
                        for part in [
                            doc["content"],
                            context_snapshot.get("existing_case_inventory") or "",
                        ]
                        if part
                    ),
                    user_instruction=common["user_instruction"],
                    skill=skill,
                    ai_role=ai_role,
                    task=task,
                ),
            )

            coverage_matrix = cls.execute_checkpointed_step(
                task,
                "analyze_coverage",
                lambda: FunctionalCaseGenerator.finalize_coverage_matrix(
                    requirement_model,
                    existing_inventory,
                    FunctionalCaseGenerator.analyze_gap(
                        requirement_analysis=requirement_model,
                        existing_coverage=existing_inventory,
                        user_instruction=common["user_instruction"],
                        skill=skill,
                        ai_role=ai_role,
                        task=task,
                    ),
                ),
            )

            def build_case_plan():
                plan = FunctionalCaseGenerator.compose_case_plan(
                    requirement_model,
                    existing_inventory,
                    coverage_matrix,
                    preserve_existing=bool(input_data.get("preserve_case_no")),
                )
                return plan if plan.get("outline") else FunctionalCaseGenerator.build_outline(**common)

            case_plan = cls.execute_checkpointed_step(task, "plan_cases", build_case_plan)

            def generate_case_batches():
                payload = FunctionalCaseGenerator.generate_cases(outline=case_plan, **common)
                if not payload.get("cases"):
                    raise ai_service_error("未生成任何功能测试用例")
                return payload

            generated = cls.execute_checkpointed_step(
                task,
                "generate_case_batches",
                generate_case_batches,
                summarize=lambda value: {"case_count": len(value.get("cases") or [])},
            )
            normalized = cls.execute_checkpointed_step(
                task,
                "normalize_cases",
                lambda: FunctionalCaseGenerator.normalize(generated),
                summarize=lambda value: {"case_count": len(value.get("cases") or [])},
            )

            def deduplicate_payload(payload):
                cases, report = FunctionalCaseGenerator.deduplicate(
                    payload,
                    skill=skill,
                    ai_role=ai_role,
                    task=task,
                )
                return {"payload": cases, "report": report}

            dedup_result = cls.execute_checkpointed_step(
                task,
                "deduplicate_cases",
                lambda: deduplicate_payload(normalized),
                summarize=lambda value: value["report"],
            )
            deduplicated = dedup_result["payload"]

            initial_evaluation = cls.execute_checkpointed_step(
                task,
                "evaluate_coverage",
                lambda: FunctionalCaseGenerator.evaluate_final_coverage(
                    generated_payload=deduplicated,
                    requirement_model=requirement_model,
                    coverage_matrix=coverage_matrix,
                    user_instruction=common["user_instruction"],
                    skill=skill,
                    ai_role=ai_role,
                    task=task,
                ),
            )
            AgentArtifactService.evaluate(
                task,
                "functional_case_coverage",
                passed=bool(initial_evaluation.get("passed")),
                score=initial_evaluation.get("score") or 0,
                metrics={
                    "candidate_count": len(deduplicated.get("cases") or []),
                    "dimension_summary": initial_evaluation.get("dimension_summary") or {},
                },
                findings=initial_evaluation.get("findings") or [],
            )

            def repair_until_valid():
                payload = deduplicated
                report = initial_evaluation
                rounds = 0
                while (not report.get("passed") or (input_data.get("deep_check") and rounds < 2)) and rounds < 2:
                    if rounds == 0:
                        payload = FunctionalCaseGenerator.coverage_check_and_patch(
                            generated_payload=payload,
                            outline={
                                "requirement_model": requirement_model,
                                "coverage_matrix": coverage_matrix,
                                "case_plan": case_plan,
                            },
                            **common,
                        )
                    elif input_data.get("deep_check"):
                        payload = FunctionalCaseGenerator.deep_patch_cases(
                            generated_payload=payload,
                            **common,
                        )
                    else:
                        payload = FunctionalCaseGenerator.repair_findings(
                            generated_payload=payload,
                            findings=report.get("findings") or [],
                            requirement_model=requirement_model,
                            **common,
                        )
                    payload = FunctionalCaseGenerator.normalize(payload)
                    payload = deduplicate_payload(payload)["payload"]
                    rounds += 1
                    report = FunctionalCaseGenerator.evaluate_final_coverage(
                        generated_payload=payload,
                        requirement_model=requirement_model,
                        coverage_matrix=coverage_matrix,
                        user_instruction=common["user_instruction"],
                        skill=skill,
                        ai_role=ai_role,
                        task=task,
                    )
                if not report.get("passed"):
                    missing = "、".join(report.get("missing_criterion_ids") or []) or "无明确编号"
                    raise ai_service_error(f"功能用例未通过语义覆盖门禁，缺失验收点：{missing}")
                return {"payload": payload, "evaluation": report, "repair_rounds": rounds}

            repair_result = cls.execute_checkpointed_step(
                task,
                "repair_cases",
                repair_until_valid,
                summarize=lambda value: {
                    **cls.coverage_summary(value["payload"]),
                    "repair_rounds": value["repair_rounds"],
                    "evaluation": value["evaluation"],
                },
            )
            generated = repair_result["payload"]
            AgentArtifactService.evaluate(
                task,
                "functional_case_final_coverage",
                passed=True,
                score=repair_result["evaluation"].get("score") or 100,
                metrics={
                    "case_count": len(generated.get("cases") or []),
                    "repair_rounds": repair_result["repair_rounds"],
                    "dimension_summary": repair_result["evaluation"].get("dimension_summary") or {},
                },
                findings=repair_result["evaluation"].get("findings") or [],
            )

            preview = cls.execute_checkpointed_step(
                task,
                "plan_changes",
                lambda: {
                    **ManualTestSuiteService.sync_preview(
                        suite,
                        FunctionalCaseGenerator.normalize(generated),
                        preserve_case_no=bool(input_data.get("preserve_case_no")),
                    ),
                    "source": doc,
                },
                summarize=lambda value: {
                    "case_count": len(value.get("cases") or []),
                    "validation": value.get("validation") or {},
                    "changes": value.get("changes") or [],
                },
            )

            def commit_cases():
                FunctionalTestCaseSyncService.sync_confirm(suite, preview, task.create_user_id)
                changes = preview.get("changes") or []
                return {
                    "case_count": len(preview.get("cases") or []),
                    "added_count": sum(
                        1 for item in changes if item.get("change_status") == ManualTestChangeStatusEnum.ADDED.value),
                    "changed_count": sum(
                        1 for item in changes if item.get("change_status") == ManualTestChangeStatusEnum.CHANGED.value),
                    "removed_count": sum(
                        1 for item in changes if item.get("change_status") == ManualTestChangeStatusEnum.REMOVED.value),
                    "unchanged_count": sum(1 for item in changes if
                                           item.get("change_status") == ManualTestChangeStatusEnum.UNCHANGED.value),
                }

            output = cls.execute_checkpointed_step(
                task,
                "commit_cases",
                commit_cases,
                artifact_status="committed",
            )

            def post_validate():
                suite.refresh_from_db()
                stored_case_count = FunctionalTestQuerySelector.manual_test_case().filter(suite=suite).count()
                report = {**output, "stored_case_count": stored_case_count}
                if suite.case_count != stored_case_count:
                    raise ai_service_error("功能用例写入后数量校验失败")
                return report

            cls.execute_checkpointed_step(task, "post_validate", post_validate)
            AiTaskService.finish_task(task, output)
            cls.save_generation_context(
                suite=suite,
                task=task,
                context_payload=input_data,
                summary="同步功能 Case 成功",
                source_content=doc.get("content") or "",
                output={**output, "cases": preview.get("cases") or []},
                status=AiAgentTaskStatusEnum.SUCCESS.value,
            )
        except Exception as exc:
            failed_step = cls.current_running_step(task)
            if failed_step:
                AiAgentTaskStepService.fail_step(task, failed_step.step_key, exc)
            AiTaskService.fail_task(task, str(exc))
            cls.save_generation_context(
                suite=suite,
                task=task,
                context_payload=input_data,
                summary=str(exc) or "同步功能 Case 失败",
                source_content=context_snapshot.get("source_content") or input_data.get("source_content") or "",
                output={},
                status=AiAgentTaskStatusEnum.FAIL.value,
                error_message=str(exc),
            )
            raise

    @classmethod
    def ensure_no_active_task(cls, suite_id: int | str, exclude_task_id: int | None = None):
        queryset = AiAgentTask.objects.filter(
            task_type=cls.task_type,
            status__in=[
                AiAgentTaskStatusEnum.PENDING.value,
                AiAgentTaskStatusEnum.CLAIMED.value,
                AiAgentTaskStatusEnum.RUNNING.value,
                AiAgentTaskStatusEnum.WAITING_MODEL.value,
            ],
        ).order_by("-id")
        if exclude_task_id:
            queryset = queryset.exclude(id=exclude_task_id)
        for task in queryset[:200]:
            if str((task.input_data or {}).get("suite_id") or "") == str(suite_id):
                task = AiTaskService.reconcile_interrupted_task(task)
                if task.status in [
                    AiAgentTaskStatusEnum.PENDING.value,
                    AiAgentTaskStatusEnum.CLAIMED.value,
                    AiAgentTaskStatusEnum.RUNNING.value,
                    AiAgentTaskStatusEnum.WAITING_MODEL.value,
                ]:
                    raise ai_service_error("当前需求已有同步任务进行中，请等待完成后再操作")

    @staticmethod
    def task_snapshot(task: AiAgentTask) -> dict:
        return {
            "id": task.id,
            "status": task.status,
            "input_data": task.input_data or {},
            "output_data": task.output_data or {},
            "error_message": task.error_message or "",
        }

    @classmethod
    def save_generation_context(
            cls,
            suite: ManualTestSuite,
            task: AiAgentTask,
            context_payload: dict,
            summary: str,
            source_content: str,
            output: dict,
            status: int,
            error_message: str = "",
    ):
        cases = output.get("cases") if isinstance(output.get("cases"), list) else []
        sync_stats = {key: value for key, value in output.items() if key != "cases"}
        AgentContextService.save_context(
            suite_id=suite.id,
            context_type="manual_case_sync_dialog",
            context_hash=context_payload.get("context_hash") or "",
            source_snapshot={
                "selected_context_keys": context_payload.get("selected_context_keys") or [],
                "content": f"复用上下文：{context_payload.get('reuse_context_id')}"
                if context_payload.get("reuse_context")
                else (source_content or "")[:60000],
                "reuse_context": bool(context_payload.get("reuse_context")),
                "reuse_context_id": context_payload.get("reuse_context_id"),
                "role": context_payload.get("role_snapshot") or AgentRole.snapshot(
                    context_payload.get("ai_role") or cls.fixed_role),
                "historical_context": context_payload.get("historical_context") or [],
                "source_manifest": context_payload.get("source_manifest") or {},
            },
            result_snapshot={
                "task_id": task.id,
                "status": status,
                "sync_stats": sync_stats,
                "cases": cases,
                "error_message": error_message or "",
                "role": context_payload.get("role_snapshot") or AgentRole.snapshot(
                    context_payload.get("ai_role") or cls.fixed_role),
            },
            summary=(error_message or summary)[:60000],
            task=task,
            skill_snapshot=context_payload.get("skill_snapshot") or {},
            user_instruction=context_payload.get("user_instruction") or "",
            user_id=task.create_user_id,
        )

    @classmethod
    def retry(cls, task_id: int, input_patch: dict | None = None):
        task = AiAgentTask.objects.get(id=task_id, task_type=cls.task_type)
        if task.status in [
            AiAgentTaskStatusEnum.PENDING.value,
            AiAgentTaskStatusEnum.CLAIMED.value,
            AiAgentTaskStatusEnum.RUNNING.value,
            AiAgentTaskStatusEnum.WAITING_MODEL.value,
        ]:
            raise ai_service_error("当前任务正在运行中，请等待完成后再操作")
        input_data = dict(task.input_data or {})
        previous_signature = cls.retry_signature(input_data)
        previous_skill_version_id = task.skill_version_id
        input_patch = input_patch or {}
        suite = FunctionalTestQuerySelector.manual_test_suite().get(id=input_data.get("suite_id"))
        context_keys = input_patch.get("context_keys")
        if context_keys is None:
            context_keys = input_patch.get("selected_context_keys")
        current_resource_ids = input_patch.get("current_resource_ids")
        historical_context = input_patch.get("historical_context")
        if context_keys is not None or current_resource_ids is not None or historical_context is not None:
            context_payload = AgentContextService.build_functional_suite_context(
                suite,
                context_keys if context_keys is not None else input_data.get("selected_context_keys"),
                current_resource_ids=current_resource_ids
                if current_resource_ids is not None
                else input_data.get("current_resource_ids"),
                historical_context=historical_context
                if historical_context is not None
                else input_data.get("historical_context"),
            )
            input_data.update(
                {
                    "selected_context_keys": context_payload["context_keys"],
                    "context_hash": context_payload["context_hash"],
                    "reuse_context": context_payload["reuse_context"],
                    "reuse_context_id": context_payload["reuse_context_id"],
                    "preserve_case_no": FunctionalTestContextKeyEnum.PLATFORM_CASE.value in context_payload[
                        "context_keys"],
                    "current_resource_ids": context_payload.get("current_resource_ids") or [],
                    "historical_context": context_payload.get("historical_context_manifest") or [],
                    "source_manifest": context_payload.get("source_manifest") or {},
                }
            )
            input_data["context_artifact_id"] = AgentArtifactService.create(
                task,
                "functional_case_context_snapshot",
                {
                    "source_content": context_payload["ai_source_content"],
                    "requirement_context": context_payload.get("context_summary")
                    if context_payload.get("reuse_context")
                    else context_payload["selected_context"],
                    "existing_case_inventory": context_payload.get("existing_case_inventory") or "",
                    "reusable_artifacts": context_payload.get("reusable_artifacts") or {},
                    "source_manifest": context_payload.get("source_manifest") or {},
                },
                status="validated",
            ).id
        for key in ("user_instruction", "ai_role", "skill_id"):
            if key in input_patch:
                input_data[key] = input_patch.get(key)
        skill = AgentSkillService.resolve_functional_case_skill(input_data.get("skill_id") or None)
        ai_role = AgentDefinitionService.resolve_role(cls.agent_key, input_data.get("ai_role"))
        input_data["skill_id"] = skill.id if skill else None
        input_data["skill_snapshot"] = AgentSkillService.skill_snapshot(skill) if skill else {}
        input_data["ai_role"] = ai_role
        input_data["role_snapshot"] = AgentRole.snapshot(ai_role)
        next_signature = cls.retry_signature(input_data)
        if "skill_id" in input_patch:
            from src.apps.ai.services.harness.skill_version import SkillVersionService

            task.skill = skill if getattr(skill, "id", None) else None
            task.skill_version = SkillVersionService.resolve(task.skill, task.create_user_id)
        task.status = AiAgentTaskStatusEnum.PENDING.value
        task.error_message = None
        task.output_data = {}
        task.input_data = input_data
        task.input_snapshot = input_data
        task.worker_id = None
        task.lease_expires_at = None
        task.cancel_requested = False
        update_fields = ["status", "error_message", "output_data", "input_data", "input_snapshot", "worker_id",
                         "lease_expires_at", "cancel_requested", "update_time"]
        if "skill_id" in input_patch:
            update_fields.extend(["skill", "skill_version"])
        task.save(update_fields=update_fields)
        if previous_signature == next_signature and previous_skill_version_id == task.skill_version_id:
            AiAgentTaskStepService.reset_from_step(task, cls.step_defs)
        else:
            AiAgentTaskStepService.reset_steps(task, cls.step_defs)
        cls.dispatch(task.id)
        return task

    @staticmethod
    def retry_signature(input_data: dict) -> tuple:
        return (
            input_data.get("context_hash"),
            input_data.get("skill_id"),
            input_data.get("ai_role"),
            bool(input_data.get("deep_check")),
            input_data.get("user_instruction") or "",
        )

    @staticmethod
    def wait_for_critical_ambiguity_confirmation(task: AiAgentTask, requirement_model: dict) -> bool:
        confirmation = (task.input_data or {}).get("confirmation") or {}
        if str(confirmation.get("answer") or "").strip():
            return False
        critical = []
        for item in requirement_model.get("ambiguities") or []:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("severity") or "").strip().lower()
            if item.get("requires_confirmation") or severity in {"critical", "blocking"}:
                critical.append(item)
        if not critical:
            return False
        output = dict(task.output_data or {})
        output["waiting_confirmation"] = {
            "type": "requirement_ambiguity",
            "ambiguities": critical,
        }
        progress = dict(output.get("progress") or {})
        progress.update(
            {
                "stage": "等待确认",
                "detail": "需求存在会导致相反预期的关键歧义，请确认后继续",
            }
        )
        output["progress"] = progress
        task.status = AiAgentTaskStatusEnum.WAITING_CONFIRM.value
        task.output_data = output
        task.result_summary = {"waiting_confirmation": output["waiting_confirmation"]}
        task.save(update_fields=["status", "output_data", "result_summary", "update_time"])
        from src.apps.ai.services.harness.artifact import AgentEventService

        AgentEventService.emit(
            task,
            "waiting_confirmation",
            "需求存在关键歧义，等待用户确认",
            data=output["waiting_confirmation"],
            step_key="understand_requirement",
        )
        return True

    @staticmethod
    def attach_context_snapshot(task: AiAgentTask, context_payload: dict):
        artifact = AgentArtifactService.create(
            task,
            "functional_case_context_snapshot",
            {
                "source_content": context_payload["ai_source_content"],
                "requirement_context": context_payload.get("context_summary")
                if context_payload.get("reuse_context")
                else context_payload["selected_context"],
                "existing_case_inventory": context_payload.get("existing_case_inventory") or "",
                "reusable_artifacts": context_payload.get("reusable_artifacts") or {},
                "source_manifest": context_payload.get("source_manifest") or {},
            },
            status="validated",
        )
        task.input_data = {**(task.input_data or {}), "context_artifact_id": artifact.id}
        task.input_snapshot = task.input_data
        task.save(update_fields=["input_data", "input_snapshot", "update_time"])

    @staticmethod
    def load_context_snapshot(task: AiAgentTask) -> dict:
        artifact = AiAgentArtifact.objects.filter(
            id=(task.input_data or {}).get("context_artifact_id"),
            task=task,
            artifact_type="functional_case_context_snapshot",
        ).first()
        return artifact.content_json if artifact else {}

    @staticmethod
    def current_running_step(task: AiAgentTask):
        return task.aiagenttaskstep_set.filter(status=AiAgentTaskStatusEnum.RUNNING.value).order_by(
            "-update_time").first()

    @staticmethod
    def coverage_summary(parsed: dict) -> dict:
        cases = parsed.get("cases") or []
        missing_titles = [item.get("case_no") or item.get("title") for item in cases if not item.get("test_point")]
        return {
            "case_count": len(cases),
            "missing_test_point_count": len(missing_titles),
            "missing_test_point_cases": missing_titles[:20],
        }
