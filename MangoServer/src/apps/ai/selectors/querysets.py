from django.db.models import Prefetch

from src.apps.ai.models import (
    AiAgentContext,
    AiAgentTask,
    AiAgentTaskItem,
    AiAgentTaskStep,
    AiAgentToolCall,
    AiMcpServer,
    AiMcpTool,
    AiSkill,
)


class AiQuerySelector:
    @staticmethod
    def _task_item_prefetch(prefix=""):
        return Prefetch(
            f"{prefix}aiagenttaskitem_set",
            queryset=AiAgentTaskItem.objects.order_by("item_order", "id"),
            to_attr="_presenter_items",
        )

    @staticmethod
    def ai_agent_context():
        return AiAgentContext.objects.all()

    @staticmethod
    def ai_agent_task():
        return AiAgentTask.objects.all()

    @staticmethod
    def ai_agent_task_step():
        return AiAgentTaskStep.objects.all()

    @staticmethod
    def ai_agent_tool_call():
        return AiAgentToolCall.objects.all()

    @staticmethod
    def ai_mcp_server():
        return AiMcpServer.objects.all()

    @staticmethod
    def ai_mcp_tool():
        return AiMcpTool.objects.all()

    @staticmethod
    def ai_skill():
        return AiSkill.objects.all()

    @staticmethod
    def agent_task_details():
        return AiAgentTask.objects.select_related(
            "skill", "skill__user", "skill__update_user", "create_user"
        ).prefetch_related(AiQuerySelector._task_item_prefetch())

    @staticmethod
    def agent_context_details():
        return AiAgentContext.objects.select_related(
            "task",
            "task__skill",
            "task__skill__user",
            "task__skill__update_user",
            "task__create_user",
            "create_user",
        ).prefetch_related(AiQuerySelector._task_item_prefetch("task__"))

    @staticmethod
    def mcp_server_details():
        return AiMcpServer.objects.select_related(
            "project_product",
            "project_product__project",
            "module",
            "module__parent",
            "module__parent__parent",
            "create_user",
            "update_user",
        )

    @staticmethod
    def skill_details():
        return AiSkill.objects.select_related("user", "update_user")

    @staticmethod
    def mcp_tool_details():
        return AiMcpTool.objects.select_related(
            "server",
            "server__project_product",
            "server__project_product__project",
            "server__module",
            "server__module__parent",
            "server__module__parent__parent",
            "server__create_user",
            "server__update_user",
            "project_product",
            "project_product__project",
            "module",
            "module__parent",
            "module__parent__parent",
            "update_user",
            "api_info_binding",
        )

    @staticmethod
    def agent_task_step_details():
        return AiAgentTaskStep.objects.select_related(
            "task",
            "task__skill",
            "task__skill__user",
            "task__skill__update_user",
            "task__create_user",
        ).prefetch_related(AiQuerySelector._task_item_prefetch("task__"))

    @staticmethod
    def agent_tool_call_details():
        return AiAgentToolCall.objects.select_related(
            "task",
            "task__skill",
            "task__skill__user",
            "task__skill__update_user",
            "task__create_user",
            "server",
            "server__project_product",
            "server__project_product__project",
            "server__module",
            "server__module__parent",
            "server__module__parent__parent",
            "server__create_user",
            "server__update_user",
        ).prefetch_related(AiQuerySelector._task_item_prefetch("task__"))
