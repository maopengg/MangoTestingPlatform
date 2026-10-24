# -*- coding: utf-8 -*-
from django.urls import path

from src.apps.ai.api.views.agent_context import AiAgentContextCRUD
from src.apps.ai.api.views.agent_task import AiAgentTaskCRUD, AiAgentTaskViews
from src.apps.ai.api.views.assistant_message import AiAssistantMessageViews
from src.apps.ai.api.views.assistant_session import AiAssistantViews
from src.apps.ai.api.views.mcp_server import AiMcpServerCRUD, AiMcpServerViews
from src.apps.ai.api.views.mcp_tool import AiMcpToolCRUD, AiMcpToolViews
from src.apps.ai.api.views.skill import AiSkillCRUD, AiSkillViews

urlpatterns = [
    path("skill", AiSkillCRUD.as_view()),
    path("skill/download", AiSkillViews.as_view({"get": "download"})),
    path("skill/publish", AiSkillViews.as_view({"post": "publish"})),
    path("skill/disable", AiSkillViews.as_view({"post": "disable"})),
    path("skill/archive", AiSkillViews.as_view({"post": "archive"})),
    path("mcp/server", AiMcpServerCRUD.as_view()),
    path("mcp/server/test", AiMcpServerViews.as_view({"post": "test"})),
    path("mcp/server/refresh-status", AiMcpServerViews.as_view({"post": "refresh_status"})),
    path("mcp/server/builtin", AiMcpServerViews.as_view({"post": "builtin"})),
    path("mcp/server/sync-tools", AiMcpServerViews.as_view({"post": "sync_tools"})),
    path("mcp/tool", AiMcpToolCRUD.as_view()),
    path("mcp/tool/status", AiMcpToolViews.as_view({"put": "status"})),
    path("mcp/tool/call", AiMcpToolViews.as_view({"post": "call"})),
    path("mcp/tool/import-api-info", AiMcpToolViews.as_view({"post": "import_api_info"})),
    path("task", AiAgentTaskCRUD.as_view()),
    path("task/detail", AiAgentTaskViews.as_view({"get": "task_detail"})),
    path("task/step", AiAgentTaskViews.as_view({"get": "step"})),
    path("task/tool-call", AiAgentTaskViews.as_view({"get": "tool_call"})),
    path("task/retry", AiAgentTaskViews.as_view({"post": "retry"})),
    path("agent/run/detail", AiAgentTaskViews.as_view({"get": "run_detail"})),
    path("agent/run/steps", AiAgentTaskViews.as_view({"get": "run_steps"})),
    path("agent/run/artifacts", AiAgentTaskViews.as_view({"get": "run_artifacts"})),
    path("agent/run/evidence", AiAgentTaskViews.as_view({"get": "run_evidence"})),
    path("agent/run/events", AiAgentTaskViews.as_view({"get": "run_events"})),
    path("agent/run/retry", AiAgentTaskViews.as_view({"post": "retry"})),
    path("agent/run/cancel", AiAgentTaskViews.as_view({"post": "run_cancel"})),
    path("agent/run/confirm", AiAgentTaskViews.as_view({"post": "run_confirm"})),
    path("agent/context", AiAgentContextCRUD.as_view()),
    path("assistant/status", AiAssistantViews.as_view({"get": "status"})),
    path("assistant/session", AiAssistantViews.as_view({"get": "session"})),
    path("assistant/session/list", AiAssistantViews.as_view({"get": "sessions"})),
    path("assistant/session/create", AiAssistantViews.as_view({"post": "create_session"})),
    path("assistant/message", AiAssistantMessageViews.as_view({"get": "messages", "post": "message"})),
    path("assistant/message/stream", AiAssistantMessageViews.as_view({"post": "message_stream"})),
    path("assistant/tool-confirm", AiAssistantMessageViews.as_view({"post": "tool_confirm"})),
    path("assistant/clear", AiAssistantViews.as_view({"post": "clear"})),
    path("agent/functional-case/start", AiAgentTaskViews.as_view({"post": "functional_case_start"})),
    path("agent/functional-case/status", AiAgentTaskViews.as_view({"get": "functional_case_status"})),
    path("agent/functional-case/steps", AiAgentTaskViews.as_view({"get": "functional_case_steps"})),
    path("agent/functional-case/retry", AiAgentTaskViews.as_view({"post": "functional_case_retry"})),
    path("agent/api-automation/start", AiAgentTaskViews.as_view({"post": "api_automation_start"})),
    path("agent/api-automation/status", AiAgentTaskViews.as_view({"get": "api_automation_status"})),
    path("agent/api-automation/steps", AiAgentTaskViews.as_view({"get": "api_automation_steps"})),
    path("agent/api-automation/retry", AiAgentTaskViews.as_view({"post": "api_automation_retry"})),
]
