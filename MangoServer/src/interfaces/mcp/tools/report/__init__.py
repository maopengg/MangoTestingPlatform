from __future__ import annotations

from .execution_result import register_execution_result_tools
from .test_report import register_test_report_tools


def register_report_tools(mcp):
    register_test_report_tools(mcp)
    register_execution_result_tools(mcp)
