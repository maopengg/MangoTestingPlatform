from __future__ import annotations

import os
import logging
import inspect
from functools import wraps
from datetime import datetime


MCP_HTTP_PATH = "/mcp"
DEFAULT_ALLOWED_HOSTS = [
    "127.0.0.1:*",
    "localhost:*",
    "[::1]:*",
    "qfei-auto-platform-dev.internal.qtech.cn",
    "qfei-auto-platform-test.internal.qtech.cn",
]

DEFAULT_ALLOWED_ORIGINS = [
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
    "https://qfei-auto-platform-dev.internal.qtech.cn",
    "https://qfei-auto-platform-test.internal.qtech.cn",
]

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

# The MCP SDK logs normal Streamable HTTP connection shutdowns as
# ClosedResourceError tracebacks. They are noisy during browser probes and
# short-lived client calls, so keep them out of MangoServer's console logs.
logging.getLogger("mcp.server.streamable_http").setLevel(logging.CRITICAL)


def _mcp_server_info() -> dict:
    from django.conf import settings

    from src.services.mcp_server.common import get_http_headers

    headers = get_http_headers()
    host = headers.get("host") or headers.get("Host")
    forwarded_proto = headers.get("x-forwarded-proto") or headers.get("X-Forwarded-Proto")
    proto = forwarded_proto.split(",", 1)[0].strip() if forwarded_proto else None
    if not proto:
        proto = "https" if headers.get("x-forwarded-ssl") == "on" else "http"
    base_url = f"{proto}://{host}" if host else None
    django_env = os.environ.get("DJANGO_ENV", "master")
    now = datetime.now()
    return {
        "name": "MangoTestingPlatform",
        "mcp_name": "MangoTestingPlatform",
        "environment": django_env,
        "django_env": django_env,
        "settings_module": os.environ.get("DJANGO_SETTINGS_MODULE"),
        "debug": getattr(settings, "DEBUG", None),
        "base_url": base_url,
        "mcp_url": f"{base_url}{MCP_HTTP_PATH}" if base_url else None,
        "mcp_path": MCP_HTTP_PATH,
        "allowed_hosts": _split_env_list("MANGO_MCP_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS),
        "server_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "server_timestamp": int(now.timestamp()),
        "timezone": getattr(settings, "TIME_ZONE", None),
    }


def _split_env_list(name: str, default: list[str]) -> list[str]:
    value = os.environ.get(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _authenticated_tool_method(mcp):
    original_tool = mcp.tool

    def authenticated_tool(*tool_args, **tool_kwargs):
        decorator = original_tool(*tool_args, **tool_kwargs)

        def decorate(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                from src.services.mcp_server.common import log_mcp_tool_call_async, require_mcp_user, user_from_auth_token

                try:
                    bound_arguments = inspect.signature(func).bind_partial(*args, **kwargs)
                    tool_arguments = dict(bound_arguments.arguments)
                except Exception:
                    tool_arguments = {"args": args, "kwargs": kwargs}
                auth_error = require_mcp_user()
                if auth_error:
                    log_mcp_tool_call_async(func.__name__, tool_arguments, auth_error, status_code=401)
                    return auth_error
                user = user_from_auth_token()
                write_guard_error = _mcp_demo_write_guard(func.__name__, user)
                if write_guard_error:
                    log_mcp_tool_call_async(func.__name__, tool_arguments, write_guard_error, status_code=200, user=user)
                    return write_guard_error
                try:
                    result = func(*args, **kwargs)
                except Exception as exc:
                    log_mcp_tool_call_async(
                        func.__name__,
                        tool_arguments,
                        {"success": False, "message": str(exc), "error_code": "MCP_TOOL_EXCEPTION"},
                        status_code=500,
                        user=user,
                    )
                    raise
                log_mcp_tool_call_async(func.__name__, tool_arguments, result, status_code=200, user=user)
                return result

            return decorator(wrapper)

        return decorate

    return authenticated_tool


def _mcp_demo_write_guard(tool_name: str, user) -> dict | None:
    """Apply the same demo-environment write restrictions as IsDeleteMiddleWare."""
    from src.services.mcp_server.common import fail
    from src.settings import IS_DELETE

    if IS_DELETE:
        return None
    if getattr(user, "username", None) in ["admin", "open"]:
        return None

    operation = _mcp_tool_write_operation(tool_name)
    if operation is None:
        return None

    messages = {
        "delete": "演示环境非管理员权限禁止删除，只能执行测试任务",
        "create": "演示环境非管理员权限禁止新增，只能执行测试任务",
        "update": "演示环境非管理员权限禁止修改，只能执行测试任务",
    }
    return fail(
        messages[operation],
        "DEMO_ENV_WRITE_FORBIDDEN",
        {
            "tool": tool_name,
            "operation": operation,
            "allowed_users": ["admin", "open"],
            "current_user": getattr(user, "username", None),
        },
    )


def _mcp_tool_write_operation(tool_name: str) -> str | None:
    allowed_tools = {
        "ensure_user_test_environment",
        "switch_user_test_environment",
        "run_api_info",
        "run_api_case",
        "run_api_case_batch",
        "run_ui_case",
        "run_ui_case_batch",
        "run_ui_page_step",
        "test_ui_element",
        "run_pytest_case",
        "retry_test_report_case",
        "retry_test_report",
        "test_data_factory_datasource_connection",
        "evaluate_test_data_expression",
    }
    if tool_name in allowed_tools:
        return None

    delete_prefixes = (
        "delete_",
        "cleanup_",
        "clear_",
    )
    create_prefixes = (
        "create_",
        "add_",
        "copy_",
        "upload_",
        "bind_",
        "batch_generate_",
        "execute_",
        "debug_run_",
    )
    update_prefixes = (
        "update_",
        "set_",
        "sort_",
        "refresh_",
        "auto_generate_",
        "sync_",
        "push_",
    )
    if tool_name.startswith(delete_prefixes):
        return "delete"
    if tool_name.startswith(create_prefixes):
        return "create"
    if tool_name.startswith(update_prefixes):
        return "update"
    return None


def _logged_public_tool(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        from src.services.mcp_server.common import log_mcp_tool_call_async, user_from_auth_token

        try:
            bound_arguments = inspect.signature(func).bind_partial(*args, **kwargs)
            tool_arguments = dict(bound_arguments.arguments)
        except Exception:
            tool_arguments = {"args": args, "kwargs": kwargs}
        user = None
        try:
            user = user_from_auth_token()
        except Exception:
            pass
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            log_mcp_tool_call_async(
                func.__name__,
                tool_arguments,
                {"success": False, "message": str(exc), "error_code": "MCP_TOOL_EXCEPTION"},
                status_code=500,
                user=user,
            )
            raise
        log_mcp_tool_call_async(func.__name__, tool_arguments, result, status_code=200, user=user)
        return result

    return wrapper


def _transport_security_settings():
    from mcp.server.transport_security import TransportSecuritySettings

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=_env_bool("MANGO_MCP_ENABLE_DNS_REBINDING_PROTECTION", True),
        allowed_hosts=_split_env_list("MANGO_MCP_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS),
        allowed_origins=_split_env_list("MANGO_MCP_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS),
    )


def _platform_capabilities() -> dict:
    return {
        "success": True,
        "message": "操作成功",
        "data": {
            "server": _mcp_server_info(),
            "authentication": {
                "required_for_business_tools": True,
                "header": "Authorization: Bearer <MCP APIKey>",
                "api_key_prefix": "mango_",
                "setup_hint": "请到「系统管理 - 用户管理」复制或生成 MCP APIKey，并配置到 MCP 客户端 Authorization 请求头。",
                "demo_write_guard": {
                    "enabled_when": "IS_DELETE=False",
                    "admin_users": ["admin", "open"],
                    "rule": "演示环境下非管理员禁止 MCP 新增、修改、删除类工具；查询、预览、分析和测试任务执行类工具保留。",
                },
                "public_tools": ["get_mcp_server_info", "get_platform_capabilities"],
            },
            "capabilities": [
                {
                    "name": "server_info",
                    "description": "MCP 服务自身信息、环境和地址",
                    "tools": [
                        "get_mcp_server_info",
                        "get_platform_capabilities",
                    ],
                },
                {
                    "name": "project_context",
                    "description": "项目、用户、测试环境上下文",
                    "tools": [
                        "get_current_user_context",
                        "switch_user_test_environment",
                        "ensure_user_test_environment",
                        "list_test_environments",
                        "list_project_test_objects",
                        "list_project_products",
                        "list_product_modules",
                        "create_product_module",
                        "update_product_module",
                        "preview_delete_product_module_impact",
                        "delete_product_module",
                        "list_case_owners",
                    ],
                },
                {
                    "name": "api_automation",
                    "description": "API 接口、请求头、用例、场景、文件参数引用、执行和结果分析",
                    "tools": [
                        "list_api_headers",
                        "preview_create_api_header_impact",
                        "create_api_header",
                        "update_api_header",
                        "list_api_public_variables",
                        "create_api_public_variable",
                        "update_api_public_variable",
                        "set_api_public_variable_status",
                        "search_api_infos",
                        "get_api_info_detail",
                        "create_api_info",
                        "create_api_info_from_curl",
                        "update_api_info",
                        "create_api_case",
                        "search_api_cases",
                        "get_api_case_detail_full",
                        "update_api_case",
                        "preview_delete_api_case_impact",
                        "delete_api_case",
                        "add_api_case_step",
                        "list_api_case_steps",
                        "sort_api_case_steps",
                        "refresh_api_case_step_from_api_info",
                        "list_api_case_scenarios",
                        "create_api_case_scenario",
                        "update_api_case_scenario",
                        "copy_api_case_scenario",
                        "get_api_assertion_methods",
                        "get_api_assertion_schema",
                        "generate_api_case_scenario_assertions",
                        "generate_api_case_scenario_extractors",
                        "auto_generate_api_case_scenario_schema",
                        "create_complete_api_case",
                        "run_api_info",
                        "run_api_case",
                        "run_api_case_batch",
                        "get_api_case_run_result",
                        "analyze_api_case_failure",
                        "get_api_case_schema",
                    ],
                },
                {
                    "name": "ui_automation",
                    "description": "UI 页面、元素、页面步骤、UI case、方法树、执行和结果分析",
                    "tools": [
                        "get_ui_automation_schema",
                        "get_ui_operation_methods",
                        "get_ui_assertion_methods",
                        "get_ui_public_assertion_methods",
                        "list_ui_public_variables",
                        "create_ui_public_variable",
                        "update_ui_public_variable",
                        "set_ui_public_variable_status",
                        "search_ui_pages",
                        "get_ui_page_detail",
                        "create_ui_page",
                        "update_ui_page",
                        "search_ui_elements",
                        "get_ui_element_detail",
                        "create_ui_element",
                        "update_ui_element",
                        "set_ui_element_iframe",
                        "test_ui_element",
                        "search_ui_page_steps",
                        "get_ui_page_step_detail_full",
                        "create_ui_page_step",
                        "update_ui_page_step",
                        "copy_ui_page_step",
                        "run_ui_page_step",
                        "list_ui_page_step_details",
                        "create_ui_page_step_detail",
                        "update_ui_page_step_detail",
                        "sort_ui_page_step_details",
                        "search_ui_cases",
                        "get_ui_case_detail_full",
                        "create_ui_case",
                        "update_ui_case",
                        "copy_ui_case",
                        "add_ui_case_step",
                        "list_ui_case_steps",
                        "sort_ui_case_steps",
                        "refresh_ui_case_step_cache_data",
                        "run_ui_case",
                        "run_ui_case_batch",
                        "get_ui_case_run_result",
                        "preview_delete_ui_page_impact",
                        "delete_ui_page",
                        "preview_delete_ui_element_impact",
                        "delete_ui_element",
                        "preview_delete_ui_page_step_impact",
                        "delete_ui_page_step",
                        "preview_delete_ui_page_step_detail_impact",
                        "delete_ui_page_step_detail",
                        "preview_delete_ui_case_impact",
                        "delete_ui_case",
                        "preview_delete_ui_case_step_impact",
                        "delete_ui_case_step",
                    ],
                },
                {
                    "name": "pytest_automation",
                    "description": "单元自动化 Pytest 项目绑定、仓库同步、文件读写、执行和安全推送",
                    "tools": [
                        "get_pytest_automation_schema",
                        "list_pytest_products",
                        "get_pytest_product_detail",
                        "create_pytest_product",
                        "update_pytest_product",
                        "sync_pytest_products_from_repo",
                        "read_pytest_product_init_file",
                        "preview_update_pytest_product_init_file_impact",
                        "update_pytest_product_init_file",
                        "preview_push_pytest_repo_impact",
                        "push_pytest_repo",
                        "search_pytest_cases",
                        "get_pytest_case_detail",
                        "sync_pytest_cases",
                        "read_pytest_case_file",
                        "preview_update_pytest_case_file_impact",
                        "update_pytest_case_file",
                        "run_pytest_case",
                        "get_pytest_case_run_result",
                        "preview_delete_pytest_product_impact",
                        "delete_pytest_product",
                        "preview_delete_pytest_case_impact",
                        "delete_pytest_case",
                    ],
                },
                {
                    "name": "api_auth_config",
                    "description": "API Token 授权配置、缓存查看、立即刷新和清理",
                    "tools": [
                        "get_api_auth_config_schema",
                        "list_api_auth_configs",
                        "get_api_auth_config_detail",
                        "create_api_auth_config",
                        "update_api_auth_config",
                        "set_api_auth_config_status",
                        "refresh_api_auth_config",
                        "preview_clear_api_auth_config_cache_impact",
                        "clear_api_auth_config_cache",
                        "get_api_auth_config_cache",
                        "preview_delete_api_auth_config_impact",
                        "delete_api_auth_config",
                        "list_api_auth_time_tasks",
                    ],
                },
                {
                    "name": "data_factory",
                    "description": "数据工厂实体、字段、模板、执行、清理和用例绑定",
                    "tools": [
                        "get_data_factory_schema",
                        "list_data_factory_datasource_aliases",
                        "list_data_factory_datasource_bindings",
                        "list_data_factory_database_tables",
                        "get_data_factory_table_schema",
                        "list_data_factory_entities",
                        "get_data_factory_entity_detail",
                        "create_data_factory_entity",
                        "batch_generate_data_factory_entities",
                        "list_data_factory_fields",
                        "batch_save_data_factory_fields",
                        "preview_data_factory_field_values",
                        "list_data_factory_templates",
                        "get_data_factory_template_detail",
                        "preview_data_factory_template",
                        "preview_run_data_factory_template_impact",
                        "execute_data_factory_template",
                        "preview_delete_data_factory_template_impact",
                        "delete_data_factory_template",
                        "list_data_factory_case_configs",
                        "bind_data_factory_to_case_source",
                        "list_data_factory_executions",
                        "get_data_factory_execution_detail",
                        "preview_cleanup_data_factory_execution_impact",
                        "cleanup_data_factory_execution",
                    ],
                },
                {
                    "name": "system_variable",
                    "description": "平台变量、随机测试数据方法查询和表达式试算",
                    "tools": [
                        "list_test_data_methods",
                        "evaluate_test_data_expression",
                    ],
                },
                {
                    "name": "system_file",
                    "description": "系统文件上传、查询和下载地址获取",
                    "tools": [
                        "list_system_files",
                        "upload_system_file",
                        "get_system_file_download_url",
                    ],
                },
                {
                    "name": "test_report",
                    "description": "测试报告查询、筛选、失败分析和安全重试",
                    "tools": [
                        "get_test_report_schema",
                        "list_test_reports",
                        "get_test_report_detail",
                        "get_test_report_summary",
                        "list_test_report_cases",
                        "get_test_report_trend",
                        "analyze_test_report_failures",
                        "preview_retry_test_report_case_impact",
                        "retry_test_report_case",
                        "preview_retry_test_report_impact",
                        "retry_test_report",
                    ],
                },
            ]
        },
        "warnings": [],
    }


def mcp_asgi_app():
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError:
        return _missing_dependency_app

    from src.services.mcp_server.tools.api_automation import register_api_automation_tools
    from src.services.mcp_server.tools.api_auth_config import register_api_auth_config_tools
    from src.services.mcp_server.tools.data_factory import register_data_factory_tools
    from src.services.mcp_server.tools.project_context import register_project_context_tools
    from src.services.mcp_server.tools.system_file import register_system_file_tools
    from src.services.mcp_server.tools.system_variable import register_system_variable_tools
    from src.services.mcp_server.tools.test_report import register_test_report_tools
    from src.services.mcp_server.tools.ui_automation import register_ui_automation_tools
    from src.services.mcp_server.tools.pytest_automation import register_pytest_automation_tools

    try:
        mcp = FastMCP(
            "MangoTestingPlatform",
            stateless_http=True,
            json_response=True,
            streamable_http_path="/",
            transport_security=_transport_security_settings(),
        )
    except TypeError:
        mcp = FastMCP(
            "MangoTestingPlatform",
            stateless_http=True,
            json_response=True,
        )

    @mcp.tool()
    @_logged_public_tool
    def get_mcp_server_info() -> dict:
        """查询 Mango MCP 服务自身信息，包括环境、地址和服务时间。"""
        return {
            "success": True,
            "message": "操作成功",
            "data": _mcp_server_info(),
            "warnings": [],
        }

    @mcp.tool()
    @_logged_public_tool
    def get_platform_capabilities() -> dict:
        """查询 Mango MCP 当前开放的能力分组。"""
        return _platform_capabilities()

    mcp.tool = _authenticated_tool_method(mcp)

    @mcp.resource("mango://project-product/{project_product_id}")
    def get_project_product_resource(project_product_id: str) -> dict:
        """读取项目产品上下文资源。"""
        from src.apps.auto_system.models import ProjectProduct

        item = ProjectProduct.objects.select_related("project").get(id=int(project_product_id))
        return {
            "id": item.id,
            "name": item.name,
            "project": {"id": item.project.id, "name": item.project.name},
            "api_client_type": item.api_client_type,
            "ui_client_type": item.ui_client_type,
        }

    @mcp.resource("mango://api-info/{api_info_id}")
    def get_api_info_resource(api_info_id: str) -> dict:
        """读取 API 接口定义资源。"""
        from django.forms import model_to_dict
        from src.apps.auto_api.models import ApiInfo

        return model_to_dict(ApiInfo.objects.get(id=int(api_info_id)))

    @mcp.resource("mango://api-case/{case_id}")
    def get_api_case_resource(case_id: str) -> dict:
        """读取完整 API case 树资源。"""
        from src.services.mcp_server.tools.api_automation import _case_tree

        return _case_tree(int(case_id), include_result_data=True)

    @mcp.resource("mango://data-factory/entity/{entity_id}")
    def get_data_factory_entity_resource(entity_id: str) -> dict:
        """读取数据工厂实体和字段规则资源。"""
        from django.forms import model_to_dict
        from src.apps.auto_data_factory.models import DataFactoryEntity, DataFactoryField

        entity = DataFactoryEntity.objects.get(id=int(entity_id))
        fields = [
            model_to_dict(item)
            for item in DataFactoryField.objects.filter(entity_id=entity.id).order_by("sort", "id")
        ]
        return {"entity": model_to_dict(entity), "fields": fields}

    @mcp.resource("mango://data-factory/template/{template_id}")
    def get_data_factory_template_resource(template_id: str) -> dict:
        """读取数据工厂状态模板、实体、字段和缓存变量资源。"""
        from src.apps.auto_data_factory.models import DataFactoryField, DataFactoryTemplate
        from src.services.mcp_server.tools.data_factory import _cache_keys_for_template, _template_summary
        from django.forms import model_to_dict

        template = DataFactoryTemplate.objects.select_related("entity").get(id=int(template_id))
        fields = [
            model_to_dict(item)
            for item in DataFactoryField.objects.filter(entity_id=template.entity_id).order_by("sort", "id")
        ]
        return {
            "template": _template_summary(template),
            "entity": model_to_dict(template.entity),
            "fields": fields,
            "cache_keys": _cache_keys_for_template(template),
        }

    @mcp.resource("mango://data-factory/execution/{execution_id}")
    def get_data_factory_execution_resource(execution_id: str) -> dict:
        """读取数据工厂执行详情资源。"""
        from src.services.mcp_server.tools.data_factory import _execution_detail

        return _execution_detail(int(execution_id))

    @mcp.resource("mango://data-factory/case-config/{source_type}/{source_id}")
    def get_data_factory_case_config_resource(source_type: str, source_id: str) -> dict:
        """读取某个用例来源绑定的数据工厂配置资源。"""
        from src.apps.auto_data_factory.models import DataFactoryCaseConfig
        from src.services.mcp_server.tools.data_factory import _case_config_summary

        queryset = DataFactoryCaseConfig.objects.select_related("template", "template__entity").filter(
            source_type=int(source_type),
            source_id=int(source_id),
        )
        return {"items": [_case_config_summary(item) for item in queryset.order_by("sort", "id")]}

    @mcp.resource("mango://ui-page/{page_id}")
    def get_ui_page_resource(page_id: str) -> dict:
        """读取 UI 页面和元素资源。"""
        from django.forms import model_to_dict
        from src.apps.auto_ui.models import Page, PageElement

        page = Page.objects.get(id=int(page_id))
        elements = [
            model_to_dict(item)
            for item in PageElement.objects.filter(page_id=page.id).order_by("id")
        ]
        return {"page": model_to_dict(page), "elements": elements}

    @mcp.resource("mango://ui-page-step/{page_step_id}")
    def get_ui_page_step_resource(page_step_id: str) -> dict:
        """读取 UI 页面步骤、流程图和步骤详情资源。"""
        from django.forms import model_to_dict
        from src.apps.auto_ui.models import PageSteps, PageStepsDetailed

        page_step = PageSteps.objects.get(id=int(page_step_id))
        details = [
            model_to_dict(item)
            for item in PageStepsDetailed.objects.filter(page_step_id=page_step.id).order_by("step_sort", "id")
        ]
        return {"page_step": model_to_dict(page_step), "details": details}

    @mcp.resource("mango://ui-case/{case_id}")
    def get_ui_case_resource(case_id: str) -> dict:
        """读取完整 UI case 树资源。"""
        from src.services.mcp_server.tools.ui_automation import _case_tree

        return _case_tree(int(case_id), include_result_data=True)

    @mcp.resource("mango://pytest-product/{product_id}")
    def get_pytest_product_resource(product_id: str) -> dict:
        """读取 Pytest 项目绑定资源。"""
        from src.services.mcp_server.tools.pytest_automation import _product_detail

        return _product_detail(int(product_id))

    @mcp.resource("mango://pytest-case/{case_id}")
    def get_pytest_case_resource(case_id: str) -> dict:
        """读取 Pytest case 元信息资源，不直接返回文件内容。"""
        from src.services.mcp_server.tools.pytest_automation import _case_detail

        return _case_detail(int(case_id))

    @mcp.prompt()
    def api_case_from_curl(curl_command: str, project_product_name: str = "", module_name: str = "") -> str:
        """生成根据 curl 创建 API case 的标准提示词。"""
        return (
            "请根据以下 curl 在 MangoTestingPlatform 中创建 API 接口定义、API case、"
            "默认场景参数，并在用户选择测试环境后执行 case。"
            f"\n项目产品：{project_product_name}\n模块：{module_name}\n\ncurl:\n{curl_command}"
        )

    @mcp.prompt()
    def api_failure_analysis(case_id: int) -> str:
        """生成 API case 失败分析提示词。"""
        return (
            f"请读取 mango://api-case/{case_id}，分析最近一次 API case 执行失败原因，"
            "给出证据和可操作修复建议。"
        )

    @mcp.prompt()
    def data_factory_template_from_table(
        project_product_name: str = "",
        module_name: str = "",
        table_name: str = "",
        business_state: str = "",
    ) -> str:
        """生成根据数据库表创建数据工厂模板的标准提示词。"""
        return (
            "请通过 Mango 数据工厂 MCP 查询数据源、表结构、实体和字段规则，"
            "为指定业务状态创建或更新数据工厂实体、字段规则和状态模板。"
            f"\n项目产品：{project_product_name}\n模块：{module_name}"
            f"\n表名：{table_name}\n业务状态：{business_state}"
            "\n要求先预览字段生成值，再创建模板；返回 entity_id、template_id 和可用缓存变量。"
        )

    @mcp.prompt()
    def bind_data_factory_for_api_case(case_id: int, scenario_id: int | None = None, template_name: str = "") -> str:
        """生成给 API case 或场景绑定数据工厂的标准提示词。"""
        target = f"API 场景 {scenario_id}" if scenario_id else f"API case {case_id}"
        return (
            f"请为 {target} 选择并绑定数据工厂模板。"
            f"\n期望模板：{template_name}"
            "\n步骤：查询模板详情，确认字段和 cache_keys；绑定到场景优先使用 source_type=3；"
            "将请求体变量改为 `${{模板名.字段名}}`；执行 case 并根据 data_factory_cache_data 验证变量。"
        )

    register_project_context_tools(mcp)
    register_api_automation_tools(mcp)
    register_ui_automation_tools(mcp)
    register_pytest_automation_tools(mcp)
    register_api_auth_config_tools(mcp)
    register_data_factory_tools(mcp)
    register_system_variable_tools(mcp)
    register_system_file_tools(mcp)
    register_test_report_tools(mcp)
    return mcp.streamable_http_app()


async def _missing_dependency_app(scope, receive, send):
    body = (
        b'{"success": false, "message": "MCP dependency is not installed. '
        b'Run pip install \\"mcp[cli]==1.17.0\\".", "error_code": "MCP_DEPENDENCY_MISSING"}'
    )
    await send(
        {
            "type": "http.response.start",
            "status": 503,
            "headers": [(b"content-type", b"application/json; charset=utf-8")],
        }
    )
    await send({"type": "http.response.body", "body": body})
