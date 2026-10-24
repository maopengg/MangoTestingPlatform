# -*- coding: utf-8 -*-
from src.apps.ai.enums import AiSkillTypeEnum
from src.apps.ai.enums.role import AgentRole
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentTask, AiAgentTaskItem, AiMcpServer
from src.apps.ai.services.agent.context import AgentContextService
from src.apps.ai.services.harness.definition import AgentDefinitionService
from src.apps.ai.services.skill.service import AgentSkillService
from src.apps.functional_test.enums import ManualTestAutomationTypeEnum, ManualTestTypeEnum
from src.apps.functional_test.models import ManualTestCase
from src.apps.functional_test.selectors.querysets import FunctionalTestQuerySelector


class ApiAutomationStartMixin:
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
            raise ai_service_error("请选择要生成API自动化的功能用例")
        manual_case = FunctionalTestQuerySelector.manual_test_case().select_related("suite", "project_product",
                                                                                    "module").get(id=manual_case_id)
        if ManualTestTypeEnum.API.value not in (manual_case.test_types or []):
            raise ai_service_error("当前用例未开启API自动化测试类型")
        if not skill_id:
            raise ai_service_error("生成API自动化必须选择技能")
        selected_mcp_server_ids = cls.normalize_mcp_server_ids(mcp_server_ids)
        if not selected_mcp_server_ids:
            raise ai_service_error("生成API自动化必须选择MCP服务")
        active_task = cls.find_active_task(manual_case.id)
        if active_task:
            raise ai_service_error("当前功能用例已有API自动化生成任务进行中，请等待完成后再操作")
        skill = AgentSkillService.get_skill(skill_id=skill_id)
        if not skill:
            raise ai_service_error("选择的技能不存在或未发布")
        if skill.skill_type != AiSkillTypeEnum.API_AUTOMATION.value:
            raise ai_service_error("生成API自动化只能选择API自动化类型的技能")
        mcp_servers = list(AiMcpServer.objects.filter(id__in=selected_mcp_server_ids, status=1))
        if len(mcp_servers) != len(selected_mcp_server_ids):
            raise ai_service_error("选择的MCP服务不存在或已停用")
        selected_role = AgentDefinitionService.resolve_role(cls.agent_key, ai_role)
        context_package = AgentContextService.build_api_context_package(manual_case.suite, context_keys)
        existing = FunctionalTestQuerySelector.manual_test_automation_binding().filter(
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
        cls.attach_context_snapshot(task, context_package)
        AiAgentTaskItem.objects.create(
            task=task,
            manual_case_id=manual_case.id,
            item_order=1,
            api_case_id=existing.api_case_id if existing else None,
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
            raise ai_service_error("请选择要批量生成API自动化的需求或功能用例")
        if not skill_id:
            raise ai_service_error("生成API自动化必须选择技能")
        selected_mcp_server_ids = cls.normalize_mcp_server_ids(mcp_server_ids)
        if not selected_mcp_server_ids:
            raise ai_service_error("生成API自动化必须选择MCP服务")
        skill = AgentSkillService.get_skill(skill_id=skill_id)
        if not skill:
            raise ai_service_error("选择的技能不存在或未发布")
        if skill.skill_type != AiSkillTypeEnum.API_AUTOMATION.value:
            raise ai_service_error("生成API自动化只能选择API自动化类型的技能")
        mcp_servers = list(AiMcpServer.objects.filter(id__in=selected_mcp_server_ids, status=1))
        if len(mcp_servers) != len(selected_mcp_server_ids):
            raise ai_service_error("选择的MCP服务不存在或已停用")

        suite, manual_cases = cls.resolve_batch_cases(suite_id=suite_id, manual_case_ids=manual_case_ids, scope=scope)
        if not manual_cases:
            raise ai_service_error("当前需求暂无可生成API自动化的用例")
        active_batch = cls.find_active_suite_batch_task(suite.id)
        if active_batch:
            raise ai_service_error("当前需求已有批量API自动化生成任务进行中，请等待完成后再操作")
        active_case = next((case for case in manual_cases if cls.find_active_task(case.id)), None)
        if active_case:
            raise ai_service_error(
                f"功能用例 {active_case.case_no or active_case.id} 已有API自动化生成任务进行中，请等待完成后再操作")

        selected_role = AgentDefinitionService.resolve_role(cls.agent_key, ai_role)
        context_package = AgentContextService.build_api_context_package(suite, context_keys)
        api_bindings = {
            item.manual_case_id: item
            for item in FunctionalTestQuerySelector.manual_test_automation_binding().filter(
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
        cls.attach_context_snapshot(task, context_package)
        AiAgentTaskItem.objects.bulk_create(
            [
                AiAgentTaskItem(
                    task=task,
                    manual_case_id=case.id,
                    item_order=index,
                    api_case_id=(api_bindings.get(case.id).api_case_id if api_bindings.get(case.id) else None),
                )
                for index, case in enumerate(manual_cases, start=1)
            ]
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
