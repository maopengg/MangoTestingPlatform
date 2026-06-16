# -*- coding: utf-8 -*-
from src.apps.ai.agent.base import BaseAgent
from src.apps.ai.agent.context import AgentContextService
from src.apps.ai.agent.document import AgentDocumentService
from src.apps.ai.agent.functional_case.generator import FunctionalCaseGenerator
from src.apps.ai.agent.roles import AgentRole
from src.apps.ai.agent.skill.service import AgentSkillService
from src.apps.ai.agent.task_step import AiAgentTaskStepService
from src.apps.ai.models import AiAgentTask
from src.apps.ai.service.core import AiTaskService
from src.apps.functional_test.models import ManualTestSuite
from src.apps.functional_test.service.case_sync import FunctionalTestCaseSyncService
from src.apps.functional_test.service.suite import ManualTestSuiteService
from src.common.enums.ai_enum import AiAgentTaskStatusEnum, AiAgentTaskTypeEnum
from src.common.enums.manual_test_enum import FunctionalTestContextKeyEnum, ManualTestChangeStatusEnum


class FunctionalCaseAgent(BaseAgent):
    task_type = AiAgentTaskTypeEnum.MANUAL_CASE_SYNC.value
    fixed_role = AgentRole.BUSINESS_TEST_EXPERT
    step_defs = [
        {"key": "collect_context", "name": "收集上下文", "order": 1},
        {"key": "generate_cases", "name": "生成平台用例", "order": 2},
        {"key": "normalize_cases", "name": "规范化用例", "order": 4},
        {"key": "write_cases", "name": "写入平台用例", "order": 5},
        {"key": "finish_summary", "name": "生成结果汇总", "order": 6},
    ]

    @classmethod
    def start(
        cls,
        suite_id: int,
        context_keys: list | None = None,
        skill_id: int | None = None,
        ai_role: str | None = None,
        deep_check: bool = False,
        user_instruction: str = "",
        user_id: int | None = None,
    ) -> AiAgentTask:
        suite = ManualTestSuite.objects.get(id=suite_id)
        cls.ensure_no_active_task(suite.id)
        context_payload = AgentContextService.build_functional_suite_context(suite, context_keys)
        skill = AgentSkillService.resolve_functional_case_skill(skill_id)
        ai_role = AgentRole.normalize(ai_role, cls.fixed_role)
        task = cls.create_task(
            f"同步功能测试Case：{suite.requirement_name or suite.id}",
            {
                "suite_id": suite.id,
                "selected_context_keys": context_payload["context_keys"],
                "context_hash": context_payload["context_hash"],
                "reuse_context": context_payload["reuse_context"],
                "reuse_context_id": context_payload["reuse_context_id"],
                "source_url": "",
                "source_content": context_payload["ai_source_content"],
                "requirement_context": context_payload["selected_context"][:60000],
                "preserve_case_no": FunctionalTestContextKeyEnum.PLATFORM_CASE.value in context_payload["context_keys"],
                "skill_id": skill.id if skill else None,
                "skill_snapshot": AgentSkillService.skill_snapshot(skill) if skill else {},
                "ai_role": ai_role,
                "role_snapshot": AgentRole.snapshot(ai_role),
                "deep_check": bool(deep_check),
                "user_instruction": user_instruction,
            },
            user_id=user_id,
            skill=skill if getattr(skill, "id", None) else None,
        )
        if deep_check:
            AiAgentTaskStepService.create_steps(task, [{"key": "deep_patch", "name": "深度补漏", "order": 3}])
        cls.dispatch(task.id)
        return task

    @classmethod
    def run(cls, task: AiAgentTask):
        input_data = task.input_data or {}
        suite = ManualTestSuite.objects.get(id=input_data.get("suite_id"))
        try:
            AiAgentTaskStepService.start_step(task, "collect_context", input_data)
            doc = AgentDocumentService.read_document(
                input_data.get("source_url") or "",
                input_data.get("source_content") or "",
            )
            AiAgentTaskStepService.finish_step(
                task,
                "collect_context",
                {
                    "context_hash": input_data.get("context_hash"),
                    "selected_context_keys": input_data.get("selected_context_keys") or [],
                    "source_size": len(doc.get("content") or ""),
                },
            )

            skill = AgentSkillService.resolve_functional_case_skill(input_data.get("skill_id") or None)
            ai_role = AgentRole.normalize(input_data.get("ai_role"), cls.fixed_role)

            AiAgentTaskStepService.start_step(task, "generate_cases", {"source_size": len(doc.get("content") or "")})
            generated = FunctionalCaseGenerator.generate_direct_cases(
                source_content=doc["content"],
                requirement_context=input_data.get("requirement_context") or "",
                user_instruction=input_data.get("user_instruction") or "",
                skill=skill,
                ai_role=ai_role,
                task=task,
            )
            AiAgentTaskStepService.finish_step(
                task,
                "generate_cases",
                {
                    "case_count": len(generated.get("cases") or []),
                },
            )
            if input_data.get("deep_check"):
                AiAgentTaskStepService.create_steps(task, [{"key": "deep_patch", "name": "深度补漏", "order": 3}])
                AiAgentTaskStepService.start_step(task, "deep_patch")
                generated = FunctionalCaseGenerator.deep_patch_cases(
                    generated_payload=generated,
                    source_content=doc["content"],
                    requirement_context=input_data.get("requirement_context") or "",
                    user_instruction=input_data.get("user_instruction") or "",
                    skill=skill,
                    ai_role=ai_role,
                    task=task,
                )
                AiAgentTaskStepService.finish_step(task, "deep_patch", cls.coverage_summary(generated))

            AiAgentTaskStepService.start_step(task, "normalize_cases")
            normalized = FunctionalCaseGenerator.normalize(generated)
            preview = ManualTestSuiteService.sync_preview(
                suite,
                normalized,
                preserve_case_no=bool(input_data.get("preserve_case_no")),
            )
            preview["source"] = doc
            AiAgentTaskStepService.finish_step(
                task,
                "normalize_cases",
                {
                    "case_count": len(preview.get("cases") or []),
                    "validation": preview.get("validation") or {},
                },
            )

            AiAgentTaskStepService.start_step(task, "write_cases")
            FunctionalTestCaseSyncService.sync_confirm(suite, preview, task.create_user_id)
            changes = preview.get("changes") or []
            output = {
                "case_count": len(preview.get("cases") or []),
                "added_count": sum(1 for item in changes if item.get("change_status") == ManualTestChangeStatusEnum.ADDED.value),
                "changed_count": sum(1 for item in changes if item.get("change_status") == ManualTestChangeStatusEnum.CHANGED.value),
                "removed_count": sum(1 for item in changes if item.get("change_status") == ManualTestChangeStatusEnum.REMOVED.value),
                "unchanged_count": sum(1 for item in changes if item.get("change_status") == ManualTestChangeStatusEnum.UNCHANGED.value),
            }
            AiAgentTaskStepService.finish_step(task, "write_cases", output)

            AiAgentTaskStepService.start_step(task, "finish_summary")
            AiAgentTaskStepService.finish_step(task, "finish_summary", output)
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
                AiAgentTaskStepService.fail_step(task, failed_step.step_key, str(exc))
            AiTaskService.fail_task(task, str(exc))
            cls.save_generation_context(
                suite=suite,
                task=task,
                context_payload=input_data,
                summary=str(exc) or "同步功能 Case 失败",
                source_content=input_data.get("source_content") or "",
                output={},
                status=AiAgentTaskStatusEnum.FAIL.value,
                error_message=str(exc),
            )
            raise

    @classmethod
    def ensure_no_active_task(cls, suite_id: int | str, exclude_task_id: int | None = None):
        queryset = AiAgentTask.objects.filter(
            task_type=cls.task_type,
            status__in=[AiAgentTaskStatusEnum.PENDING.value, AiAgentTaskStatusEnum.RUNNING.value],
        ).order_by("-id")
        if exclude_task_id:
            queryset = queryset.exclude(id=exclude_task_id)
        for task in queryset[:200]:
            if str((task.input_data or {}).get("suite_id") or "") == str(suite_id):
                task = AiTaskService.reconcile_interrupted_task(task)
                if task.status in [AiAgentTaskStatusEnum.PENDING.value, AiAgentTaskStatusEnum.RUNNING.value]:
                    raise ValueError("当前需求已有同步任务进行中，请等待完成后再操作")

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
                "role": context_payload.get("role_snapshot") or AgentRole.snapshot(context_payload.get("ai_role") or cls.fixed_role),
            },
            result_snapshot={
                "task_id": task.id,
                "status": status,
                "sync_stats": sync_stats,
                "cases": cases,
                "error_message": error_message or "",
                "role": context_payload.get("role_snapshot") or AgentRole.snapshot(context_payload.get("ai_role") or cls.fixed_role),
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
        if task.status == AiAgentTaskStatusEnum.RUNNING.value:
            raise ValueError("当前任务正在运行中，请等待完成后再操作")
        input_data = dict(task.input_data or {})
        input_patch = input_patch or {}
        suite = ManualTestSuite.objects.get(id=input_data.get("suite_id"))
        context_keys = input_patch.get("context_keys")
        if context_keys is None:
            context_keys = input_patch.get("selected_context_keys")
        if context_keys is not None:
            context_payload = AgentContextService.build_functional_suite_context(suite, context_keys)
            input_data.update(
                {
                    "selected_context_keys": context_payload["context_keys"],
                    "context_hash": context_payload["context_hash"],
                    "reuse_context": context_payload["reuse_context"],
                    "reuse_context_id": context_payload["reuse_context_id"],
                    "source_content": context_payload["ai_source_content"],
                    "requirement_context": context_payload["selected_context"][:60000],
                    "preserve_case_no": FunctionalTestContextKeyEnum.PLATFORM_CASE.value in context_payload["context_keys"],
                }
            )
        for key in ("user_instruction", "ai_role", "skill_id"):
            if key in input_patch:
                input_data[key] = input_patch.get(key)
        skill = AgentSkillService.resolve_functional_case_skill(input_data.get("skill_id") or None)
        ai_role = AgentRole.normalize(input_data.get("ai_role"), cls.fixed_role)
        input_data["skill_id"] = skill.id if skill else None
        input_data["skill_snapshot"] = AgentSkillService.skill_snapshot(skill) if skill else {}
        input_data["ai_role"] = ai_role
        input_data["role_snapshot"] = AgentRole.snapshot(ai_role)
        task.status = AiAgentTaskStatusEnum.RUNNING.value
        task.error_message = None
        task.output_data = {}
        task.input_data = input_data
        task.save(update_fields=["status", "error_message", "output_data", "input_data", "update_time"])
        AiAgentTaskStepService.reset_steps(task, cls.step_defs)
        cls.dispatch(task.id)
        return task

    @staticmethod
    def current_running_step(task: AiAgentTask):
        return task.aiagenttaskstep_set.filter(status=AiAgentTaskStatusEnum.RUNNING.value).order_by("-update_time").first()

    @staticmethod
    def coverage_summary(parsed: dict) -> dict:
        cases = parsed.get("cases") or []
        missing_titles = [item.get("case_no") or item.get("title") for item in cases if not item.get("test_point")]
        return {
            "case_count": len(cases),
            "missing_test_point_count": len(missing_titles),
            "missing_test_point_cases": missing_titles[:20],
        }
