# -*- coding: utf-8 -*-
from src.apps.ai.agent.api_automation.skill_contract import ApiAutomationSkillContractCompiler
from src.apps.ai.agent.api_automation.tool_catalog import ApiAutomationToolStageCatalog
from src.apps.ai.enums import AiAgentTaskStatusEnum, AiSkillTypeEnum
from src.apps.ai.enums.role import AgentRole
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentTask, AiAgentTaskItem, AiMcpServer
from src.apps.ai.services.agent.context import AgentContextService
from src.apps.ai.services.agent.task_step import AiAgentTaskStepService
from src.apps.ai.services.harness.artifact import AgentArtifactService
from src.apps.ai.services.harness.definition import AgentDefinitionService
from src.apps.ai.services.skill.service import AgentSkillService
from src.apps.functional_test.selectors.querysets import FunctionalTestQuerySelector


class ApiAutomationRetryMixin:
    @classmethod
    def retry(cls, task_id: int, input_patch: dict | None = None):
        task = AiAgentTask.objects.get(id=task_id, task_type=cls.task_type)
        if task.status in cls.active_statuses:
            raise ai_service_error("当前任务正在运行中，请等待完成后再操作")
        input_data = dict(task.input_data or {})
        previous_signature = cls.retry_signature(input_data)
        previous_skill_version_id = task.skill_version_id
        if input_patch:
            input_data.update(input_patch)
        if input_patch and "selected_context_keys" in input_patch:
            suite = FunctionalTestQuerySelector.manual_test_suite().get(id=input_data.get("suite_id"))
            context_package = AgentContextService.build_api_context_package(
                suite,
                input_data.get("selected_context_keys") or None,
            )
            input_data.update(
                {
                    "selected_context_keys": context_package["context_keys"],
                    "context_hash": context_package["context_hash"],
                    "reuse_context": context_package["reuse_context"],
                    "reuse_context_id": context_package["reuse_context_id"],
                }
            )
            input_data["context_artifact_id"] = AgentArtifactService.create(
                task,
                "api_context_snapshot",
                context_package,
                status="validated",
            ).id
        input_data["ai_role"] = AgentDefinitionService.resolve_role(
            cls.agent_key,
            input_data.get("ai_role"),
        )
        input_data["role_snapshot"] = AgentRole.snapshot(input_data["ai_role"])
        if input_data.get("mode") == "batch":
            cls.prepare_batch_continue_input(task, input_data)
        if input_patch and "skill_id" in input_patch:
            skill = AgentSkillService.get_skill(skill_id=input_data.get("skill_id") or None)
            if not skill:
                raise ai_service_error("生成API自动化必须选择技能")
            if skill.skill_type != AiSkillTypeEnum.API_AUTOMATION.value:
                raise ai_service_error("生成API自动化只能选择API自动化类型的技能")
            input_data["skill_snapshot"] = AgentSkillService.skill_snapshot(skill) if skill else {}
            from src.apps.ai.services.harness.skill_version import SkillVersionService

            task.skill = skill
            task.skill_version = SkillVersionService.resolve(skill, task.create_user_id)
        if input_patch and "mcp_server_ids" in input_patch:
            server_ids = cls.normalize_mcp_server_ids(input_data.get("mcp_server_ids"))
            if not server_ids:
                raise ai_service_error("生成API自动化必须选择MCP服务")
            servers = list(AiMcpServer.objects.filter(id__in=server_ids, status=1))
            if len(servers) != len(server_ids):
                raise ai_service_error("选择的MCP服务不存在或已停用")
            server_map = {server.id: server for server in servers}
            ordered_servers = [server_map[server_id] for server_id in server_ids]
            input_data["mcp_server_ids"] = server_ids
            input_data["mcp_server_names"] = [server.name for server in ordered_servers]
            input_data["mcp_server_prompts"] = {
                server.id: server.prompt or "" for server in ordered_servers
            }
        task.input_data = input_data
        task.input_snapshot = input_data
        task.status = AiAgentTaskStatusEnum.PENDING.value
        task.error_message = None
        task.output_data = {}
        task.worker_id = None
        task.lease_expires_at = None
        task.cancel_requested = False
        update_fields = ["input_data", "input_snapshot", "status", "error_message", "output_data", "worker_id",
                         "lease_expires_at", "cancel_requested", "update_time"]
        if input_patch and "skill_id" in input_patch:
            update_fields.extend(["skill", "skill_version"])
        task.save(update_fields=update_fields)
        next_signature = cls.retry_signature(input_data)
        if previous_signature == next_signature and previous_skill_version_id == task.skill_version_id:
            AiAgentTaskStepService.reset_from_step(task, cls.step_defs, "load_capabilities")
        else:
            AiAgentTaskStepService.reset_steps(task, cls.step_defs)
        cls.dispatch(task.id)
        return task

    @staticmethod
    def retry_signature(input_data: dict) -> tuple:
        return (
            input_data.get("context_hash"),
            input_data.get("skill_id"),
            tuple(sorted(int(item) for item in input_data.get("mcp_server_ids") or [])),
            input_data.get("ai_role"),
            input_data.get("user_instruction") or "",
        )

    @staticmethod
    def prepare_batch_continue_input(task: AiAgentTask, input_data: dict):
        pending_case_ids = list(
            AiAgentTaskItem.objects.filter(task=task)
            .exclude(status=AiAgentTaskStatusEnum.SUCCESS.value)
            .order_by("item_order", "id")
            .values_list("manual_case_id", flat=True)
        )
        if not pending_case_ids:
            raise ai_service_error("当前批量任务已全部成功，无需继续生成")
        input_data["retry_pending_case_ids"] = pending_case_ids

    @staticmethod
    def missing_skill_capabilities(skill_contract: dict, available_tools: set[str]) -> list[str]:
        group_map = {
            "data_factory": "data_factory",
            "extractor": "extractors",
            "headers": "headers",
            "diagnosis": "execution",
        }
        missing = []
        for capability in skill_contract.get("required_capabilities") or []:
            if capability in ApiAutomationSkillContractCompiler.BASE_REQUIRED:
                continue
            group = group_map.get(capability)
            if group and not (available_tools & set(ApiAutomationToolStageCatalog.TOOL_GROUPS[group])):
                missing.append(capability)
        return missing

    @staticmethod
    def validate_skill_execution(skill_contract: dict, plan: dict):
        if not plan.get("builtin_workflow"):
            return
        capability_stage_map = {
            "data_factory": "configure_data_factory",
            "extractor": "add_extractors",
            "headers": "configure_headers",
            "diagnosis": "execute_and_diagnose",
        }
        stage_results = {
            item.get("stage"): item
            for item in plan.get("stage_results") or []
        }
        missing = []
        for capability in skill_contract.get("required_capabilities") or []:
            if capability in ApiAutomationSkillContractCompiler.BASE_REQUIRED:
                continue
            stage = stage_results.get(capability_stage_map.get(capability)) or {}
            if stage.get("skipped") or int(stage.get("tool_call_count") or 0) <= 0:
                missing.append(capability)
        if missing:
            raise ai_service_error(
                "API 自动化未按内置 Skill 执行必需能力：" + "、".join(missing)
            )
