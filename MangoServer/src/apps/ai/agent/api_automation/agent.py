# -*- coding: utf-8 -*-
from src.apps.ai.agent.api_automation.executor import ApiAutomationExecutor
from src.apps.ai.agent.base import BaseAgent
from src.apps.ai.agent.context import AgentContextService
from src.apps.ai.agent.roles import AgentRole
from src.apps.ai.agent.skill.service import AgentSkillService
from src.apps.ai.agent.task_step import AiAgentTaskStepService
from src.apps.ai.models import AiAgentTask, AiMcpServer
from src.apps.ai.service.core import AiTaskService
from src.apps.functional_test.models import ManualTestAutomationBinding, ManualTestCase, ManualTestSuite
from src.apps.functional_test.service.automation import ManualAutomationService
from src.common.enums.ai_enum import AiAgentTaskStatusEnum, AiAgentTaskTypeEnum, AiSkillTypeEnum
from src.common.enums.manual_test_enum import ManualTestAutomationTypeEnum, ManualTestTypeEnum


class ApiAutomationAgent(BaseAgent):
    task_type = AiAgentTaskTypeEnum.GENERATE_API_CASE.value
    fixed_role = AgentRole.API_AUTOMATION_EXPERT
    active_statuses = [AiAgentTaskStatusEnum.PENDING.value, AiAgentTaskStatusEnum.RUNNING.value]
    step_defs = [
        {"key": "collect_context", "name": "收集上下文", "order": 1},
        {"key": "load_manual_case", "name": "读取功能用例", "order": 2},
        {"key": "load_skill", "name": "加载技能", "order": 3},
        {"key": "load_mcp_tools", "name": "加载 MCP 工具", "order": 4},
        {"key": "plan_api_case", "name": "规划 API 自动化", "order": 5},
        {"key": "execute_mcp_tools", "name": "执行 MCP 工具链", "order": 6},
        {"key": "validate_result", "name": "校验生成结果", "order": 7},
        {"key": "bind_result", "name": "回填自动化绑定", "order": 8},
        {"key": "run_api_case", "name": "执行 API Case", "order": 9},
        {"key": "finish_summary", "name": "生成结果汇总", "order": 10},
    ]

    @classmethod
    def start(
        cls,
        manual_case_id: int | None = None,
        suite_id: int | None = None,
        manual_case_ids: list | None = None,
        scope: str | None = None,
        context_keys: list | None = None,
        skill_id: int | None = None,
        mcp_server_ids: list | None = None,
        ai_role: str | None = None,
        user_instruction: str = "",
        user_id: int | None = None,
    ) -> AiAgentTask:
        if manual_case_ids or scope:
            return cls.start_batch(
                suite_id=suite_id,
                manual_case_ids=manual_case_ids,
                scope=scope,
                context_keys=context_keys,
                skill_id=skill_id,
                mcp_server_ids=mcp_server_ids,
                ai_role=ai_role,
                user_instruction=user_instruction,
                user_id=user_id,
            )
        if not manual_case_id:
            raise ValueError("请选择要生成API自动化的功能用例")
        manual_case = ManualTestCase.objects.select_related("suite", "project_product", "module").get(id=manual_case_id)
        if ManualTestTypeEnum.API.value not in (manual_case.test_types or []):
            raise ValueError("当前用例未开启API自动化测试类型")
        if not skill_id:
            raise ValueError("生成API自动化必须选择技能")
        selected_mcp_server_ids = cls.normalize_mcp_server_ids(mcp_server_ids)
        if not selected_mcp_server_ids:
            raise ValueError("生成API自动化必须选择MCP服务")
        active_task = cls.find_active_task(manual_case.id)
        if active_task:
            raise ValueError("当前功能用例已有API自动化生成任务进行中，请等待完成后再操作")
        skill = AgentSkillService.get_skill(skill_id=skill_id)
        if not skill:
            raise ValueError("选择的技能不存在或未发布")
        if skill.skill_type != AiSkillTypeEnum.API_AUTOMATION.value:
            raise ValueError("生成API自动化只能选择API自动化类型的技能")
        mcp_servers = list(AiMcpServer.objects.filter(id__in=selected_mcp_server_ids))
        if not mcp_servers:
            raise ValueError("选择的MCP服务不存在或已停用")
        selected_role = AgentRole.normalize(ai_role, cls.fixed_role)
        context_package = AgentContextService.build_api_context_package(manual_case.suite, context_keys)
        existing = ManualTestAutomationBinding.objects.filter(
            manual_case=manual_case,
            automation_type=ManualTestAutomationTypeEnum.API.value,
        ).first()
        task = cls.create_task(
            f"生成API自动化：{manual_case.title}",
            {
                "suite_id": manual_case.suite_id,
                "manual_case_id": manual_case.id,
                "manual_case_snapshot": cls.manual_case_snapshot(manual_case),
                "existing_api_case_id": existing.api_case_id if existing else None,
                "selected_context_keys": context_package["context_keys"],
                "context_hash": context_package["context_hash"],
                "reuse_context": context_package["reuse_context"],
                "reuse_context_id": context_package["reuse_context_id"],
                "skill_id": skill.id,
                "skill_snapshot": AgentSkillService.skill_snapshot(skill),
                "mcp_server_ids": [server.id for server in mcp_servers],
                "mcp_server_names": [server.name for server in mcp_servers],
                "mcp_server_prompts": {server.id: server.prompt or "" for server in mcp_servers},
                "ai_role": selected_role,
                "role_snapshot": AgentRole.snapshot(selected_role),
                "user_instruction": user_instruction,
            },
            user_id=user_id,
            skill=skill,
        )
        cls.dispatch(task.id)
        return task

    @classmethod
    def start_batch(
        cls,
        suite_id: int | None = None,
        manual_case_ids: list | None = None,
        scope: str | None = None,
        context_keys: list | None = None,
        skill_id: int | None = None,
        mcp_server_ids: list | None = None,
        ai_role: str | None = None,
        user_instruction: str = "",
        user_id: int | None = None,
    ) -> AiAgentTask:
        if not suite_id and not manual_case_ids:
            raise ValueError("请选择要批量生成API自动化的需求或功能用例")
        if not skill_id:
            raise ValueError("生成API自动化必须选择技能")
        selected_mcp_server_ids = cls.normalize_mcp_server_ids(mcp_server_ids)
        if not selected_mcp_server_ids:
            raise ValueError("生成API自动化必须选择MCP服务")
        skill = AgentSkillService.get_skill(skill_id=skill_id)
        if not skill:
            raise ValueError("选择的技能不存在或未发布")
        if skill.skill_type != AiSkillTypeEnum.API_AUTOMATION.value:
            raise ValueError("生成API自动化只能选择API自动化类型的技能")
        mcp_servers = list(AiMcpServer.objects.filter(id__in=selected_mcp_server_ids))
        if not mcp_servers:
            raise ValueError("选择的MCP服务不存在或已停用")

        suite, manual_cases = cls.resolve_batch_cases(suite_id=suite_id, manual_case_ids=manual_case_ids, scope=scope)
        if not manual_cases:
            raise ValueError("当前需求暂无可生成API自动化的用例")
        active_batch = cls.find_active_suite_batch_task(suite.id)
        if active_batch:
            raise ValueError("当前需求已有批量API自动化生成任务进行中，请等待完成后再操作")
        active_case = next((case for case in manual_cases if cls.find_active_task(case.id)), None)
        if active_case:
            raise ValueError(f"功能用例 {active_case.case_no or active_case.id} 已有API自动化生成任务进行中，请等待完成后再操作")

        selected_role = AgentRole.normalize(ai_role, cls.fixed_role)
        context_package = AgentContextService.build_api_context_package(suite, context_keys)
        api_bindings = {
            item.manual_case_id: item
            for item in ManualTestAutomationBinding.objects.filter(
                manual_case_id__in=[case.id for case in manual_cases],
                automation_type=ManualTestAutomationTypeEnum.API.value,
            )
        }
        manual_case_snapshots = []
        for case in manual_cases:
            snapshot = cls.manual_case_snapshot(case)
            existing = api_bindings.get(case.id)
            snapshot["existing_api_case_id"] = existing.api_case_id if existing else None
            manual_case_snapshots.append(snapshot)
        task = cls.create_task(
            f"批量生成API自动化：{suite.requirement_name or suite.id}",
            {
                "mode": "batch",
                "suite_id": suite.id,
                "scope": scope or "",
                "manual_case_ids": [case.id for case in manual_cases],
                "manual_case_snapshots": manual_case_snapshots,
                "selected_context_keys": context_package["context_keys"],
                "context_hash": context_package["context_hash"],
                "reuse_context": context_package["reuse_context"],
                "reuse_context_id": context_package["reuse_context_id"],
                "skill_id": skill.id,
                "skill_snapshot": AgentSkillService.skill_snapshot(skill),
                "mcp_server_ids": [server.id for server in mcp_servers],
                "mcp_server_names": [server.name for server in mcp_servers],
                "mcp_server_prompts": {server.id: server.prompt or "" for server in mcp_servers},
                "ai_role": selected_role,
                "role_snapshot": AgentRole.snapshot(selected_role),
                "user_instruction": user_instruction,
                "batch_summary": cls.batch_summary(manual_case_snapshots),
            },
            user_id=user_id,
            skill=skill,
        )
        cls.dispatch(task.id)
        return task

    @staticmethod
    def manual_case_snapshot(manual_case: ManualTestCase) -> dict:
        return {
            "id": manual_case.id,
            "case_no": manual_case.case_no,
            "title": manual_case.title,
            "test_point": manual_case.test_point,
        }

    @classmethod
    def run(cls, task: AiAgentTask):
        input_data = task.input_data or {}
        if input_data.get("mode") == "batch":
            return cls.run_batch(task)
        manual_case = ManualTestCase.objects.select_related("suite", "project_product", "module").get(id=input_data.get("manual_case_id"))
        suite = manual_case.suite
        context_package = AgentContextService.build_api_context_package(
            suite,
            input_data.get("selected_context_keys") or None,
        )
        skill = AgentSkillService.get_skill(skill_id=input_data.get("skill_id") or None)
        mcp_servers = list(AiMcpServer.objects.filter(id__in=input_data.get("mcp_server_ids") or []))
        try:
            AiAgentTaskStepService.start_step(task, "collect_context", {"selected_context_keys": context_package["context_keys"]})
            AiAgentTaskStepService.finish_step(
                task,
                "collect_context",
                {
                    "context_hash": context_package["context_hash"],
                    "reuse_context": context_package["reuse_context"],
                    "reuse_context_id": context_package["reuse_context_id"],
                },
            )
            AiAgentTaskStepService.start_step(task, "load_manual_case")
            AiAgentTaskStepService.finish_step(task, "load_manual_case", {"manual_case_id": manual_case.id, "title": manual_case.title})
            AiAgentTaskStepService.start_step(task, "load_skill")
            if not skill:
                raise ValueError("选择的技能不存在或未发布")
            if skill.skill_type != AiSkillTypeEnum.API_AUTOMATION.value:
                raise ValueError("生成API自动化只能选择API自动化类型的技能")
            AiAgentTaskStepService.finish_step(task, "load_skill", AgentSkillService.skill_snapshot(skill))
            AiAgentTaskStepService.start_step(task, "load_mcp_tools")
            if not mcp_servers:
                raise ValueError("选择的MCP服务不存在或已停用")
            AiAgentTaskStepService.finish_step(
                task,
                "load_mcp_tools",
                {
                    "mcp_server_ids": [server.id for server in mcp_servers],
                    "mcp_server_names": [server.name for server in mcp_servers],
                    "mcp_server_prompts": {server.id: server.prompt or "" for server in mcp_servers},
                },
            )
            AiAgentTaskStepService.start_step(task, "plan_api_case")
            AiAgentTaskStepService.update_step(task, "plan_api_case", 40, {"message": "AI 正在根据 Skill 规划 MCP 工具链"})
            AiAgentTaskStepService.start_step(task, "execute_mcp_tools")
            plan = ApiAutomationExecutor.execute(
                task=task,
                manual_case=manual_case,
                suite=suite,
                skill=skill,
                mcp_servers=mcp_servers,
                context_package=context_package,
                existing_api_case_id=input_data.get("existing_api_case_id") or None,
                ai_role=input_data.get("ai_role") or cls.fixed_role,
                user_instruction=input_data.get("user_instruction") or "",
                user_id=task.create_user_id,
            )
            AiAgentTaskStepService.finish_step(task, "plan_api_case", {"api_case_id": plan.get("api_case_id")})
            AiAgentTaskStepService.finish_step(task, "execute_mcp_tools", {"tool_call_count": len(plan.get("tool_calls") or [])})
            AiAgentTaskStepService.start_step(task, "validate_result")
            AiAgentTaskStepService.finish_step(
                task,
                "validate_result",
                {"api_case_id": plan.get("api_case_id"), "assertion_summary": plan.get("assertion_summary") or {}},
            )
            AiAgentTaskStepService.start_step(task, "bind_result")
            AiAgentTaskStepService.finish_step(task, "bind_result", {"binding_id": plan.get("binding_id")})
            AiAgentTaskStepService.start_step(task, "run_api_case")
            AiAgentTaskStepService.finish_step(task, "run_api_case", {"executed": True})
            AiAgentTaskStepService.start_step(task, "finish_summary")
            AiAgentTaskStepService.finish_step(task, "finish_summary", plan)
            AiTaskService.finish_task(task, plan)
            cls.save_generation_context(
                suite=suite,
                manual_case=manual_case,
                task_snapshot=cls.task_snapshot(task),
                context_package=context_package,
                selected_context_keys=context_package["context_keys"],
                plan=plan,
                user_id=task.create_user_id,
                status=AiAgentTaskStatusEnum.SUCCESS.value,
                user_instruction=input_data.get("user_instruction") or "",
            )
        except Exception as exc:
            running = task.aiagenttaskstep_set.filter(status=AiAgentTaskStatusEnum.RUNNING.value).order_by("-update_time").first()
            if running:
                AiAgentTaskStepService.fail_step(task, running.step_key, str(exc))
            AiTaskService.fail_task(task, str(exc))
            if skill:
                cls.save_generation_context(
                    suite=suite,
                    manual_case=manual_case,
                    task_snapshot=cls.task_snapshot(task),
                    context_package=context_package,
                    selected_context_keys=context_package["context_keys"],
                    plan={"task_id": task.id, "tool_calls": [], "diff_summary": "生成 API Case 失败"},
                    user_id=task.create_user_id,
                    status=AiAgentTaskStatusEnum.FAIL.value,
                    user_instruction=input_data.get("user_instruction") or "",
                    error_message=str(exc),
                )
            raise

    @classmethod
    def run_batch(cls, task: AiAgentTask):
        input_data = task.input_data or {}
        suite_id = input_data.get("suite_id")
        suite = ManualTestSuite.objects.get(id=suite_id)
        manual_case_ids = input_data.get("manual_case_ids") or []
        execute_case_ids = input_data.get("retry_pending_case_ids") or manual_case_ids
        manual_cases = list(ManualTestCase.objects.select_related("suite", "project_product", "module").filter(id__in=manual_case_ids, suite_id=suite.id))
        case_map = {case.id: case for case in manual_cases}
        ordered_cases = [case_map[case_id] for case_id in manual_case_ids if case_id in case_map]
        execute_cases = [case_map[case_id] for case_id in execute_case_ids if case_id in case_map]
        if not ordered_cases:
            raise ValueError("批量API自动化任务中的用例已不存在，请重新选择后再生成")
        if not execute_cases:
            raise ValueError("批量API自动化任务中没有需要继续生成的用例")
        context_package = AgentContextService.build_api_context_package(suite, input_data.get("selected_context_keys") or None)
        skill = AgentSkillService.get_skill(skill_id=input_data.get("skill_id") or None)
        mcp_servers = list(AiMcpServer.objects.filter(id__in=input_data.get("mcp_server_ids") or []))
        items = cls.build_batch_items(input_data, ordered_cases)
        execute_case_id_set = {case.id for case in execute_cases}
        for item in items:
            if item.get("manual_case_id") in execute_case_id_set and item.get("status") != "success":
                item["status"] = "pending"
                item.pop("error_message", None)
                item["summary"] = "等待继续生成"
        success_count = len([item for item in items if item.get("status") == "success"])
        fail_count = 0
        try:
            AiAgentTaskStepService.start_step(task, "collect_context", {"selected_context_keys": context_package["context_keys"]})
            AiAgentTaskStepService.finish_step(
                task,
                "collect_context",
                {
                    "context_hash": context_package["context_hash"],
                    "reuse_context": context_package["reuse_context"],
                    "reuse_context_id": context_package["reuse_context_id"],
                },
            )
            AiAgentTaskStepService.start_step(task, "load_manual_case")
            AiAgentTaskStepService.finish_step(task, "load_manual_case", {"total": len(ordered_cases), "execute_total": len(execute_cases)})
            AiAgentTaskStepService.start_step(task, "load_skill")
            if not skill:
                raise ValueError("选择的技能不存在或未发布")
            if skill.skill_type != AiSkillTypeEnum.API_AUTOMATION.value:
                raise ValueError("生成API自动化只能选择API自动化类型的技能")
            AiAgentTaskStepService.finish_step(task, "load_skill", AgentSkillService.skill_snapshot(skill))
            AiAgentTaskStepService.start_step(task, "load_mcp_tools")
            if not mcp_servers:
                raise ValueError("选择的MCP服务不存在或已停用")
            AiAgentTaskStepService.finish_step(
                task,
                "load_mcp_tools",
                {
                    "mcp_server_ids": [server.id for server in mcp_servers],
                    "mcp_server_names": [server.name for server in mcp_servers],
                    "mcp_server_prompts": {server.id: server.prompt or "" for server in mcp_servers},
                },
            )
            AiAgentTaskStepService.start_step(task, "execute_mcp_tools")
            cls.update_batch_progress(task, items, success_count + fail_count, success_count, fail_count, f"批量任务已开始，待处理 {len(execute_cases)} 条用例")
            bindings = {
                item.manual_case_id: item
                for item in ManualTestAutomationBinding.objects.filter(
                    manual_case_id__in=[case.id for case in execute_cases],
                    automation_type=ManualTestAutomationTypeEnum.API.value,
                )
            }
            item_map = {item.get("manual_case_id"): item for item in items}
            for index, manual_case in enumerate(execute_cases, start=1):
                item = item_map.get(manual_case.id)
                if not item:
                    continue
                item["status"] = "running"
                cls.update_batch_progress(
                    task,
                    items,
                    success_count + fail_count + 1,
                    success_count,
                    fail_count,
                    f"正在处理 {index}/{len(execute_cases)}：{manual_case.case_no} / {manual_case.title}",
                )
                try:
                    existing = bindings.get(manual_case.id)
                    plan = ApiAutomationExecutor.execute(
                        task=task,
                        manual_case=manual_case,
                        suite=suite,
                        skill=skill,
                        mcp_servers=mcp_servers,
                        context_package=context_package,
                        existing_api_case_id=existing.api_case_id if existing else None,
                        ai_role=input_data.get("ai_role") or cls.fixed_role,
                        user_instruction=input_data.get("user_instruction") or "",
                        user_id=task.create_user_id,
                    )
                    item.update(
                        {
                            "status": "success",
                            "api_case_id": plan.get("api_case_id"),
                            "binding_id": plan.get("binding_id"),
                            "summary": plan.get("diff_summary") or "已生成并执行一次",
                        }
                    )
                    success_count += 1
                except Exception as exc:
                    item.update({"status": "fail", "error_message": str(exc)[:1000], "summary": "生成失败"})
                    fail_count += 1
                cls.update_batch_progress(
                    task,
                    items,
                    success_count + fail_count,
                    success_count,
                    fail_count,
                    f"已处理 {index}/{len(execute_cases)}：成功 {success_count}，失败 {fail_count}",
                )
            AiAgentTaskStepService.finish_step(task, "execute_mcp_tools", {"success_count": success_count, "fail_count": fail_count, "total": len(ordered_cases)})
            AiAgentTaskStepService.start_step(task, "finish_summary")
            output = cls.batch_output(task, items, len(ordered_cases), success_count, fail_count)
            status = (
                AiAgentTaskStatusEnum.SUCCESS.value
                if success_count == len(ordered_cases)
                else AiAgentTaskStatusEnum.PARTIAL_SUCCESS.value
                if success_count
                else AiAgentTaskStatusEnum.FAIL.value
            )
            AiAgentTaskStepService.finish_step(task, "finish_summary", output)
            if status == AiAgentTaskStatusEnum.FAIL.value:
                AiTaskService.fail_task(task, "批量生成API自动化全部失败", output)
            else:
                AiTaskService.finish_task(task, output, status=status)
            cls.save_batch_generation_context(
                suite=suite,
                task_snapshot=cls.task_snapshot(task),
                context_package=context_package,
                selected_context_keys=context_package["context_keys"],
                output=output,
                user_id=task.create_user_id,
                status=status,
                user_instruction=input_data.get("user_instruction") or "",
            )
        except Exception as exc:
            running = task.aiagenttaskstep_set.filter(status=AiAgentTaskStatusEnum.RUNNING.value).order_by("-update_time").first()
            if running:
                AiAgentTaskStepService.fail_step(task, running.step_key, str(exc))
            output = cls.batch_output(task, items, 0, success_count, fail_count)
            AiTaskService.fail_task(task, str(exc), output)
            cls.save_batch_generation_context(
                suite=suite,
                task_snapshot=cls.task_snapshot(task),
                context_package=context_package,
                selected_context_keys=context_package["context_keys"],
                output=output,
                user_id=task.create_user_id,
                status=AiAgentTaskStatusEnum.FAIL.value,
                user_instruction=input_data.get("user_instruction") or "",
                error_message=str(exc),
            )
            raise

    @staticmethod
    def task_snapshot(task: AiAgentTask) -> dict:
        return {
            "id": task.id,
            "status": task.status,
            "input_data": task.input_data or {},
            "output_data": task.output_data or {},
            "error_message": task.error_message or "",
        }

    @staticmethod
    def save_generation_context(
        suite,
        manual_case,
        task_snapshot: dict,
        context_package: dict,
        selected_context_keys: list[int],
        plan: dict,
        user_id: int | None,
        status: int,
        user_instruction: str = "",
        error_message: str = "",
    ):
        task = AiAgentTask.objects.filter(id=task_snapshot.get("id")).first()
        AgentContextService.save_context(
            suite_id=suite.id,
            manual_case_id=manual_case.id,
            context_type="api_case_plan",
            context_hash=context_package["context_hash"],
            source_snapshot={
                "selected_context_keys": selected_context_keys,
                "content": f"复用上下文：{context_package['reuse_context_id']}"
                if context_package.get("reuse_context")
                else (context_package.get("context_text") or "")[:60000],
                "reuse_context": context_package.get("reuse_context"),
                "reuse_context_id": context_package.get("reuse_context_id"),
                "role": task_snapshot.get("input_data", {}).get("role_snapshot") or AgentRole.snapshot(task_snapshot.get("input_data", {}).get("ai_role") or ApiAutomationAgent.fixed_role),
            },
            result_snapshot={
                "task_id": task_snapshot.get("id"),
                "context_hash": context_package.get("context_hash"),
                "mcp_server_ids": plan.get("mcp_server_ids") or [],
                "mcp_server_names": plan.get("mcp_server_names") or [],
                "mcp_server_prompts": plan.get("mcp_server_prompts") or {},
                "ai_role": plan.get("ai_role") or "api_automation_expert",
                "role": task_snapshot.get("input_data", {}).get("role_snapshot") or AgentRole.snapshot(task_snapshot.get("input_data", {}).get("ai_role") or ApiAutomationAgent.fixed_role),
                "tool_calls": plan.get("tool_calls") or [],
                "plan": plan,
                "case_title": manual_case.title,
                "case_no": manual_case.case_no,
                "status": status,
            },
            summary=(error_message or plan.get("diff_summary") or "")[:60000],
            task=task,
            skill_snapshot=task_snapshot.get("input_data", {}).get("skill_snapshot") or {},
            mcp_snapshot={
                "mcp_server_ids": plan.get("mcp_server_ids") or [],
                "mcp_server_names": plan.get("mcp_server_names") or [],
                "mcp_server_prompts": plan.get("mcp_server_prompts") or {},
            },
            user_instruction=user_instruction or "",
            user_id=user_id,
        )

    @staticmethod
    def save_batch_generation_context(
        suite,
        task_snapshot: dict,
        context_package: dict,
        selected_context_keys: list[int],
        output: dict,
        user_id: int | None,
        status: int,
        user_instruction: str = "",
        error_message: str = "",
    ):
        task = AiAgentTask.objects.filter(id=task_snapshot.get("id")).first()
        input_data = task_snapshot.get("input_data") or {}
        summary = error_message or f"批量生成API自动化完成：成功 {output.get('success_count', 0)}，失败 {output.get('fail_count', 0)}，共 {output.get('total', 0)}"
        AgentContextService.save_context(
            suite_id=suite.id,
            manual_case_id=None,
            context_type="api_case_plan",
            context_hash=context_package["context_hash"],
            source_snapshot={
                "selected_context_keys": selected_context_keys,
                "content": f"复用上下文：{context_package['reuse_context_id']}"
                if context_package.get("reuse_context")
                else (context_package.get("context_text") or "")[:60000],
                "reuse_context": context_package.get("reuse_context"),
                "reuse_context_id": context_package.get("reuse_context_id"),
                "role": input_data.get("role_snapshot") or AgentRole.snapshot(input_data.get("ai_role") or ApiAutomationAgent.fixed_role),
            },
            result_snapshot={
                "mode": "batch",
                "task_id": task_snapshot.get("id"),
                "context_hash": context_package.get("context_hash"),
                "mcp_server_ids": input_data.get("mcp_server_ids") or [],
                "mcp_server_names": input_data.get("mcp_server_names") or [],
                "mcp_server_prompts": input_data.get("mcp_server_prompts") or {},
                "ai_role": input_data.get("ai_role") or "api_automation_expert",
                "role": input_data.get("role_snapshot") or AgentRole.snapshot(input_data.get("ai_role") or ApiAutomationAgent.fixed_role),
                "items": output.get("items") or [],
                "total": output.get("total") or 0,
                "success_count": output.get("success_count") or 0,
                "fail_count": output.get("fail_count") or 0,
                "status": status,
            },
            summary=summary[:60000],
            task=task,
            skill_snapshot=input_data.get("skill_snapshot") or {},
            mcp_snapshot={
                "mcp_server_ids": input_data.get("mcp_server_ids") or [],
                "mcp_server_names": input_data.get("mcp_server_names") or [],
                "mcp_server_prompts": input_data.get("mcp_server_prompts") or {},
            },
            user_instruction=user_instruction or "",
            user_id=user_id,
        )

    @classmethod
    def retry(cls, task_id: int, input_patch: dict | None = None):
        task = AiAgentTask.objects.get(id=task_id, task_type=cls.task_type)
        if task.status == AiAgentTaskStatusEnum.RUNNING.value:
            raise ValueError("当前任务正在运行中，请等待完成后再操作")
        input_data = dict(task.input_data or {})
        previous_output_data = dict(task.output_data or {})
        if input_patch:
            input_data.update(input_patch)
        input_data["ai_role"] = AgentRole.normalize(input_data.get("ai_role"), cls.fixed_role)
        input_data["role_snapshot"] = AgentRole.snapshot(input_data["ai_role"])
        if input_data.get("mode") == "batch":
            cls.prepare_batch_continue_input(input_data, previous_output_data)
        if input_patch and "skill_id" in input_patch:
            skill = AgentSkillService.get_skill(skill_id=input_data.get("skill_id") or None)
            if skill and skill.skill_type != AiSkillTypeEnum.API_AUTOMATION.value:
                raise ValueError("生成API自动化只能选择API自动化类型的技能")
            input_data["skill_snapshot"] = AgentSkillService.skill_snapshot(skill) if skill else {}
        task.input_data = input_data
        task.status = AiAgentTaskStatusEnum.RUNNING.value
        task.error_message = None
        task.output_data = {}
        task.save(update_fields=["input_data", "status", "error_message", "output_data", "update_time"])
        AiAgentTaskStepService.reset_steps(task, cls.step_defs)
        cls.dispatch(task.id)
        return task

    @staticmethod
    def prepare_batch_continue_input(input_data: dict, previous_output_data: dict):
        previous_items = previous_output_data.get("items") or []
        if not previous_items:
            input_data.pop("retry_pending_case_ids", None)
            input_data.pop("previous_batch_items", None)
            return
        pending_case_ids = [
            item.get("manual_case_id")
            for item in previous_items
            if item.get("manual_case_id") and item.get("status") != "success"
        ]
        if not pending_case_ids:
            raise ValueError("当前批量任务已全部成功，无需继续生成")
        input_data["retry_pending_case_ids"] = pending_case_ids
        input_data["previous_batch_items"] = previous_items

    @classmethod
    def find_active_task(cls, manual_case_id: int) -> AiAgentTask | None:
        queryset = AiAgentTask.objects.filter(
            task_type=cls.task_type,
            status__in=cls.active_statuses,
        ).order_by("-id")
        for task in queryset[:200]:
            input_data = task.input_data or {}
            is_same_single = input_data.get("manual_case_id") == manual_case_id
            is_same_batch = input_data.get("mode") == "batch" and manual_case_id in (input_data.get("manual_case_ids") or [])
            if is_same_single or is_same_batch:
                task = AiTaskService.reconcile_interrupted_task(task)
                if task.status in cls.active_statuses:
                    return task
        return None

    @classmethod
    def find_active_suite_batch_task(cls, suite_id: int) -> AiAgentTask | None:
        queryset = AiAgentTask.objects.filter(
            task_type=cls.task_type,
            status__in=cls.active_statuses,
        ).order_by("-id")
        for task in queryset[:200]:
            input_data = task.input_data or {}
            if input_data.get("mode") == "batch" and str(input_data.get("suite_id") or "") == str(suite_id):
                task = AiTaskService.reconcile_interrupted_task(task)
                if task.status in cls.active_statuses:
                    return task
        return None

    @classmethod
    def resolve_batch_cases(cls, suite_id: int | None = None, manual_case_ids: list | None = None, scope: str | None = None):
        normalized_ids = cls.normalize_manual_case_ids(manual_case_ids)
        queryset = ManualTestCase.objects.select_related("suite", "project_product", "module")
        if normalized_ids:
            cases = list(queryset.filter(id__in=normalized_ids))
            case_map = {case.id: case for case in cases}
            cases = [case_map[case_id] for case_id in normalized_ids if case_id in case_map]
            cases = [case for case in cases if ManualTestTypeEnum.API.value in (case.test_types or [])]
            suite_ids = {case.suite_id for case in cases}
            if suite_id:
                cases = [case for case in cases if str(case.suite_id) == str(suite_id)]
                suite_ids = {case.suite_id for case in cases}
            if len(suite_ids) > 1:
                raise ValueError("批量生成API自动化只能选择同一个需求下的用例")
            if not cases:
                raise ValueError("当前选择中没有可生成API自动化的用例")
            return cases[0].suite, cases
        if not suite_id:
            raise ValueError("请选择要批量生成API自动化的需求")
        cases_queryset = queryset.filter(suite_id=suite_id, test_types__contains=[ManualTestTypeEnum.API.value]).order_by("id")
        if scope == "unbound_api_cases":
            bound_case_ids = ManualTestAutomationBinding.objects.filter(
                manual_case__suite_id=suite_id,
                automation_type=ManualTestAutomationTypeEnum.API.value,
            ).values_list("manual_case_id", flat=True)
            cases_queryset = cases_queryset.exclude(id__in=bound_case_ids)
        cases = list(cases_queryset)
        if not cases:
            suite = ManualTestSuite.objects.filter(id=suite_id).first()
            if suite:
                return suite, []
            raise ValueError("当前需求暂无可生成API自动化的用例")
        return cases[0].suite, cases

    @staticmethod
    def normalize_manual_case_ids(values: list | tuple | None = None) -> list[int]:
        if values is None:
            return []
        if not isinstance(values, (list, tuple, set)):
            values = [values]
        normalized = []
        for value in values:
            try:
                case_id = int(value)
            except (TypeError, ValueError):
                continue
            if case_id and case_id not in normalized:
                normalized.append(case_id)
        return normalized

    @staticmethod
    def batch_summary(manual_case_snapshots: list[dict]) -> dict:
        total = len(manual_case_snapshots)
        bound_count = len([item for item in manual_case_snapshots if item.get("existing_api_case_id")])
        return {
            "total": total,
            "unbound_count": total - bound_count,
            "bound_count": bound_count,
        }

    @staticmethod
    def build_batch_items(input_data: dict, ordered_cases: list[ManualTestCase]) -> list[dict]:
        previous_items = {
            item.get("manual_case_id"): item
            for item in input_data.get("previous_batch_items") or []
            if item.get("manual_case_id")
        }
        snapshots = input_data.get("manual_case_snapshots") or []
        snapshot_map = {item.get("id"): item for item in snapshots if item.get("id")}
        items = []
        for case in ordered_cases:
            previous = previous_items.get(case.id)
            if previous:
                items.append(
                    {
                        **previous,
                        "manual_case_id": case.id,
                        "case_no": case.case_no,
                        "title": case.title,
                    }
                )
                continue
            snapshot = snapshot_map.get(case.id) or {}
            items.append(
                {
                    "manual_case_id": case.id,
                    "case_no": case.case_no,
                    "title": case.title,
                    "status": "pending",
                    "api_case_id": snapshot.get("existing_api_case_id"),
                }
            )
        return items

    @staticmethod
    def batch_output(task: AiAgentTask, items: list[dict], current_index: int, success_count: int, fail_count: int) -> dict:
        input_data = task.input_data or {}
        return {
            "mode": "batch",
            "suite_id": input_data.get("suite_id"),
            "total": len(items),
            "current_index": current_index,
            "success_count": success_count,
            "fail_count": fail_count,
            "items": items,
        }

    @classmethod
    def update_batch_progress(
        cls,
        task: AiAgentTask,
        items: list[dict],
        current_index: int,
        success_count: int,
        fail_count: int,
        detail: str,
    ):
        output = cls.batch_output(task, items, current_index, success_count, fail_count)
        task.output_data = {**(task.output_data or {}), **output}
        task.save(update_fields=["output_data", "update_time"])
        total = max(len(items), 1)
        percent = min(95, 10 + int((current_index / total) * 80))
        AiTaskService.update_progress(
            task,
            percent,
            "批量生成 API 自动化",
            detail,
            {
                "mode": "batch",
                "current_index": current_index,
                "total": len(items),
                "success_count": success_count,
                "fail_count": fail_count,
            },
        )

    @staticmethod
    def normalize_mcp_server_ids(values: list | tuple | None = None) -> list[int]:
        if values is None:
            values = []
        if not isinstance(values, (list, tuple, set)):
            values = [values]
        normalized = []
        for value in values:
            try:
                server_id = int(value)
            except (TypeError, ValueError):
                continue
            if server_id and server_id not in normalized:
                normalized.append(server_id)
        return normalized
