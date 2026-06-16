# -*- coding: utf-8 -*-
import json
from typing import Any

from src.apps.ai.agent.api_automation.api_case_runner import ApiCaseExecutionService
from src.apps.ai.agent.api_automation.result_extractor import ApiAutomationResultExtractor
from src.apps.ai.agent.api_automation.tool_catalog import ApiAutomationToolStageCatalog
from src.apps.ai.agent.api_automation.tool_schema import ApiAutomationToolSchemaBuilder
from src.apps.ai.agent.api_automation.workflow_planner import ApiAutomationWorkflowPlanner
from src.apps.ai.agent.mcp.tool_runner import AgentMcpToolRunner
from src.apps.ai.agent.roles import AgentRole
from src.apps.ai.models import AiAgentTask, AiMcpServer, AiMcpTool, AiSkill
from src.apps.ai.service.core import AiTaskService, mask_sensitive
from src.apps.auto_api.models import ApiCase
from src.apps.functional_test.models import ManualTestAutomationBinding, ManualTestCase, ManualTestSuite
from src.apps.functional_test.service.automation import ManualAutomationService
from src.apps.system.service.ai.client import AiService
from src.common.enums.manual_test_enum import ManualTestAutomationTypeEnum, ManualTestRelationTypeEnum, ManualTestTypeEnum


class ApiAutomationExecutor:
    TOOL_LIMIT = 300
    MAX_ROUNDS = 8
    STAGE_MAX_ROUNDS = 4
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
    ROLE_PROMPTS = {
        AgentRole.API_AUTOMATION_EXPERT: AgentRole.PROMPTS[AgentRole.API_AUTOMATION_EXPERT],
        AgentRole.BUSINESS_TEST_EXPERT: AgentRole.PROMPTS[AgentRole.BUSINESS_TEST_EXPERT],
    }

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
    ) -> dict:
        if ManualTestTypeEnum.API.value not in (manual_case.test_types or []):
            raise ValueError("当前用例未开启API自动化测试类型")
        if not skill:
            raise ValueError("生成API自动化必须选择技能")
        if not mcp_servers:
            raise ValueError("生成API自动化必须选择MCP服务")

        tools, tool_map = cls.build_tools(mcp_servers, user_id, existing_api_case_id)
        if not tools:
            raise ValueError("选中的MCP服务没有可用工具，请先同步MCP工具")

        use_builtin_workflow = cls.should_use_builtin_workflow(skill, mcp_servers)
        workflow_plan = {}
        tool_calls: list[dict] = []
        api_case_id: int | None = None
        final_message: dict = {}
        stage_results: list[dict] = []
        used_write_tool = False
        used_run_tool = False
        exhausted_rounds = False

        if use_builtin_workflow:
            tool_catalog = ApiAutomationToolStageCatalog.catalog_for_tools(tool_map)
            workflow_plan = ApiAutomationWorkflowPlanner.plan(
                manual_case=manual_case,
                suite=suite,
                skill=skill,
                context_package=context_package,
                existing_api_case_id=existing_api_case_id,
                tool_catalog=tool_catalog,
                user_instruction=user_instruction,
                ai_role=ai_role,
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
                    builtin_workflow=True,
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
                    response = AiService.chat_with_tools(
                        messages=messages,
                        tools=stage_tools,
                        tool_choice="auto",
                        temperature=0,
                        max_tokens=3000,
                    )
                    final_message = cls.first_message(response)
                    current_tool_calls = final_message.get("tool_calls") or []
                    if not current_tool_calls:
                        api_case_id = cls.extract_api_case_id(final_message) or cls.extract_api_case_id(cls.message_content(final_message)) or api_case_id
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
        else:
            messages = cls.build_messages(
                manual_case=manual_case,
                suite=suite,
                skill=skill,
                mcp_servers=mcp_servers,
                tools=tools,
                context_package=context_package,
                existing_api_case_id=existing_api_case_id,
                ai_role=ai_role,
                user_instruction=user_instruction,
                builtin_workflow=False,
            )
            generic_completed = False
            for round_index in range(cls.MAX_ROUNDS):
                AiTaskService.update_progress(
                    task,
                    min(20 + int(round_index / cls.MAX_ROUNDS * 20), 40),
                    "请求已经发给 AI",
                    f"正在通过通用 MCP Agent 调用工具 {round_index + 1}/{cls.MAX_ROUNDS}",
                    {"round_index": round_index + 1, "round_total": cls.MAX_ROUNDS, "tool_call_count": len(tool_calls)},
                )
                response = AiService.chat_with_tools(
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0,
                    max_tokens=3000,
                )
                final_message = cls.first_message(response)
                current_tool_calls = final_message.get("tool_calls") or []
                if not current_tool_calls:
                    api_case_id = cls.extract_api_case_id(final_message) or cls.extract_api_case_id(cls.message_content(final_message)) or api_case_id
                    generic_completed = True
                    break
                messages.append(final_message)
                call_result = cls.handle_tool_calls(
                    task=task,
                    tool_calls=tool_calls,
                    current_tool_calls=current_tool_calls,
                    stage_tool_map=tool_map,
                    full_tool_map=tool_map,
                    messages=messages,
                    manual_case=manual_case,
                    suite=suite,
                    existing_api_case_id=existing_api_case_id,
                    user_id=user_id,
                    stage={"stage": "generic_mcp", "name": "通用 MCP 工具调用"},
                    stage_index=1,
                    api_case_id=api_case_id,
                )
                api_case_id = call_result["api_case_id"] or api_case_id
                used_write_tool = used_write_tool or call_result["used_write_tool"]
                used_run_tool = used_run_tool or call_result["used_run_tool"]
            if not generic_completed:
                exhausted_rounds = True
            stage_results.append(
                {
                    "stage": "generic_mcp",
                    "name": "通用 MCP 工具调用",
                    "skipped": False,
                    "tool_call_count": len(tool_calls),
                    "api_case_id": api_case_id,
                    "assistant_message": cls.message_content(final_message)[:3000],
                }
            )

        if not tool_calls:
            raise ValueError("AI未调用MCP工具。请检查技能是否明确要求使用MCP创建或更新API自动化Case")
        if exhausted_rounds and (not api_case_id or not used_write_tool):
            raise ValueError("AI工具调用已达到最大轮次，但仍未完成API自动化Case创建或更新。请检查技能流程是否过于宽泛，或将技能/MCP标记为内置后使用分阶段工具链")
        if existing_api_case_id:
            api_case_id = api_case_id or existing_api_case_id
            if int(api_case_id) != int(existing_api_case_id):
                raise ValueError(f"已绑定API Case必须覆盖旧ID，但MCP返回了不同ID：{api_case_id}")
        if not api_case_id:
            latest_result = tool_calls[-1]["result"] if tool_calls else {}
            latest_error = cls.extract_mcp_error_message(latest_result)
            if latest_error:
                raise ValueError(f"MCP工具执行失败：{latest_error}")
            raise ValueError(f"MCP工具调用完成但未返回api_case_id/case_id，最近一次MCP返回：{json.dumps(latest_result, ensure_ascii=False)[:800]}")
        if not used_write_tool:
            raise ValueError("AI未调用创建或更新API自动化Case的MCP写入工具")
        if not ApiCase.objects.filter(id=api_case_id).exists():
            raise ValueError(f"MCP返回的API Case不存在：{api_case_id}")

        if not used_run_tool:
            run_result = cls.try_run_api_case(task, tools, tool_map, int(api_case_id), user_id)
            if run_result:
                used_run_tool = True
                tool_calls.append(run_result)
        if not used_run_tool:
            raise ValueError("API Case 已生成，但没有可用 MCP 工具执行一次 API Case")

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
            "tool_calls": tool_calls,
            "workflow_plan": workflow_plan,
            "stage_results": stage_results,
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
    ) -> tuple[list[dict], dict[str, AiMcpTool]]:
        return ApiAutomationToolSchemaBuilder.build_tools(servers, user_id, existing_api_case_id, cls.TOOL_LIMIT)

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
        role_prompt = cls.ROLE_PROMPTS[cls.normalize_ai_role(ai_role)]
        action_rule = (
            f"当前功能测试用例已绑定 API Case：{existing_api_case_id}。必须严格使用旧 ID 原地更新，不允许新建重复 Case。"
            if existing_api_case_id
            else "当前功能测试用例未绑定 API Case。必须创建一个新的完整 API Case。"
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
            "task": "请严格按照 Skill，通过 MCP 工具创建或更新 API 自动化 Case。",
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
            "requirements": [
                action_rule,
                "必须调用 MCP 工具，不能只返回文字计划。",
                "调用工具前必须先阅读 mcp_servers 中每个 MCP 的 prompt 和 description，根据 MCP 职责选择工具；不要把飞书、代码检索、平台写入等不同 MCP 的用途混用。",
                "如果 builtin_workflow=true，只允许完成 current_stage 描述的工作，不要跳到其他阶段；如果当前阶段确实无需操作，请说明原因并结束本阶段。",
                "如果 builtin_workflow=false，请按用户选择的角色提示词、Skill 规则和 MCP 工具能力自行完成工具链。",
                "Skill 是强制流程，请按 Skill 中描述的接口、断言、数据工厂、执行、结果查询等步骤推进。",
                "如果 Skill 没有要求某一步，可以不做；但平台最低要求是最终有 api_case_id/case_id，并且 API Case 被执行一次。",
                "最终回复必须包含 JSON：{\"api_case_id\": 数字, \"summary\": \"...\"}。",
            ],
        }
        system_prompt = "\n\n".join(
            [
                role_prompt,
                "你只能使用已提供的 MCP tools 完成落库、更新和执行。不要编造工具返回结果。",
                "调用 create_complete_api_case 时，必须传 case_name、api.name、api.url、api.method、scenarios[].name。api.method 使用 0=GET、1=POST、2=PUT、3=DELETE、6=PATCH。",
                f"用户选择的技能规则：\n{skill.content}",
            ]
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
        for tool_call in current_tool_calls:
            tool_call_id, tool_name, arguments = cls.tool_call_parts(tool_call)
            tool = stage_tool_map.get(tool_name)
            if not tool:
                tool = cls.resolve_readonly_cross_stage_tool(tool_name, full_tool_map)
            if not tool:
                raise ValueError(f"AI请求调用的MCP工具不可用：{tool_name}")
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
            arguments = cls.normalize_tool_arguments(tool.name, arguments, manual_case, suite, existing_api_case_id, user_id)
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
        }

    @staticmethod
    def resolve_readonly_cross_stage_tool(tool_name: str, full_tool_map: dict[str, AiMcpTool] | None) -> AiMcpTool | None:
        tool = (full_tool_map or {}).get(tool_name)
        if tool and not tool.write_operation:
            return tool
        return None

    @classmethod
    def try_run_api_case(cls, task: AiAgentTask, tools: list[dict], tool_map: dict[str, AiMcpTool], api_case_id: int, user_id: int | None) -> dict | None:
        return ApiCaseExecutionService.try_run_api_case(task, tool_map, api_case_id, user_id)

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
        case_name = normalized.get("case_name") or normalized.get("name") or normalized.get("case_title") or manual_case.title or manual_case.case_no
        normalized["case_name"] = str(case_name or "AI生成API自动化Case")[:128]
        normalized.pop("name", None)
        normalized.setdefault("project_product_id", suite.project_product_id)
        normalized.setdefault("module_id", suite.module_id)
        owner_id = normalized.get("case_people_id") or manual_case.owner_id or suite.owner_id or user_id
        if owner_id:
            normalized["case_people_id"] = owner_id
        normalized.setdefault("scenario_layer", manual_case.scenario_layer or 0)
        normalized.setdefault("scenario_type", manual_case.scenario_type or 0)
        normalized.setdefault("scenario_tags", manual_case.scenario_tags or [])
        normalized.setdefault("scenario_description", manual_case.test_point or manual_case.title)
        api = normalized.get("api") or normalized.get("api_info") or normalized.get("interface") or {}
        api = dict(api) if isinstance(api, dict) else {}
        api["name"] = str(api.get("name") or api.get("api_name") or api.get("title") or normalized["case_name"])[:128]
        if not api.get("url") and api.get("path"):
            api["url"] = api.get("path")
        if not api.get("method") and api.get("http_method"):
            api["method"] = api.get("http_method")
        if "method" in api:
            api["method"] = cls.normalize_http_method(api.get("method"))
        if "json" in api and "json_body" not in api:
            api["json_body"] = api.pop("json")
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
        if not normalized["api"].get("url"):
            missing_fields.append("api.url")
        if normalized["api"].get("method") is None:
            missing_fields.append("api.method")
        if missing_fields:
            raise ValueError("AI调用 create_complete_api_case 时缺少必要入参：" + "、".join(missing_fields))
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
