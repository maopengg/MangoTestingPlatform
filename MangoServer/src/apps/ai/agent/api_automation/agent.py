# -*- coding: utf-8 -*-
from src.apps.ai.agent.base import BaseAgent
from src.apps.ai.enums import AiAgentTaskStatusEnum, AiAgentTaskTypeEnum
from src.apps.ai.enums.role import AgentRole
from .agent_parts.context import ApiAutomationContextMixin
from .agent_parts.execution import ApiAutomationExecutionMixin
from .agent_parts.lookup import ApiAutomationLookupMixin
from .agent_parts.output import ApiAutomationOutputMixin
from .agent_parts.retry import ApiAutomationRetryMixin
from .agent_parts.start import ApiAutomationStartMixin
from .agent_parts.validation import ApiAutomationValidationMixin


class ApiAutomationAgent(ApiAutomationStartMixin, ApiAutomationExecutionMixin, ApiAutomationValidationMixin,
                         ApiAutomationContextMixin, ApiAutomationRetryMixin, ApiAutomationLookupMixin,
                         ApiAutomationOutputMixin, BaseAgent):
    task_type = AiAgentTaskTypeEnum.GENERATE_API_CASE.value
    agent_key = "api_automation"
    fixed_role = AgentRole.API_AUTOMATION_EXPERT
    active_statuses = [
        AiAgentTaskStatusEnum.PENDING.value,
        AiAgentTaskStatusEnum.CLAIMED.value,
        AiAgentTaskStatusEnum.RUNNING.value,
        AiAgentTaskStatusEnum.WAITING_MODEL.value,
    ]
    step_defs = [
        {"key": "collect_context", "name": "收集上下文", "order": 1},
        {"key": "load_capabilities", "name": "加载 MCP 能力", "order": 2},
        {"key": "compile_skill", "name": "编译技能协议", "order": 3},
        {"key": "plan_workflow", "name": "规划工具链", "order": 4},
        {"key": "validate_plan", "name": "校验工具计划", "order": 5},
        {"key": "execute_stages", "name": "执行 MCP 工具链", "order": 6},
        {"key": "verify_api_assets", "name": "校验 API 资产", "order": 7},
        {"key": "execute_api_case", "name": "执行 API Case", "order": 8},
        {"key": "diagnose_and_repair", "name": "诊断和修复", "order": 9},
        {"key": "bind_result", "name": "回填自动化绑定", "order": 10},
        {"key": "post_validate", "name": "写入后校验", "order": 11},
    ]
