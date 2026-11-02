from __future__ import annotations

import inspect
import json
import logging
import os
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime
from functools import wraps

from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.functional_test.presenters import format_case, format_case_list, format_context_resource, format_suite, \
    prepare_case_list_queryset, prepare_case_queryset, prepare_context_resource_queryset, prepare_suite_queryset
from src.apps.functional_test.selectors.querysets import FunctionalTestQuerySelector
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector

MCP_HTTP_PATH = "/mcp"
LOCAL_ALLOWED_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
LOCAL_ALLOWED_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]

MCP_DOMAIN_PATHS = {
    "evaluation": "/mcp/evaluation",
    "api": "/mcp/api",
    "ui": "/mcp/ui",
    "pytest": "/mcp/pytest",
    "data-factory": "/mcp/data-factory",
    "report": "/mcp/report",
    "scheduler": "/mcp/scheduler",
    "functional-test": "/mcp/functional-test",
    "file": "/mcp/file",
    "todo": "/mcp/todo",
}

DOMAIN_RESOURCE_COMPONENTS = {
    "api": {"get_project_product_resource", "get_api_info_resource", "get_api_case_resource"},
    "ui": {"get_project_product_resource", "get_ui_page_resource", "get_ui_page_step_resource", "get_ui_case_resource"},
    "pytest": {"get_project_product_resource", "get_pytest_product_resource", "get_pytest_case_resource"},
    "data-factory": {
        "get_project_product_resource",
        "get_data_factory_entity_resource",
        "get_data_factory_template_resource",
        "get_data_factory_execution_resource",
        "get_data_factory_case_config_resource",
    },
    "functional-test": {
        "get_project_product_resource",
        "get_functional_test_suite_resource",
        "get_functional_test_case_resource",
        "get_functional_test_context_resource",
    },
}

GLOBAL_RESOURCE_COMPONENTS = {
    "get_mcp_skill_catalog_resource",
    "get_mcp_skill_resource",
}

DOMAIN_PROMPT_COMPONENTS = {
    "api": {"api_case_from_curl", "api_failure_analysis"},
    "data-factory": {"data_factory_template_from_table", "bind_data_factory_for_api_case"},
}

GLOBAL_PROMPT_COMPONENTS = {"use_mcp_skill"}

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

# The MCP SDK logs normal Streamable HTTP connection shutdowns as
# ClosedResourceError tracebacks. They are noisy during browser probes and
# short-lived client calls, so keep them out of MangoServer's console logs.
logging.getLogger("mcp.server.streamable_http").setLevel(logging.CRITICAL)


def _mcp_server_info(mcp_path: str = MCP_HTTP_PATH, domain: str | None = None) -> dict:
    from django.conf import settings

    from src.interfaces.mcp.common import get_http_headers

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
        "version": getattr(settings, "VERSION", None),
        "settings_module": os.environ.get("DJANGO_SETTINGS_MODULE"),
        "debug": getattr(settings, "DEBUG", None),
        "base_url": base_url,
        "mcp_url": f"{base_url}{mcp_path}" if base_url else None,
        "mcp_path": mcp_path,
        "domain": domain or "all",
        "domain_endpoints": {
            name: f"{base_url}{path}" if base_url else path
            for name, path in MCP_DOMAIN_PATHS.items()
        },
        "allowed_hosts": _mcp_allowed_hosts(),
        "allowed_origins": _mcp_allowed_origins(),
        "server_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "server_timestamp": int(now.timestamp()),
        "timezone": getattr(settings, "TIME_ZONE", None),
    }


def _split_env_list(name: str, default: list[str]) -> list[str]:
    value = os.environ.get(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _mcp_allowed_hosts() -> list[str]:
    from django.conf import settings

    return _split_env_list("MANGO_MCP_ALLOWED_HOSTS", getattr(settings, "MCP_ALLOWED_HOSTS", LOCAL_ALLOWED_HOSTS))


def _mcp_allowed_origins() -> list[str]:
    from django.conf import settings

    return _split_env_list(
        "MANGO_MCP_ALLOWED_ORIGINS",
        getattr(settings, "MCP_ALLOWED_ORIGINS", LOCAL_ALLOWED_ORIGINS),
    )


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


class McpAuthorizationContextApp:
    """Keep the raw ASGI Authorization header available throughout an MCP request."""

    def __init__(self, app):
        self.app = app

    def __getattr__(self, name):
        return getattr(self.app, name)

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        from src.interfaces.mcp.common import bind_authorization_header, reset_authorization_header

        authorization = next(
            (
                value.decode("latin-1")
                for key, value in scope.get("headers", [])
                if key.lower() == b"authorization"
            ),
            None,
        )
        context_token = bind_authorization_header(authorization)
        try:
            return await self.app(scope, receive, send)
        finally:
            reset_authorization_header(context_token)


class McpDomainPathApp:
    """Make domain endpoints work with the canonical no-trailing-slash MCP URL."""

    def __init__(self, app):
        self.app = app

    def __getattr__(self, name):
        return getattr(self.app, name)

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and scope.get("path") in {f"/{name}" for name in MCP_DOMAIN_PATHS}:
            scope = {**scope, "path": f"{scope['path']}/"}
        root_path = scope.get("root_path", "")
        path = scope.get("path", "")
        if scope.get("type") == "http" and root_path and not path.startswith(root_path + "/"):
            scope = {**scope, "path": root_path + path}
        return await self.app(scope, receive, send)


def _tool_operation(name: str) -> str:
    if name == "stop_evaluation_case_execution":
        return "execute"
    if name.startswith("agent_ui_"):
        return "read" if name == "agent_ui_get_case" else "execute"
    if name.startswith(("delete_", "batch_delete_", "archive_", "batch_archive_", "cleanup_", "clear_", "unbind_")):
        return "delete"
    if name.startswith(("create_", "add_", "upload_", "import_", "batch_generate_", "batch_upload_", "batch_upsert_")):
        return "create"
    if name.startswith(("update_", "set_", "sort_", "copy_", "sync_", "push_", "save_", "replace_", "bind_", "publish_",
                        "unpublish_")):
        return "update"
    if name.startswith(("run_", "execute_", "trigger_", "refresh_", "retry_")):
        return "execute"
    return "read"


def _standard_tool_kwargs(name: str, domain: str, tool_kwargs: dict) -> dict:
    operation = _tool_operation(name)
    result = dict(tool_kwargs)
    result.setdefault("title", name.replace("_", " ").title())
    result["tags"] = set(result.get("tags") or ()) | {domain}
    result.setdefault(
        "annotations",
        {
            "readOnlyHint": operation == "read",
            "destructiveHint": operation == "delete",
            "idempotentHint": operation in {"read", "update", "delete"},
            "openWorldHint": operation in {"execute", "create", "update", "delete"},
        },
    )
    meta = dict(result.get("meta") or {})
    meta["mango"] = {**dict(meta.get("mango") or {}), "domain": domain, "operation": operation}
    result["meta"] = meta
    return result


def _mcp_expected_exception_result(error: Exception) -> tuple[dict, int] | None:
    from src.common.exceptions.normalization import normalize_expected_exception
    from src.interfaces.mcp.common import fail

    normalized = normalize_expected_exception(error)
    if not normalized:
        return None
    return (
        fail(normalized.message, normalized.error_code, normalized.details),
        normalized.log_status_code,
    )


def _mcp_failure_result(
        error: Exception,
        operation: str,
        generic_message: str,
        generic_code: str,
        details: dict,
) -> tuple[dict, int]:
    from src.interfaces.mcp.common import fail

    expected = _mcp_expected_exception_result(error)
    if expected:
        return expected
    _report_mcp_system_error(error, operation)
    return fail(generic_message, generic_code, details), 500


def _authenticated_tool_method(mcp, domain: str):
    original_tool = mcp.tool

    def authenticated_tool(*tool_args, **tool_kwargs):
        def decorate(func):
            name = tool_kwargs.get("name") or func.__name__
            standard_kwargs = _standard_tool_kwargs(name, domain, tool_kwargs)
            standard_kwargs.setdefault(
                "description",
                inspect.getdoc(func) or f"执行 {name.replace('_', ' ')} 操作。",
            )
            decorator = original_tool(*tool_args, **standard_kwargs)
            if inspect.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    from django.db import close_old_connections
                    from src.interfaces.mcp.authentication import filter_scoped_result
                    from src.interfaces.mcp.common import log_mcp_tool_call_async, require_mcp_user, \
                        user_from_auth_token

                    tool_arguments = _mcp_tool_arguments(func, args, kwargs)
                    close_old_connections()
                    auth_error = require_mcp_user()
                    if auth_error:
                        log_mcp_tool_call_async(func.__name__, tool_arguments, auth_error, status_code=401)
                        return auth_error
                    user = user_from_auth_token()
                    try:
                        result = filter_scoped_result(user, await func(*args, **kwargs))
                    except Exception as exc:
                        result, status_code = _mcp_failure_result(
                            exc,
                            f'tool:{func.__name__}',
                            "MCP 工具执行异常，请联系管理员查看服务日志。",
                            "MCP_TOOL_EXCEPTION",
                            {"tool": func.__name__},
                        )
                        log_mcp_tool_call_async(
                            func.__name__,
                            tool_arguments,
                            result,
                            status_code=status_code,
                            user=user,
                        )
                        return result
                    finally:
                        close_old_connections()
                    log_mcp_tool_call_async(func.__name__, tool_arguments, result, status_code=200, user=user)
                    return result

                return decorator(async_wrapper)

            @wraps(func)
            def wrapper(*args, **kwargs):
                from django.db import close_old_connections
                from src.interfaces.mcp.authentication import filter_scoped_result
                from src.interfaces.mcp.common import log_mcp_tool_call_async, require_mcp_user, user_from_auth_token

                tool_arguments = _mcp_tool_arguments(func, args, kwargs)
                close_old_connections()
                auth_error = require_mcp_user()
                if auth_error:
                    log_mcp_tool_call_async(func.__name__, tool_arguments, auth_error, status_code=401)
                    return auth_error
                user = user_from_auth_token()
                try:
                    result = filter_scoped_result(user, func(*args, **kwargs))
                except Exception as exc:
                    result, status_code = _mcp_failure_result(
                        exc,
                        f'tool:{func.__name__}',
                        "MCP 工具执行异常，请联系管理员查看服务日志。",
                        "MCP_TOOL_EXCEPTION",
                        {"tool": func.__name__},
                    )
                    log_mcp_tool_call_async(
                        func.__name__,
                        tool_arguments,
                        result,
                        status_code=status_code,
                        user=user,
                    )
                    return result
                finally:
                    close_old_connections()
                log_mcp_tool_call_async(func.__name__, tool_arguments, result, status_code=200, user=user)
                return result

            return decorator(wrapper)

        return decorate

    return authenticated_tool


def _mcp_tool_arguments(func, args, kwargs) -> dict:
    try:
        bound_arguments = inspect.signature(func).bind_partial(*args, **kwargs)
        return dict(bound_arguments.arguments)
    except Exception:
        return {"args": args, "kwargs": kwargs}


def _report_mcp_system_error(error: Exception, operation: str) -> None:
    from src.apps.system.enums import RuntimeServiceName
    from src.common.enums.system_error import SystemErrorEventSource
    from src.common.decorators.system_error import report_system_error

    report_system_error(
        error,
        source=SystemErrorEventSource.MCP,
        request_path=operation,
        service_name=RuntimeServiceName.MCP,
    )


def _logged_public_tool(func):
    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            from src.interfaces.mcp.common import log_mcp_tool_call_async, user_from_auth_token

            tool_arguments = _mcp_tool_arguments(func, args, kwargs)
            user = None
            try:
                user = user_from_auth_token()
            except Exception:
                pass
            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                expected = _mcp_expected_exception_result(exc)
                if expected:
                    result, status_code = expected
                    log_mcp_tool_call_async(
                        func.__name__, tool_arguments, result, status_code=status_code, user=user,
                    )
                    return result
                _report_mcp_system_error(exc, f'public-tool:{func.__name__}')
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

        return async_wrapper

    @wraps(func)
    def wrapper(*args, **kwargs):
        from src.interfaces.mcp.common import log_mcp_tool_call_async, user_from_auth_token

        tool_arguments = _mcp_tool_arguments(func, args, kwargs)
        user = None
        try:
            user = user_from_auth_token()
        except Exception:
            pass
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            expected = _mcp_expected_exception_result(exc)
            if expected:
                result, status_code = expected
                log_mcp_tool_call_async(
                    func.__name__, tool_arguments, result, status_code=status_code, user=user,
                )
                return result
            _report_mcp_system_error(exc, f'public-tool:{func.__name__}')
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


def _logged_authenticated_resource(func):
    """Authenticate and log MCP resource reads."""
    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            from django.db import close_old_connections
            from src.interfaces.mcp.common import log_mcp_tool_call_async, require_mcp_user, user_from_auth_token

            resource_arguments = _mcp_tool_arguments(func, args, kwargs)
            resource_name = f"resource:{func.__name__}"
            close_old_connections()
            auth_error = require_mcp_user()
            if auth_error:
                log_mcp_tool_call_async(resource_name, resource_arguments, auth_error, status_code=401)
                return auth_error
            user = user_from_auth_token()
            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                result, status_code = _mcp_failure_result(
                    exc,
                    resource_name,
                    "MCP 资源读取异常，请联系管理员查看服务日志。",
                    "MCP_RESOURCE_EXCEPTION",
                    {"resource": func.__name__},
                )
                log_mcp_tool_call_async(
                    resource_name, resource_arguments, result, status_code=status_code, user=user,
                )
                return result
            finally:
                close_old_connections()
            log_mcp_tool_call_async(resource_name, resource_arguments, result, status_code=200, user=user)
            return result

        return async_wrapper

    @wraps(func)
    def wrapper(*args, **kwargs):
        from django.db import close_old_connections
        from src.interfaces.mcp.common import log_mcp_tool_call_async, require_mcp_user, user_from_auth_token

        resource_arguments = _mcp_tool_arguments(func, args, kwargs)
        resource_name = f"resource:{func.__name__}"
        close_old_connections()
        auth_error = require_mcp_user()
        if auth_error:
            log_mcp_tool_call_async(resource_name, resource_arguments, auth_error, status_code=401)
            return auth_error
        user = user_from_auth_token()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            result, status_code = _mcp_failure_result(
                exc,
                resource_name,
                "MCP 资源读取异常，请联系管理员查看服务日志。",
                "MCP_RESOURCE_EXCEPTION",
                {"resource": func.__name__},
            )
            log_mcp_tool_call_async(
                resource_name, resource_arguments, result, status_code=status_code, user=user,
            )
            return result
        finally:
            close_old_connections()
        log_mcp_tool_call_async(resource_name, resource_arguments, result, status_code=200, user=user)
        return result

    return wrapper


def _domain_component_transform(domain: str | None):
    from fastmcp.server.transforms import Transform

    class DomainComponentTransform(Transform):
        @staticmethod
        def _resource_allowed(name: str) -> bool:
            return (
                    domain is None
                    or name in GLOBAL_RESOURCE_COMPONENTS
                    or name in DOMAIN_RESOURCE_COMPONENTS.get(domain, set())
            )

        @staticmethod
        def _prompt_allowed(name: str) -> bool:
            return (
                    domain is None
                    or name in GLOBAL_PROMPT_COMPONENTS
                    or name in DOMAIN_PROMPT_COMPONENTS.get(domain, set())
            )

        async def list_resource_templates(self, templates):
            return [template for template in templates if self._resource_allowed(template.name)]

        async def get_resource_template(self, uri, call_next, *, version=None):
            template = await call_next(uri, version=version)
            return template if template and self._resource_allowed(template.name) else None

        async def list_prompts(self, prompts):
            return [prompt for prompt in prompts if self._prompt_allowed(prompt.name)]

        async def get_prompt(self, name, call_next, *, version=None):
            if not self._prompt_allowed(name):
                return None
            return await call_next(name, version=version)

    return DomainComponentTransform()


def mcp_asgi_app(domain: str | None = None):
    try:
        from fastmcp import FastMCP
    except ModuleNotFoundError:
        return _missing_dependency_app

    from django.conf import settings

    from src.interfaces.mcp.authentication import MangoAuthorizationMiddleware, TOKEN_VERIFIER

    endpoint_path = MCP_DOMAIN_PATHS.get(domain, MCP_HTTP_PATH)
    mcp = FastMCP(
        f"MangoTestingPlatform-{domain or 'all'}",
        version=getattr(settings, "VERSION", None),
        instructions=(
            "Mango 测试平台标准 MCP 服务。调用能力受当前用户角色权限、部门项目范围和超级管理员身份约束。"
            "本服务同时发布版本化 Skill：连接后先读取 mango://skills/catalog，"
            "根据任务匹配 title/category/description，再读取对应 mango://skills/{skill_name}。"
            "必须先遵循 SKILL.md，并按其路由读取 references 后再调用业务工具。"
            "客户端可用 list_mcp_skills/get_mcp_skill 兼容不支持 MCP Resource 的场景，"
            "并通过 known_versions 自动判断是否需要获取更新。"
        ),
        auth=TOKEN_VERIFIER,
        middleware=[MangoAuthorizationMiddleware()],
        transforms=[_domain_component_transform(domain)],
        strict_input_validation=True,
        dereference_schemas=True,
        list_page_size=1000,
        mask_error_details=True,
    )

    @mcp.tool(**_standard_tool_kwargs("get_mcp_server_info", "server", {}))
    @_logged_public_tool
    def get_mcp_server_info() -> dict:
        """查询 Mango MCP 服务自身信息，包括环境、地址和服务时间。"""
        from src.interfaces.mcp.skill_catalog import McpSkillCatalogService, SKILL_CATALOG_URI

        skill_catalog = {"catalog_uri": SKILL_CATALOG_URI, "available": False}
        try:
            catalog = McpSkillCatalogService.catalog()
            skill_catalog.update({
                "available": True,
                "catalog_version": catalog["catalog_version"],
                "skill_count": catalog["skill_count"],
            })
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        return {
            "success": True,
            "message": "操作成功",
            "data": {**_mcp_server_info(endpoint_path, domain), "skill_catalog": skill_catalog},
            "warnings": [],
        }

    @mcp.tool(**_standard_tool_kwargs("list_mcp_skills", "server", {}))
    @_logged_public_tool
    def list_mcp_skills(
            known_versions: dict[str, str] | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询 MCP 发布的全部 Skill 及内容版本。

        客户端连接后应先调用本工具；known_versions 格式为 {skill_name: sha256}，
        返回的 update_available=true 表示服务端 Skill 已更新，需要重新调用 get_mcp_skill。
        """
        from src.interfaces.mcp.common import fail
        from src.interfaces.mcp.skill_catalog import McpSkillCatalogService

        try:
            catalog = McpSkillCatalogService.catalog(known_versions)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return fail(str(exc), "MCP_SKILL_CATALOG_INVALID")
        page = max(int(page or 1), 1)
        page_size = min(max(int(page_size or 10), 1), 100)
        start = (page - 1) * page_size
        items = catalog.pop("skills")
        return {
            "success": True,
            "message": "MCP Skill 目录查询成功",
            "data": {
                **catalog,
                "items": items[start: start + page_size],
                "count": len(items),
                "page": page,
                "page_size": page_size,
            },
            "warnings": [],
        }

    @mcp.tool(**_standard_tool_kwargs("get_mcp_skill", "server", {}))
    @_logged_public_tool
    def get_mcp_skill(
            skill_name: str,
            known_version: str | None = None,
            file_path: str | None = None,
            include_files: bool = True,
    ) -> dict:
        """获取 introductions.json 中已开放给 MCP 的 Skill 及文件内容。

        默认返回该 Skill 的完整文件包；file_path 可只读取一个 references/scripts/assets 文件。
        known_version 与当前内容哈希一致时返回 not_modified=true，客户端无需重复更新。
        """
        from src.interfaces.mcp.common import fail
        from src.interfaces.mcp.skill_catalog import McpSkillCatalogService

        try:
            data = McpSkillCatalogService.get_skill(
                skill_name,
                known_version=known_version,
                file_path=file_path,
                include_files=include_files,
            )
        except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
            return fail(
                str(exc),
                "MCP_SKILL_NOT_FOUND",
                {"skill_name": skill_name, "file_path": file_path},
            )
        return {
            "success": True,
            "message": "MCP Skill 获取成功",
            "data": data,
            "warnings": [],
        }

    native_tool_method = mcp.tool

    @mcp.resource("mango://skills/catalog")
    @_logged_authenticated_resource
    def get_mcp_skill_catalog_resource() -> dict:
        """读取 introductions.json 中已开放给 MCP 的 Skill 及版本目录。"""
        from src.interfaces.mcp.skill_catalog import McpSkillCatalogService

        return McpSkillCatalogService.catalog()

    @mcp.resource("mango://skills/{skill_name}")
    @_logged_authenticated_resource
    def get_mcp_skill_resource(skill_name: str) -> dict:
        """读取指定 Skill 的完整文件包；入口为 SKILL.md。"""
        from src.interfaces.mcp.common import fail
        from src.interfaces.mcp.skill_catalog import McpSkillCatalogService

        try:
            return McpSkillCatalogService.get_skill(skill_name, include_files=True)
        except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
            return fail(
                str(exc),
                "MCP_SKILL_NOT_FOUND",
                {"skill_name": skill_name},
            )

    @mcp.resource("mango://project-product/{project_product_id}")
    @_logged_authenticated_resource
    def get_project_product_resource(project_product_id: str) -> dict:
        """读取项目产品上下文资源。"""

        item = TestCenterQuerySelector.project_product().select_related("project").get(id=int(project_product_id))
        return {
            "id": item.id,
            "name": item.name,
            "project": {"id": item.project.id, "name": item.project.name},
            "api_client_type": item.api_client_type,
            "ui_client_type": item.ui_client_type,
        }

    @mcp.resource("mango://api-info/{api_info_id}")
    @_logged_authenticated_resource
    def get_api_info_resource(api_info_id: str) -> dict:
        """读取 API 接口定义资源。"""
        from django.forms import model_to_dict
        from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService

        runtime = ApiInfoRuntimeService.resolve_runtime(int(api_info_id), allow_draft=True)
        data = model_to_dict(runtime)
        data.update(ApiInfoRuntimeService.capture_runtime_payload(runtime))
        return data

    @mcp.resource("mango://api-case/{case_id}")
    @_logged_authenticated_resource
    def get_api_case_resource(case_id: str) -> dict:
        """读取完整 API case 树资源。"""
        from src.interfaces.mcp.tools.api.helper_parts.case_result import _case_tree

        return _case_tree(int(case_id), include_result_data=True)

    @mcp.resource("mango://data-factory/entity/{entity_id}")
    @_logged_authenticated_resource
    def get_data_factory_entity_resource(entity_id: str) -> dict:
        """读取数据实体和字段规则资源。"""
        from django.forms import model_to_dict

        entity = DataFactoryQuerySelector.data_factory_entity().get(id=int(entity_id))
        fields = [
            model_to_dict(item)
            for item in DataFactoryQuerySelector.data_factory_field().filter(entity_id=entity.id).order_by("sort", "id")
        ]
        return {"entity": model_to_dict(entity), "fields": fields}

    @mcp.resource("mango://data-factory/template/{template_id}")
    @_logged_authenticated_resource
    def get_data_factory_template_resource(template_id: str) -> dict:
        """读取数据工厂状态模板、实体、字段和缓存变量资源。"""
        from src.interfaces.mcp.tools.data_factory.helpers import _cache_keys_for_template, _template_summary
        from django.forms import model_to_dict

        template = DataFactoryQuerySelector.data_factory_template().select_related("entity").get(id=int(template_id))
        fields = [
            model_to_dict(item)
            for item in
            DataFactoryQuerySelector.data_factory_field().filter(entity_id=template.entity_id).order_by("sort", "id")
        ]
        return {
            "template": _template_summary(template),
            "entity": model_to_dict(template.entity),
            "fields": fields,
            "cache_keys": _cache_keys_for_template(template),
        }

    @mcp.resource("mango://data-factory/execution/{execution_id}")
    @_logged_authenticated_resource
    def get_data_factory_execution_resource(execution_id: str) -> dict:
        """读取数据工厂执行详情资源。"""
        from src.interfaces.mcp.tools.data_factory.helpers import _execution_detail

        return _execution_detail(int(execution_id))

    @mcp.resource("mango://data-factory/case-config/{source_type}/{source_id}")
    @_logged_authenticated_resource
    def get_data_factory_case_config_resource(source_type: str, source_id: str) -> dict:
        """读取某个用例来源绑定的数据工厂配置资源。"""
        from src.interfaces.mcp.tools.data_factory.helpers import _case_config_summary

        queryset = DataFactoryQuerySelector.data_factory_case_config().select_related("template",
                                                                                      "template__entity").filter(
            source_type=int(source_type),
            source_id=int(source_id),
        )
        return {"items": [_case_config_summary(item) for item in queryset.order_by("sort", "id")]}

    @mcp.resource("mango://ui-page/{page_id}")
    @_logged_authenticated_resource
    def get_ui_page_resource(page_id: str) -> dict:
        """读取 UI 页面和元素资源。"""
        from django.forms import model_to_dict

        page = UiQuerySelector.page().get(id=int(page_id))
        elements = [
            model_to_dict(item)
            for item in UiQuerySelector.page_element().filter(page_id=page.id).order_by("id")
        ]
        return {"page": model_to_dict(page), "elements": elements}

    @mcp.resource("mango://ui-page-step/{page_step_id}")
    @_logged_authenticated_resource
    def get_ui_page_step_resource(page_step_id: str) -> dict:
        """读取 UI 页面步骤、流程图和步骤详情资源。"""
        from django.forms import model_to_dict

        page_step = UiQuerySelector.page_steps().get(id=int(page_step_id))
        details = [
            model_to_dict(item)
            for item in
            UiQuerySelector.page_steps_detailed().filter(page_step_id=page_step.id).order_by("step_sort", "id")
        ]
        return {"page_step": model_to_dict(page_step), "details": details}

    @mcp.resource("mango://ui-case/{case_id}")
    @_logged_authenticated_resource
    def get_ui_case_resource(case_id: str) -> dict:
        """读取完整 UI case 树资源。"""
        from src.interfaces.mcp.tools.ui.helpers import _case_tree

        return _case_tree(int(case_id), include_result_data=True)

    @mcp.resource("mango://functional-test/suite/{suite_id}")
    def get_functional_test_suite_resource(suite_id: str) -> dict:
        """读取功能测试需求资源。"""
        from src.common.utils.redaction import mask_sensitive

        suite = prepare_suite_queryset(FunctionalTestQuerySelector.manual_test_suite().all()).get(id=int(suite_id))
        cases = prepare_case_list_queryset(FunctionalTestQuerySelector.manual_test_case().filter(suite_id=suite.id))
        resources = prepare_context_resource_queryset(
            FunctionalTestQuerySelector.functional_test_context_resource().filter(suite_id=suite.id))
        data = format_suite(suite)
        data["cases"] = format_case_list(cases, many=True)
        data["context_resources"] = format_context_resource(resources, many=True)
        return mask_sensitive(data)

    @mcp.resource("mango://functional-test/case/{case_id}")
    def get_functional_test_case_resource(case_id: str) -> dict:
        """读取功能测试用例资源。"""
        from src.common.utils.redaction import mask_sensitive

        case = prepare_case_queryset(FunctionalTestQuerySelector.manual_test_case().all()).get(id=int(case_id))
        return mask_sensitive(format_case(case))

    @mcp.resource("mango://functional-test/context-resource/{resource_id}")
    def get_functional_test_context_resource(resource_id: str) -> dict:
        """读取功能测试上下文资料资源。"""
        from src.common.utils.redaction import mask_sensitive

        resource = prepare_context_resource_queryset(
            FunctionalTestQuerySelector.functional_test_context_resource().all()).get(id=int(resource_id))
        return mask_sensitive(format_context_resource(resource))



    @mcp.resource("mango://pytest-product/{product_id}")
    def get_pytest_product_resource(product_id: str) -> dict:
        """读取 Pytest 项目绑定资源。"""
        from src.interfaces.mcp.tools.pytest.helpers import _product_detail

        return _product_detail(int(product_id))

    @mcp.resource("mango://pytest-case/{case_id}")
    def get_pytest_case_resource(case_id: str) -> dict:
        """读取 Pytest case 元信息资源，不直接返回文件内容。"""
        from src.interfaces.mcp.tools.pytest.helpers import _case_detail

        return _case_detail(int(case_id))

    @mcp.prompt()
    def use_mcp_skill(task: str, skill_name: str = "") -> str:
        """生成先加载平台 Skill、再使用 MCP 工具完成任务的标准提示词。"""
        target = f"mango://skills/{skill_name}" if skill_name else "mango://skills/catalog"
        return (
            f"请先读取 {target}。"
            "如果尚未指定 Skill，请根据目录中的 title、category、description 选择最匹配项。"
            "完整阅读 SKILL.md，并按其中路由读取本任务需要的 references；"
            "然后严格遵循 Skill，使用当前 MCP 的工具完成任务。"
            f"\n用户任务：{task}"
        )

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
            "请通过 Mango 数据工厂 MCP 查询数据库、表结构、实体和字段规则，"
            "为指定业务状态创建或更新数据实体、字段规则和状态模板。"
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

    from src.interfaces.mcp.registry import domain_registrars

    for registrar_domain, registrar in domain_registrars(domain):
        mcp.tool = native_tool_method
        mcp.tool = _authenticated_tool_method(mcp, registrar_domain)
        registrar(mcp)
    app = mcp.http_app(
        path="/",
        transport="streamable-http",
        stateless_http=False,
        json_response=True,
        host_origin_protection=_env_bool("MANGO_MCP_ENABLE_DNS_REBINDING_PROTECTION", True),
        allowed_hosts=_mcp_allowed_hosts(),
        allowed_origins=_mcp_allowed_origins(),
    )
    app.fastmcp_server = mcp
    wrapped_app = McpAuthorizationContextApp(app)
    wrapped_app.fastmcp_server = mcp
    return wrapped_app


def mcp_router_asgi_app():
    """Expose one complete server and focused standard MCP domain servers."""
    try:
        from starlette.applications import Starlette
        from starlette.routing import Mount
    except ModuleNotFoundError:
        return _missing_dependency_app

    endpoint_apps = {None: mcp_asgi_app()}
    endpoint_apps.update({domain: mcp_asgi_app(domain) for domain in MCP_DOMAIN_PATHS})

    @asynccontextmanager
    async def lifespan(_app):
        async with AsyncExitStack() as stack:
            for endpoint_app in endpoint_apps.values():
                await stack.enter_async_context(endpoint_app.router.lifespan_context(endpoint_app))
            yield

    routes = [Mount(f"/{domain}", app=endpoint_apps[domain]) for domain in MCP_DOMAIN_PATHS]
    routes.append(Mount("/", app=endpoint_apps[None]))
    app = Starlette(routes=routes, lifespan=lifespan)
    wrapped_app = McpDomainPathApp(app)
    wrapped_app.fastmcp_server = endpoint_apps[None].fastmcp_server
    wrapped_app.domain_servers = {
        domain: endpoint_apps[domain].fastmcp_server
        for domain in MCP_DOMAIN_PATHS
    }
    return wrapped_app


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
