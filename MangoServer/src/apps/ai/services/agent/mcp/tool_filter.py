# -*- coding: utf-8 -*-


class AgentMcpToolFilter:
    @staticmethod
    def filter_for_api_automation(tools, existing_api_case_id: int | None = None):
        return list(tools)

    @staticmethod
    def filter_for_readonly(tools):
        return [tool for tool in tools if not tool.write_operation]
