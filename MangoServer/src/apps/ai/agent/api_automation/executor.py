# -*- coding: utf-8 -*-
import json
from typing import Any

from src.apps.ai.agent.api_automation.result_extractor import ApiAutomationResultExtractor
from src.apps.ai.agent.api_automation.tool_catalog import ApiAutomationToolStageCatalog
from src.apps.ai.agent.api_automation.tool_schema import ApiAutomationToolSchemaBuilder
from src.apps.ai.agent.api_automation.workflow_planner import ApiAutomationWorkflowPlanner
from src.apps.ai.enums.role import AgentRole
from src.apps.ai.exceptions import AiError, ai_service_error
from src.apps.ai.model_gateway.client import AgentModelGateway
from src.apps.ai.models import AiAgentTask, AiMcpServer, AiMcpTool, AiSkill
from src.apps.ai.services.agent.api_case_execution import ApiCaseExecutionService
from src.apps.ai.services.agent.budget import AgentBudgetService
from src.apps.ai.services.agent.mcp.tool_runner import AgentMcpToolRunner
from src.apps.ai.services.core import AiTaskService, mask_sensitive
from src.apps.ai.services.harness.artifact import AgentArtifactService, AgentEventService
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.functional_test.enums import ManualTestAutomationTypeEnum, ManualTestRelationTypeEnum, ManualTestTypeEnum
from src.apps.functional_test.models import ManualTestCase, ManualTestSuite
from src.apps.functional_test.services.automation import ManualAutomationService
from src.common.prompts import get_prompt


class ApiAutomationExecutor:
    TOOL_LIMIT = None
    STAGE_MAX_ROUNDS = 4
    ASSET_REPAIR_ROUNDS = 2
    API_CREATE_TOOLS = {"create_api_case", "create_complete_api_case"}
    API_UPDATE_TOOLS = {
        "update_api_case",
        "update_api_info",
        "update_api_case_scenario",
        "create_api_info",
        "add_api_case_step",
        "create_api_case_scenario",
        "create_complete_api_case",
    }
    API_CASE_ID_INJECTION_TOOLS = {"update_api_case", "add_api_case_step"}
    API_RUN_TOOLS = {"run_api_case", "run_api_case_batch"}

    @classmethod
    def execute(
            cls,
            *,
            task: AiAgentTask,
            manual_case: ManualTestCase,
            suite: ManualTestSuite,
            skill: AiSkill,
            mcp_servers: list[AiMcpServer],
            context_package: dict,
            existing_api_case_id: int | None,
            ai_role: str,
            user_instruction: str,
            user_id: int | None,
            skill_contract: dict | None = None,
            workflow_plan: dict | None = None,
    ) -> dict:
        if ManualTestTypeEnum.API.value not in (manual_case.test_types or []):
            raise ai_service_error("当前用例未开启API自动化测试类型")
        if not skill:
            raise ai_service_error("生成API自动化必须选择技能")
        if not mcp_servers:
            raise ai_service_error("生成API自动化必须选择MCP服务")

        tools, tool_map = cls.build_tools(mcp_servers, user_id, existing_api_case_id)
        if not tools:
            raise ai_service_error("选中的MCP服务没有可用工具，请先同步MCP工具")

        use_builtin_workflow = cls.should_use_builtin_workflow(skill, mcp_servers)
        workflow_plan = workflow_plan or {}
        tool_calls: list[dict] = []
        api_case_id: int | None = None
        final_message: dict = {}
        stage_results: list[dict] = []
        used_write_tool = False
        used_run_tool = False
        execution_record_id: int | None = None
        exhausted_rounds = False

        if tools:
            tool_catalog = ApiAutomationToolStageCatalog.catalog_for_tools(tool_map)
            if not workflow_plan:
                workflow_plan = ApiAutomationWorkflowPlanner.plan(
                    manual_case=manual_case,
                    suite=suite,
                    skill=skill,
                    context_package=context_package,
                    existing_api_case_id=existing_api_case_id,
                    tool_catalog=tool_catalog,
                    user_instruction=user_instruction,
                    ai_role=ai_role,
                    skill_contract=skill_contract or {},
                    task=task,
                )
            planned_stages = workflow_plan.get("stages") or []
            for stage_index, stage in enumerate(planned_stages, start=1):
                stage_tool_map = ApiAutomationToolStageCatalog.tools_for_stage(tool_map, stage["stage"])
                stage_tools = ApiAutomationToolStageCatalog.openai_tools_for_stage(tools, stage_tool_map)
                if not stage_tools:
                    stage_results.append(
                        {
                            "stage": stage["stage"],
                            "name": stage["name"],
                            "skipped": True,
                            "reason": "当前 MCP 服务没有该阶段可用工具",
                        }
                    )
                    continue
                messages = cls.build_messages(
                    manual_case=manual_case,
                    suite=suite,
                    skill=skill,
                    mcp_servers=mcp_servers,
                    tools=stage_tools,
                    context_package=context_package,
                    existing_api_case_id=existing_api_case_id,
                    ai_role=ai_role,
                    user_instruction=user_instruction,
                    workflow_plan=workflow_plan,
                    current_stage=stage,
                    stage_results=stage_results,
                    api_case_id=api_case_id,
                    builtin_workflow=use_builtin_workflow,
                )
                stage_tool_call_count = 0
                AiTaskService.update_progress(
                    task,
                    min(20 + int(stage_index / max(len(planned_stages), 1) * 15), 35),
                    "请求已经发给 AI",
                    f"正在执行工具链阶段：{stage['name']}（{stage_index}/{len(planned_stages)}）",
                    {"stage": stage["stage"], "stage_index": stage_index, "stage_total": len(planned_stages)},
                )

                stage_completed = False
                for round_index in range(cls.STAGE_MAX_ROUNDS):
                    response = AgentModelGateway.chat_with_tools(
                        task=task,
                        messages=messages,
                        tools=stage_tools,
                        tool_choice="auto",
                        temperature=0,
                        max_tokens=3000,
                    )
                    final_message = cls.first_message(response)
                    current_tool_calls = final_message.get("tool_calls") or []
                    if not current_tool_calls:
                        api_case_id = cls.extract_api_case_id(final_message) or cls.extract_api_case_id(
                            cls.message_content(final_message)) or api_case_id
                        stage_completed = True
                        break
                    messages.append(final_message)
                    call_result = cls.handle_tool_calls(
                        task=task,
                        tool_calls=tool_calls,
                        current_tool_calls=current_tool_calls,
                        stage_tool_map=stage_tool_map,
                        full_tool_map=tool_map,
                        messages=messages,
                        manual_case=manual_case,
                        suite=suite,
                        existing_api_case_id=existing_api_case_id,
                        user_id=user_id,
                        stage=stage,
                        stage_index=stage_index,
                        api_case_id=api_case_id,
                    )
                    stage_tool_call_count += call_result["stage_tool_call_count"]
                    api_case_id = call_result["api_case_id"] or api_case_id
                    used_write_tool = used_write_tool or call_result["used_write_tool"]
                    used_run_tool = used_run_tool or call_result["used_run_tool"]
                    execution_record_id = call_result.get("execution_record_id") or execution_record_id
                if not stage_completed:
                    exhausted_rounds = True
                stage_results.append(
                    {
                        "stage": stage["stage"],
                        "name": stage["name"],
                        "skipped": False,
                        "tool_call_count": stage_tool_call_count,
                        "api_case_id": api_case_id,
                        "assistant_message": cls.message_content(final_message)[:3000],
                    }
                )
        if not tool_calls:
            raise ai_service_error("AI未调用MCP工具。请检查技能是否明确要求使用MCP创建或更新API自动化Case")
        if exhausted_rounds and (not api_case_id or not used_write_tool):
            raise ai_service_error(
                "AI工具调用已达到最大轮次，但仍未完成API自动化Case创建或更新。请检查技能流程是否过于宽泛，或补充更明确的生成要求")
        if existing_api_case_id:
            api_case_id = api_case_id or existing_api_case_id
            if int(api_case_id) != int(existing_api_case_id):
                raise ai_service_error(f"已绑定API Case必须覆盖旧ID，但MCP返回了不同ID：{api_case_id}")
        if not api_case_id:
            latest_result = tool_calls[-1]["result"] if tool_calls else {}
            latest_error = cls.extract_mcp_error_message(latest_result)
            if latest_error:
                raise ai_service_error(f"MCP工具执行失败：{latest_error}")
            raise ai_service_error(
                f"MCP工具调用完成但未返回api_case_id/case_id，最近一次MCP返回：{json.dumps(latest_result, ensure_ascii=False)[:800]}")
        if not used_write_tool:
            raise ai_service_error("AI未调用创建或更新API自动化Case的MCP写入工具")
        if not ApiQuerySelector.api_case().filter(id=api_case_id).exists():
            raise ai_service_error(f"MCP返回的API Case不存在：{api_case_id}")

        if not used_run_tool:
            run_result = cls.try_run_api_case(task, tools, tool_map, int(api_case_id), user_id)
            if run_result:
                used_run_tool = True
                execution_record_id = run_result.get("execution_record_id") or execution_record_id
                tool_calls.append(run_result)
        if not used_run_tool:
            raise ai_service_error("API Case 已生成，但没有可用 MCP 工具执行一次 API Case")
        if not execution_record_id:
            raise ai_service_error("API Case 已触发执行，但没有保存本次 Agent 的执行调用记录")

        asset_repair_report = {"required": False, "rounds": 0, "errors": []}
        try:
            assertion_summary = cls.validate_api_case_assertions(int(api_case_id))
            skill_asset_summary = cls.validate_required_assets(int(api_case_id), skill_contract or {})
        except (AiError, ValueError) as exc:
            asset_repair_report = cls.repair_asset_configuration(
                task=task,
                tool_calls=tool_calls,
                tools=tools,
                tool_map=tool_map,
                manual_case=manual_case,
                suite=suite,
                skill=skill,
                mcp_servers=mcp_servers,
                context_package=context_package,
                existing_api_case_id=existing_api_case_id,
                api_case_id=int(api_case_id),
                ai_role=ai_role,
                user_instruction=user_instruction,
                user_id=user_id,
                validation_error=str(exc),
                skill_contract=skill_contract or {},
            )
            assertion_summary = cls.validate_api_case_assertions(int(api_case_id))
            skill_asset_summary = cls.validate_required_assets(int(api_case_id), skill_contract or {})

        binding = ManualAutomationService.bind(
            manual_case,
            ManualTestAutomationTypeEnum.API.value,
            int(api_case_id),
            ManualTestRelationTypeEnum.GENERATED.value,
            user_id,
        )
        return {
            "api_case_id": int(api_case_id),
            "binding_id": binding.id,
            "execution_record_id": execution_record_id,
            "tool_calls": tool_calls,
            "workflow_plan": workflow_plan,
            "stage_results": stage_results,
            "assertion_summary": assertion_summary,
            "skill_asset_summary": skill_asset_summary,
            "asset_repair_report": asset_repair_report,
            "assistant_message": cls.message_content(final_message),
            "selected_context_keys": context_package["context_keys"],
            "context_hash": context_package["context_hash"],
            "reuse_context": context_package["reuse_context"],
            "reuse_context_id": context_package["reuse_context_id"],
            "mcp_server_ids": [server.id for server in mcp_servers],
            "mcp_server_names": [server.name for server in mcp_servers],
            "mcp_server_prompts": {server.id: server.prompt or "" for server in mcp_servers},
            "skill_id": skill.id,
            "ai_role": cls.normalize_ai_role(ai_role),
            "builtin_workflow": use_builtin_workflow,
            "diff_summary": "已通过 MCP 工具生成或更新 API 自动化 Case，并执行一次。",
        }

    @classmethod
    def build_tools(
            cls,
            servers: list[AiMcpServer],
            user_id: int | None,
            existing_api_case_id: int | None,
            *,
            refresh: bool = False,
    ) -> tuple[list[dict], dict[str, AiMcpTool]]:
        return ApiAutomationToolSchemaBuilder.build_tools(
            servers,
            user_id,
            existing_api_case_id,
            cls.TOOL_LIMIT,
            refresh=refresh,
        )

    @classmethod
    def build_messages(
            cls,
            *,
            manual_case: ManualTestCase,
            suite: ManualTestSuite,
            skill: AiSkill,
            mcp_servers: list[AiMcpServer],
            tools: list[dict],
            context_package: dict,
            existing_api_case_id: int | None,
            ai_role: str,
            user_instruction: str,
            workflow_plan: dict | None = None,
            current_stage: dict | None = None,
            stage_results: list[dict] | None = None,
            api_case_id: int | None = None,
            builtin_workflow: bool = False,
    ) -> list[dict]:
        prompt = get_prompt("api.automation")
        role_prompt = AgentRole.prompt(cls.normalize_ai_role(ai_role), AgentRole.API_AUTOMATION_EXPERT)
        action_rule = (
            prompt.render("update_action_rule", existing_api_case_id=existing_api_case_id)
            if existing_api_case_id
            else prompt.values["create_action_rule"]
        )
        context_payload = {
            "context_hash": context_package["context_hash"],
            "reuse_context": context_package["reuse_context"],
            "reuse_context_id": context_package["reuse_context_id"],
            "context_summary": context_package["context_summary"],
            "history": context_package["history"],
        }
        if not context_package["reuse_context"]:
            context_payload["full_context"] = context_package["context_text"]
        user_payload = {
            "task": prompt.values["executor_task"],
            "suite": {
                "id": suite.id,
                "requirement_name": suite.requirement_name,
                "iteration": suite.iteration,
                "project_product_id": suite.project_product_id,
                "module_id": suite.module_id,
                "owner_id": suite.owner_id,
            },
            "manual_case": {
                "id": manual_case.id,
                "case_no": manual_case.case_no,
                "project_product_id": manual_case.project_product_id,
                "module_id": manual_case.module_id,
                "title": manual_case.title,
                "test_types": manual_case.test_types,
                "priority": manual_case.priority,
                "precondition": manual_case.precondition,
                "test_point": manual_case.test_point,
                "test_data": manual_case.test_data,
                "scenario_layer": manual_case.scenario_layer,
                "scenario_type": manual_case.scenario_type,
                "scenario_tags": manual_case.scenario_tags,
                "remark": manual_case.remark,
            },
            "existing_api_case_id": existing_api_case_id,
            "mcp_servers": [
                {
                    "id": server.id,
                    "name": server.name,
                    "server_url": server.server_url,
                    "description": server.description or "",
                    "prompt": server.prompt or "",
                }
                for server in mcp_servers
            ],
            "available_tool_names": [item["function"]["name"] for item in tools],
            "workflow_plan": workflow_plan or {},
            "current_stage": current_stage or {},
            "completed_stage_results": stage_results or [],
            "current_api_case_id": api_case_id,
            "builtin_workflow": builtin_workflow,
            "context": context_payload,
            "user_instruction": user_instruction,
            "requirements": [action_rule, *prompt.values["requirements"]],
        }
        system_prompt = prompt.render(
            "executor_system",
            role_prompt=role_prompt,
            skill_content=skill.content,
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]

    @classmethod
    def should_use_builtin_workflow(cls, skill: AiSkill, mcp_servers: list[AiMcpServer]) -> bool:
        if not getattr(skill, "is_builtin", False):
            return False
        return any((server.auth_config or {}).get("builtin") for server in mcp_servers)

    @classmethod
    def handle_tool_calls(
            cls,
            *,
            task: AiAgentTask,
            tool_calls: list[dict],
            current_tool_calls: list[dict],
            stage_tool_map: dict[str, AiMcpTool],
            full_tool_map: dict[str, AiMcpTool] | None,
            messages: list[dict],
            manual_case: ManualTestCase,
            suite: ManualTestSuite,
            existing_api_case_id: int | None,
            user_id: int | None,
            stage: dict,
            stage_index: int,
            api_case_id: int | None,
    ) -> dict:
        stage_tool_call_count = 0
        used_write_tool = False
        used_run_tool = False
        execution_record_id = None
        for tool_call in current_tool_calls:
            tool_call_id, tool_name, arguments = cls.tool_call_parts(tool_call)
            tool = stage_tool_map.get(tool_name)
            if not tool:
                tool = cls.resolve_readonly_cross_stage_tool(tool_name, full_tool_map)
            if not tool:
                raise ai_service_error(f"AI请求调用的MCP工具不可用：{tool_name}")
            call_index = len(tool_calls) + 1
            stage_tool_call_count += 1
            AiTaskService.update_progress(
                task,
                min(38 + call_index * 3, 82),
                "MCP 工具调用到第几个",
                f"正在调用第 {call_index} 个 MCP 工具：{tool.name}",
                {
                    "stage": stage.get("stage"),
                    "stage_index": stage_index,
                    "tool_call_index": call_index,
                    "tool_name": tool.name,
                },
            )
            arguments = cls.normalize_tool_arguments(tool.name, arguments, manual_case, suite, existing_api_case_id,
                                                     user_id)
            result = AgentMcpToolRunner.call(task, tool, arguments, user_id)
            error_message = cls.extract_mcp_error_message(result)
            tool_calls.append(
                {
                    "stage": stage.get("stage"),
                    "tool": tool.name,
                    "arguments": mask_sensitive(arguments),
                    "result": mask_sensitive(result),
                    "error_message": error_message,
                }
            )
            if tool.name in cls.API_CREATE_TOOLS or tool.name in cls.API_UPDATE_TOOLS:
                used_write_tool = True
            if tool.name in cls.API_RUN_TOOLS:
                used_run_tool = True
                execution_record_id = getattr(task, "last_tool_call_id", None) or execution_record_id
            extracted_id = cls.extract_api_case_id(result)
            if extracted_id:
                api_case_id = extracted_id
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": cls.extract_mcp_text(result)[:12000],
                }
            )
        return {
            "stage_tool_call_count": stage_tool_call_count,
            "api_case_id": api_case_id,
            "used_write_tool": used_write_tool,
            "used_run_tool": used_run_tool,
            "execution_record_id": execution_record_id,
        }

    @staticmethod
    def resolve_readonly_cross_stage_tool(tool_name: str,
                                          full_tool_map: dict[str, AiMcpTool] | None) -> AiMcpTool | None:
        tool = (full_tool_map or {}).get(tool_name)
        if tool and not tool.write_operation:
            return tool
        return None

    @classmethod
    def try_run_api_case(cls, task: AiAgentTask, tools: list[dict], tool_map: dict[str, AiMcpTool], api_case_id: int,
                         user_id: int | None) -> dict | None:
        return ApiCaseExecutionService.try_run_api_case(task, tool_map, api_case_id, user_id)

    @classmethod
    def validate_api_case_assertions(cls, api_case_id: int) -> dict:
        details = list(ApiQuerySelector.api_case_detailed().select_related("api_info").filter(case_id=api_case_id))
        if not details:
            raise ai_service_error(f"API Case {api_case_id} 没有步骤，无法作为有效 API 自动化用例")

        detail_ids = [detail.id for detail in details]
        parameters = list(ApiQuerySelector.api_case_detailed_parameter().filter(case_detailed_id__in=detail_ids))
        if not parameters:
            raise ai_service_error(f"API Case {api_case_id} 没有场景参数，无法作为有效 API 自动化用例")

        summary = {
            "api_case_id": api_case_id,
            "step_count": len(details),
            "scenario_count": len(parameters),
            "ass_jsonpath_count": 0,
            "ass_general_count": 0,
            "ass_json_all_count": 0,
            "ass_text_all_count": 0,
            "ass_schema_count": 0,
            "api_info_schema_count": 0,
        }
        api_infos = {}
        for detail in details:
            try:
                api_info = ApiInfoRuntimeService.resolve_runtime(detail.api_info_id, allow_draft=True)
            except Exception:
                api_info = None
            api_infos[detail.id] = api_info
            if api_info and api_info.ass_schema:
                summary["api_info_schema_count"] += 1
        for parameter in parameters:
            summary["ass_jsonpath_count"] += len(parameter.ass_jsonpath or [])
            summary["ass_general_count"] += len(parameter.ass_general or [])
            if parameter.ass_json_all:
                summary["ass_json_all_count"] += 1
            if (parameter.ass_text_all or "").strip():
                summary["ass_text_all_count"] += 1
            if parameter.ass_schema:
                summary["ass_schema_count"] += 1

        total_assertions = (
                summary["ass_jsonpath_count"]
                + summary["ass_general_count"]
                + summary["ass_json_all_count"]
                + summary["ass_text_all_count"]
                + summary["ass_schema_count"]
                + summary["api_info_schema_count"]
        )
        summary["total_assertion_count"] = total_assertions
        if total_assertions <= 0:
            raise ai_service_error(
                f"API Case {api_case_id} 已生成并执行一次，但没有配置任何断言。"
                "请让 AI 按 Skill 补充状态码、JSONPath、文本、Schema 或业务字段断言后重新生成"
            )
        return summary

    @staticmethod
    def validate_required_assets(api_case_id: int, skill_contract: dict) -> dict:
        required = set(skill_contract.get("required_capabilities") or [])
        case = ApiQuerySelector.api_case().get(id=api_case_id)
        from src.apps.auto_api.services.api_case.snapshot import ApiExecutableSnapshotService

        case_config = ApiExecutableSnapshotService.current_case_config(
            case.id,
            case.project_product_id,
        )
        details = list(ApiQuerySelector.api_case_detailed().select_related("api_info").filter(case=case))
        parameters = list(
            ApiQuerySelector.api_case_detailed_parameter().filter(case_detailed_id__in=[item.id for item in details])
        )
        api_infos = {}
        for detail in details:
            try:
                api_infos[detail.id] = ApiInfoRuntimeService.resolve_runtime(detail.api_info_id, allow_draft=True)
            except Exception:
                api_infos[detail.id] = None
        result = {}
        if "data_factory" in required:
            has_data_factory = DataFactoryQuerySelector.data_factory_case_config().filter(
                source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
                source_id=api_case_id,
            ).exists() or DataFactoryQuerySelector.data_factory_case_config().filter(
                source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
                source_id__in=[item.id for item in parameters],
            ).exists()
            if not has_data_factory:
                raise ai_service_error("Skill 要求配置数据工厂，但真实 API Case 未查询到数据工厂绑定")
            result["data_factory"] = True
        if "headers" in required:
            has_headers = bool(case_config.get("front_headers")) or any(
                bool(item.headers) for item in parameters) or any(
                bool(api_infos.get(item.id) and api_infos[item.id].headers) for item in details
            )
            if not has_headers:
                raise ai_service_error("Skill 要求配置请求头，但真实 API Case 未查询到请求头配置")
            result["headers"] = True
        if "extractor" in required:
            has_extractor = any(
                bool(
                    api_infos.get(item.id)
                    and (
                            api_infos.get(item.id).posterior_json_path
                            or api_infos.get(item.id).posterior_re
                            or api_infos.get(item.id).posterior_func
                    )
                )
                for item in details
            ) or any(bool(item.posterior_response or item.posterior_response_text) for item in parameters)
            if not has_extractor:
                raise ai_service_error("Skill 要求配置提取器，但真实 API Case 未查询到提取器配置")
            result["extractor"] = True
        return result

    @classmethod
    def repair_asset_configuration(
            cls,
            *,
            task: AiAgentTask,
            tool_calls: list[dict],
            tools: list[dict],
            tool_map: dict[str, AiMcpTool],
            manual_case: ManualTestCase,
            suite: ManualTestSuite,
            skill: AiSkill,
            mcp_servers: list[AiMcpServer],
            context_package: dict,
            existing_api_case_id: int | None,
            api_case_id: int,
            ai_role: str,
            user_instruction: str,
            user_id: int | None,
            validation_error: str,
            skill_contract: dict,
    ) -> dict:
        prompt = get_prompt("api.automation")
        AgentBudgetService.before_replan(task)
        replan = {
            "reason": validation_error,
            "api_case_id": api_case_id,
            "required_capabilities": skill_contract.get("required_capabilities") or [],
            "forbidden_capabilities": skill_contract.get("forbidden_capabilities") or [],
            "strategy": "仅重规划和修复缺失资产，不重建已验证资产",
        }
        AgentArtifactService.create(task, "replan", replan, status="validated")
        AgentEventService.emit(
            task,
            "workflow_replanned",
            "真实资产校验未通过，正在定向重规划",
            data=replan,
            step_key="diagnose_and_repair",
        )
        capability_stage_map = {
            "headers": "configure_headers",
            "data_factory": "configure_data_factory",
            "assertion": "add_assertions",
            "extractor": "add_extractors",
        }
        forbidden_stages = {
            capability_stage_map[capability]
            for capability in skill_contract.get("forbidden_capabilities") or []
            if capability in capability_stage_map
        }
        repair_stage_names = {
                                 "create_or_update_case",
                                 "configure_headers",
                                 "configure_data_factory",
                                 "add_assertions",
                                 "add_extractors",
                             } - forbidden_stages
        repair_tool_names = set()
        for stage_name in repair_stage_names:
            repair_tool_names.update(ApiAutomationToolStageCatalog.stage_tool_names(stage_name))
        repair_tool_map = {
            safe_name: tool
            for safe_name, tool in tool_map.items()
            if tool.name in repair_tool_names
        }
        repair_tools = ApiAutomationToolStageCatalog.openai_tools_for_stage(tools, repair_tool_map)
        if not repair_tools:
            raise ai_service_error(f"API 资产校验失败且没有可用修复工具：{validation_error}")
        stage = {"stage": "repair_assets", "name": "修复缺失 API 资产"}
        messages = cls.build_messages(
            manual_case=manual_case,
            suite=suite,
            skill=skill,
            mcp_servers=mcp_servers,
            tools=repair_tools,
            context_package=context_package,
            existing_api_case_id=existing_api_case_id,
            ai_role=ai_role,
            user_instruction=user_instruction,
            current_stage=stage,
            api_case_id=api_case_id,
            builtin_workflow=True,
        )
        messages.append(
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": prompt.values["repair_task"],
                        "api_case_id": api_case_id,
                        "validation_error": validation_error,
                        "required_capabilities": skill_contract.get("required_capabilities") or [],
                        "rules": prompt.values["repair_rules"],
                    },
                    ensure_ascii=False,
                ),
            }
        )
        rounds = 0
        for round_index in range(cls.ASSET_REPAIR_ROUNDS):
            response = AgentModelGateway.chat_with_tools(
                task=task,
                messages=messages,
                tools=repair_tools,
                tool_choice="auto",
                temperature=0,
                max_tokens=3000,
            )
            message = cls.first_message(response)
            current_calls = message.get("tool_calls") or []
            if not current_calls:
                break
            rounds += 1
            messages.append(message)
            cls.handle_tool_calls(
                task=task,
                tool_calls=tool_calls,
                current_tool_calls=current_calls,
                stage_tool_map=repair_tool_map,
                full_tool_map=tool_map,
                messages=messages,
                manual_case=manual_case,
                suite=suite,
                existing_api_case_id=existing_api_case_id or api_case_id,
                user_id=user_id,
                stage=stage,
                stage_index=1,
                api_case_id=api_case_id,
            )
            try:
                cls.validate_api_case_assertions(api_case_id)
                cls.validate_required_assets(api_case_id, skill_contract)
                return {"required": True, "rounds": rounds, "errors": [validation_error], "resolved": True}
            except (AiError, ValueError) as exc:
                validation_error = str(exc)
                messages.append(
                    {
                        "role": "user",
                        "content": prompt.render("repair_followup", validation_error=validation_error),
                    }
                )
        raise ai_service_error(f"API 资产经过 {rounds} 轮修复仍未通过校验：{validation_error}")

    @staticmethod
    def safe_tool_name(name: str, used_names: set[str]) -> str:
        return ApiAutomationToolSchemaBuilder.safe_tool_name(name, used_names)

    @staticmethod
    def first_message(response: dict) -> dict:
        return ApiAutomationResultExtractor.first_message(response)

    @staticmethod
    def message_content(message: dict) -> str:
        return ApiAutomationResultExtractor.message_content(message)

    @staticmethod
    def tool_call_parts(tool_call: dict) -> tuple[str, str, dict]:
        return ApiAutomationResultExtractor.tool_call_parts(tool_call)

    @classmethod
    def extract_api_case_id(cls, value: Any, allow_plain_id: bool = False) -> int | None:
        return ApiAutomationResultExtractor.extract_api_case_id(value, allow_plain_id)

    @staticmethod
    def extract_mcp_text(result: Any) -> str:
        return ApiAutomationResultExtractor.extract_mcp_text(result)

    @classmethod
    def extract_mcp_error_message(cls, result: Any) -> str:
        return ApiAutomationResultExtractor.extract_mcp_error_message(result)

    @classmethod
    def normalize_tool_arguments(
            cls,
            tool_name: str,
            arguments: dict,
            manual_case: ManualTestCase,
            suite: ManualTestSuite,
            existing_api_case_id: int | None,
            user_id: int | None,
    ) -> dict:
        if tool_name == "create_complete_api_case":
            return cls.normalize_complete_api_case_arguments(arguments, manual_case, suite, user_id)
        if existing_api_case_id and tool_name in cls.API_CASE_ID_INJECTION_TOOLS:
            normalized = dict(arguments or {})
            normalized.setdefault("case_id", existing_api_case_id)
            normalized.setdefault("api_case_id", existing_api_case_id)
            return normalized
        return arguments or {}

    @classmethod
    def normalize_complete_api_case_arguments(
            cls,
            arguments: dict,
            manual_case: ManualTestCase,
            suite: ManualTestSuite,
            user_id: int | None,
    ) -> dict:
        normalized = dict(arguments or {})
        case_name = normalized.get("case_name") or normalized.get("name") or normalized.get(
            "case_title") or manual_case.title or manual_case.case_no
        normalized["case_name"] = str(case_name or "AI生成API自动化Case")[:128]
        normalized.pop("name", None)
        normalized.setdefault("project_product_id", manual_case.project_product_id)
        normalized.setdefault("module_id", manual_case.module_id)
        owner_id = normalized.get("case_people_id") or manual_case.owner_id or suite.owner_id or user_id
        if owner_id:
            normalized["case_people_id"] = owner_id
        normalized.setdefault("scenario_layer", manual_case.scenario_layer or 0)
        normalized.setdefault("scenario_type", manual_case.scenario_type or 0)
        normalized.setdefault("scenario_tags", manual_case.scenario_tags or [])
        normalized.setdefault("scenario_description", manual_case.test_point or manual_case.title)
        api = normalized.get("api") or normalized.get("api_info") or normalized.get("interface") or {}
        api = dict(api) if isinstance(api, dict) else {}
        normalized["api"] = api
        scenarios = normalized.get("scenarios") or normalized.get("parameters") or normalized.get("scenario_list") or []
        if isinstance(scenarios, dict):
            scenarios = [scenarios]
        if not isinstance(scenarios, list):
            scenarios = []
        normalized["scenarios"] = scenarios or [{"name": manual_case.title or normalized["case_name"]}]
        missing_fields = []
        if not normalized.get("project_product_id"):
            missing_fields.append("project_product_id")
        if not normalized.get("module_id"):
            missing_fields.append("module_id")
        if not normalized["api"].get("api_info_id"):
            missing_fields.append("api.api_info_id")
        if missing_fields:
            raise ai_service_error("AI调用 create_complete_api_case 时缺少必要入参：" + "、".join(missing_fields))
        return normalized

    @staticmethod
    def normalize_http_method(value: Any) -> Any:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            method_map = {"GET": 0, "POST": 1, "PUT": 2, "DELETE": 3, "OPTIONS": 4, "DEAD": 5, "PATCH": 6}
            upper_value = value.strip().upper()
            if upper_value in method_map:
                return method_map[upper_value]
            if value.strip().isdigit():
                return int(value.strip())
        return value

    @classmethod
    def normalize_ai_role(cls, ai_role: str | None = None) -> str:
        return AgentRole.normalize(ai_role, AgentRole.API_AUTOMATION_EXPERT)
