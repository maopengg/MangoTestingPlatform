"""Registration map for MCP domain tools."""


def domain_registrars(domain: str | None):
    from src.interfaces.mcp.tools.monitoring import register_monitoring_tools
    from src.interfaces.mcp.tools.api import register_api_tools
    from src.interfaces.mcp.tools.data_factory import register_data_factory_tools
    from src.interfaces.mcp.tools.functional_test import register_functional_test_tools
    from src.interfaces.mcp.tools.project import register_project_tools
    from src.interfaces.mcp.tools.pytest import register_pytest_tools
    from src.interfaces.mcp.tools.report import register_report_tools
    from src.interfaces.mcp.tools.scheduled_task import register_scheduled_task_tools
    from src.interfaces.mcp.tools.system import register_system_tools
    from src.interfaces.mcp.tools.system.file import register_system_file_tools
    from src.interfaces.mcp.tools.ui import register_ui_tools
    from src.interfaces.mcp.tools.workbench_todo import register_workbench_todo_tools
    from src.interfaces.mcp.tools.evaluation import register_evaluation_tools

    registrars = {
        "monitoring": register_monitoring_tools,
        "evaluation": register_evaluation_tools,
        "api": register_api_tools,
        "ui": register_ui_tools,
        "pytest": register_pytest_tools,
        "data-factory": register_data_factory_tools,
        "report": register_report_tools,
        "scheduler": register_scheduled_task_tools,
        "functional-test": register_functional_test_tools,
        "file": register_system_file_tools,
        "todo": register_workbench_todo_tools,
    }
    if domain is not None:
        return [("project", register_project_tools), (domain, registrars[domain])]
    return [
        ("monitoring", register_monitoring_tools),
        ("project", register_project_tools),
        ("evaluation", register_evaluation_tools),
        ("api", register_api_tools),
        ("ui", register_ui_tools),
        ("pytest", register_pytest_tools),
        ("scheduler", register_scheduled_task_tools),
        ("data-factory", register_data_factory_tools),
        ("file", register_system_tools),
        ("report", register_report_tools),
        ("functional-test", register_functional_test_tools),
        ("todo", register_workbench_todo_tools),
    ]
