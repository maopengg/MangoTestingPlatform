# -*- coding: utf-8 -*-
from src.apps.ai.agent.api_automation.result_extractor import ApiAutomationResultExtractor
from src.apps.ai.models import AiAgentTask, AiMcpTool
from src.apps.ai.services.agent.mcp.tool_runner import AgentMcpToolRunner
from src.apps.ai.services.core import AiTaskService, mask_sensitive


class ApiCaseExecutionService:
    @classmethod
    def try_run_api_case(cls, task: AiAgentTask, tool_map: dict[str, AiMcpTool], api_case_id: int,
                         user_id: int | None) -> dict | None:
        run_tool_name = None
        for safe_name, tool in tool_map.items():
            if tool.name == "run_api_case":
                run_tool_name = safe_name
                break
        if not run_tool_name:
            return None
        tool = tool_map[run_tool_name]
        arguments = {"case_id": api_case_id}
        AiTaskService.update_progress(task, 88, "执行 API Case 完成", f"正在通过 MCP 执行 API Case：{api_case_id}")
        result = AgentMcpToolRunner.call(task, tool, arguments, user_id)
        return {
            "tool": tool.name,
            "arguments": mask_sensitive(arguments),
            "result": mask_sensitive(result),
            "error_message": ApiAutomationResultExtractor.extract_mcp_error_message(result),
            "auto_invoked": True,
            "execution_record_id": getattr(task, "last_tool_call_id", None),
        }
