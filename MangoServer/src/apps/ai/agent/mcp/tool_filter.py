# -*- coding: utf-8 -*-


class AgentMcpToolFilter:
    API_BLOCKED_TOOL_NAMES = {
        "delete_api_case",
        "preview_delete_api_case_impact",
        "delete_data_factory_template",
        "preview_delete_data_factory_template_impact",
        "cleanup_data_factory_execution",
        "preview_cleanup_data_factory_execution_impact",
    }
    API_UPDATE_EXCLUDED_TOOL_NAMES = {
        "create_api_case",
        "create_complete_api_case",
        "search_api_cases",
    }

    @classmethod
    def filter_for_api_automation(cls, tools, existing_api_case_id: int | None = None):
        result = [tool for tool in tools if tool.name not in cls.API_BLOCKED_TOOL_NAMES]
        if existing_api_case_id:
            result = [tool for tool in result if tool.name not in cls.API_UPDATE_EXCLUDED_TOOL_NAMES]
        return result

    @staticmethod
    def filter_for_readonly(tools):
        return [tool for tool in tools if not tool.write_operation]
