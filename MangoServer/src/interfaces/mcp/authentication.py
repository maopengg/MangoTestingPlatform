from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import jwt
import time
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import close_old_connections
from django.db.utils import Error as DjangoDbError
from django.db.utils import InterfaceError, OperationalError
from fastmcp.exceptions import AuthorizationError
from fastmcp.server.auth import AccessToken
from fastmcp.server.auth.auth import TokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext
from jwt import exceptions as jwt_exceptions

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_pytest.selectors.querysets import PytestQuerySelector
from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.user.models import User
from src.apps.user.selectors.authorization import AuthorizationScopeSelector
from src.apps.user.selectors.querysets import UserQuerySelector
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.logging import log
from src.interfaces.mcp.common import fail, get_auth_token

PUBLIC_COMPONENTS = {"get_mcp_server_info"}
AUTHENTICATED_COMPONENTS = {
    "list_mcp_skills",
    "get_mcp_skill",
    "get_mcp_skill_catalog_resource",
    "get_mcp_skill_resource",
    "use_mcp_skill",
}
VALID_PERMISSION_KEYS = frozenset(PermissionMenuService.all_permission_keys())
GLOBAL_SCHEMA_COMPONENTS = {
    "get_api_auth_config_schema",
    "get_ui_auth_config_schema",
    "get_api_assertion_methods",
    "get_api_assertion_schema",
    "get_api_case_schema",
    "get_ui_automation_schema",
    "get_ui_operation_methods",
    "get_ui_assertion_methods",
    "get_ui_public_assertion_methods",
    "get_pytest_automation_schema",
    "get_data_factory_schema",
    "get_test_report_schema",
}


@dataclass(frozen=True)
class McpComponentPolicy:
    permission_key: str | None
    project_scoped: bool = True
    public: bool = False


DOMAIN_PERMISSIONS = {
    "project": {"base": "config.product", "create": "config.product:create", "edit": "config.product:edit",
                "delete": "config.product:delete", "execute": "config.product:query"},
    "api_info": {"base": "api.info", "create": "api.info:create", "edit": "api.info:edit", "delete": "api.info:delete",
                 "execute": "api.info:execute"},
    "api_case": {"base": "api.case", "create": "api.case:create", "edit": "api.case:edit", "delete": "api.case:delete",
                 "execute": "api.case:execute"},
    "api_headers": {"base": "api.headers", "create": "api.headers:create", "edit": "api.headers:edit",
                    "delete": "api.headers:delete", "execute": "api.headers:edit"},
    "api_public": {"base": "api.public", "create": "api.public:create", "edit": "api.public:edit",
                   "delete": "api.public:delete", "execute": "api.public:edit"},
    "api_auth": {"base": "api.auth_config", "create": "api.auth_config:create", "edit": "api.auth_config:edit",
                 "delete": "api.auth_config:delete", "execute": "api.auth_config:debug"},
    "ui_page": {"base": "ui.page", "create": "ui.page:create", "edit": "ui.page:edit", "delete": "ui.page:delete",
                "execute": "ui.page:debug"},
    "ui_step": {"base": "ui.page_steps", "create": "ui.page_steps:create", "edit": "ui.page_steps:edit",
                "delete": "ui.page_steps:delete", "execute": "ui.page_steps:debug"},
    "ui_case": {"base": "ui.case", "create": "ui.case:create", "edit": "ui.case:edit", "delete": "ui.case:delete",
                "execute": "ui.case:execute"},
    "ui_public": {"base": "ui.public", "create": "ui.public:create", "edit": "ui.public:edit",
                  "delete": "ui.public:delete", "execute": "ui.public:edit"},
    "ui_auth": {"base": "ui.auth_config", "create": "ui.auth_config:create", "edit": "ui.auth_config:edit",
                "delete": "ui.auth_config:delete", "execute": "ui.auth_config:debug"},
    "data_entity": {"base": "data_factory.entity", "create": "data_factory.entity:create",
                    "edit": "data_factory.entity:edit", "delete": "data_factory.entity:delete",
                    "execute": "data_factory.entity:debug"},
    "data_template": {"base": "data_factory.template", "create": "data_factory.template:create",
                      "edit": "data_factory.template:edit", "delete": "data_factory.template:delete",
                      "execute": "data_factory.template:debug"},
    "data_execution": {"base": "data_factory.execution", "create": "data_factory.template:debug",
                       "edit": "data_factory.template:edit", "delete": "data_factory.execution:delete",
                       "execute": "data_factory.execution:detail"},
    "datasource": {"base": "config.product", "create": "config.product:create", "edit": "config.product:edit",
                   "delete": "config.product:delete", "execute": "config.product:query"},
    "pytest_repository": {"base": "pytest.repository", "create": "pytest.repository:create",
                          "edit": "pytest.repository:edit", "delete": "pytest.repository:delete",
                          "execute": "pytest.repository:execute"},
    "pytest_product": {"base": "pytest.product", "create": "pytest.product:create", "edit": "pytest.product:edit",
                       "delete": "pytest.product:delete", "execute": "pytest.product:edit"},
    "pytest_case": {"base": "pytest.case", "create": "pytest.case:edit", "edit": "pytest.case:edit",
                    "delete": "pytest.case:delete", "execute": "pytest.case:execute"},
    "functional_suite": {"base": "functional.suite", "create": "functional.suite:create",
                         "edit": "functional.suite:edit", "delete": "functional.suite:delete",
                         "execute": "functional.suite:edit"},
    "functional_case": {"base": "functional.case", "create": "functional.case:create", "edit": "functional.case:edit",
                        "delete": "functional.case:delete", "execute": "functional.case:edit"},
    "module_coverage": {"base": "api.module_coverage", "create": "api.module_coverage:create",
                        "edit": "api.module_coverage:edit", "delete": "api.module_coverage:delete",
                        "execute": "api.module_coverage:edit"},
    "functional_plan": {"base": "functional.plan", "create": "functional.plan:create", "edit": "functional.plan:edit",
                        "delete": "functional.plan:delete", "execute": "functional.plan:execute"},
    "ai_skill": {"base": "ai.skill", "create": "ai.skill:create", "edit": "ai.skill:edit", "delete": "ai.skill:delete",
                 "execute": "ai.skill:detail"},
    "ai_mcp": {"base": "ai.mcp", "create": "ai.mcp:create", "edit": "ai.mcp:edit", "delete": "ai.mcp:delete",
               "execute": "ai.mcp:debug"},
    "ai_task": {"base": "ai.task", "create": "ai.task:create", "edit": "ai.task:debug", "delete": "ai.task:delete",
                "execute": "ai.task:debug"},
    "report": {"base": "report", "create": "report:retry", "edit": "report:retry", "delete": "report:retry",
               "execute": "report:retry"},
    "scheduled": {"base": "timing.tasks", "create": "timing.tasks:edit", "edit": "timing.tasks:edit",
                  "delete": "timing.tasks:edit", "execute": "timing.tasks:execute"},
    "file": {"base": "config.test_files", "create": "config.test_files:create", "edit": "config.test_files:edit",
             "delete": "config.test_files:delete", "execute": "config.test_files:download"},
    "variable": {"base": "help.variable", "create": "help.variable:debug", "edit": "help.variable:debug",
                 "delete": "help.variable:debug", "execute": "help.variable:debug"},
    "workbench_todo": {"base": "index.home", "create": "index.home", "edit": "index.home", "delete": "index.home",
                       "execute": "index.home"},
}


def _operation(name: str) -> str:
    if name.startswith("agent_ui_"):
        return "base" if name == "agent_ui_get_case" else "execute"
    value = name
    if value.startswith("preview_"):
        value = value[len("preview_"):]
    if value.startswith(("delete_", "batch_delete_", "archive_", "batch_archive_", "cleanup_", "clear_", "unbind_")):
        return "delete"
    if value.startswith(("create_", "add_", "upload_", "import_", "batch_generate_", "batch_upload_", "batch_upsert_")):
        return "create"
    if value.startswith(
            ("update_", "set_", "sort_", "copy_", "sync_", "push_", "save_", "replace_", "bind_", "publish_",
             "unpublish_", "auto_generate_")):
        return "edit"
    if value.startswith(
            ("run_", "start_", "finish_", "execute_", "trigger_", "test_", "evaluate_", "refresh_", "retry_",
             "analyze_", "query_")):
        return "execute"
    return "base"


def _domain(name: str) -> tuple[str | None, bool]:
    if name.startswith("agent_ui_"):
        return "ui_case", True
    if name == "get_project_product_resource":
        return "project", True
    if name in {"api_case_from_curl", "api_failure_analysis"}:
        return "api_case", True
    if name in {"data_factory_template_from_table", "bind_data_factory_for_api_case"}:
        return "data_template", True
    if name in {"get_current_user_context", "switch_user_test_environment", "list_test_environments",
                "list_case_owners"}:
        return "project", False
    if name in {"ensure_user_test_environment", "list_project_test_objects", "list_project_products",
                "list_product_modules", "create_product_module", "update_product_module",
                "preview_delete_product_module_impact", "delete_product_module"}:
        return "project", True
    if "api_auth_config" in name or name == "list_api_auth_time_tasks":
        return "api_auth", True
    if "ui_auth_config" in name or name == "list_ui_auth_time_tasks" or name == "save_ui_manual_auth_cache":
        return "ui_auth", True
    if "api_header" in name:
        return "api_headers", True
    if "api_public_variable" in name:
        return "api_public", True
    if "grpc_service" in name or "grpc_method" in name:
        return "api_info", True
    if "api_info" in name and "case_step" not in name:
        return "api_info", True
    if "api_case" in name:
        return "api_case", True
    if name.startswith(("get_api_", "search_api_case", "create_api_case", "create_complete_api_case", "copy_api_case",
                        "update_api_case", "add_api_case", "list_api_case", "sort_api_case", "refresh_api_case",
                        "run_api_case", "analyze_api_case", "delete_api_case", "preview_delete_api_case",
                        "publish_api_case", "generate_api_case", "auto_generate_api_case")):
        return "api_case", True
    if "datasource" in name or "database_table" in name or "table_schema" in name:
        return "datasource", True
    if "data_factory_execution" in name or "cleanup_data_factory" in name:
        return "data_execution", True
    if "data_factory_template" in name or "data_factory_case_config" in name or "data_factory_to_case" in name:
        return "data_template", True
    if "data_factory" in name:
        return "data_entity", True
    if "pytest_repo" in name or name == "sync_pytest_products_from_repo":
        return "pytest_repository", True
    if "pytest_product" in name or "pytest_automation_schema" in name:
        return "pytest_product", True
    if "pytest_case" in name:
        return "pytest_case", True
    if "module_coverage" in name:
        return "module_coverage", True
    if "functional_test_plan" in name:
        return "functional_plan", True
    if "functional_test_suite" in name or "functional_test_context" in name or "functional_test_suite_stats" in name:
        return "functional_suite", True
    if "functional_test" in name:
        return "functional_case", True
    if "ai_skill" in name:
        return "ai_skill", False
    if "ai_mcp" in name:
        return "ai_mcp", False
    if "ai_agent" in name or "ai_task" in name or "ai_context" in name:
        return "ai_task", True
    if "test_report" in name or "execution_result" in name:
        return "report", True
    if "scheduled_task" in name:
        return "scheduled", True
    if "workbench_todo" in name:
        return "workbench_todo", False
    if "system_file" in name:
        return "file", False
    if "test_data" in name:
        return "variable", False
    if "ui_public" in name:
        return "ui_public", True
    if "ui_case" in name:
        return "ui_case", True
    if "ui_page_step" in name or "playwright" in name or "ui_operation" in name or "ui_assertion" in name or name == "get_ui_automation_schema":
        return "ui_step", True
    if "ui_page" in name or "ui_element" in name:
        return "ui_page", True
    return None, True


def component_policy(name: str) -> McpComponentPolicy | None:
    from src.apps.evaluation.constants import MCP_EVALUATION_PERMISSIONS
    if name in MCP_EVALUATION_PERMISSIONS:
        # Evaluation services/selectors validate every nested object's product scope.
        return McpComponentPolicy(MCP_EVALUATION_PERMISSIONS[name], project_scoped=False)
    if name in PUBLIC_COMPONENTS:
        return McpComponentPolicy(None, project_scoped=False, public=True)
    if name in AUTHENTICATED_COMPONENTS:
        return McpComponentPolicy(None, project_scoped=False)
    domain, scoped = _domain(name)
    if domain is None:
        return None
    if name in GLOBAL_SCHEMA_COMPONENTS or name in {"sync_pytest_products_from_repo", "preview_push_pytest_repo_impact",
                                                    "push_pytest_repo"}:
        scoped = False
    if domain == "ai_task":
        scoped = False
    permissions = DOMAIN_PERMISSIONS[domain]
    permission_key = permissions[_operation(name)]
    base_key = permissions["base"]
    valid_keys = VALID_PERMISSION_KEYS
    suffix = None
    if "status" in name:
        suffix = "status"
    elif name.startswith("copy_"):
        suffix = "copy"
    elif "download" in name:
        suffix = "download"
    elif _operation(name) == "base" and ("detail" in name or name == "get_api_auth_config_cache"):
        suffix = "detail"
    candidate = f"{base_key}:{suffix}" if suffix else None
    if candidate in valid_keys:
        permission_key = candidate
    if name in {"sync_pytest_products_from_repo", "sync_pytest_cases", "push_pytest_repo"}:
        execute_key = f"{base_key}:execute"
        if execute_key in valid_keys:
            permission_key = execute_key
    if name in {"get_api_auth_config_cache", "refresh_api_auth_config", "preview_clear_api_auth_config_cache_impact",
                "clear_api_auth_config_cache"}:
        permission_key = "api.auth_config:detail" if name == "get_api_auth_config_cache" else "api.auth_config:debug"
    if name in {"get_ui_auth_config_cache", "refresh_ui_auth_config", "preview_clear_ui_auth_config_cache_impact",
                "clear_ui_auth_config_cache", "save_ui_manual_auth_cache"}:
        permission_key = "ui.auth_config:detail" if name == "get_ui_auth_config_cache" else "ui.auth_config:debug"
    if name in {"update_api_case_publication_status", "unpublish_api_case_revision"}:
        permission_key = "api.case:publish"
    if name == 'update_pytest_case_publication_status':
        permission_key = 'pytest.case:publish'
    if name == "update_test_report_case_diagnosis":
        permission_key = "report:exclude"
    return McpComponentPolicy(permission_key, project_scoped=scoped)


class MangoTokenVerifier(TokenVerifier):
    DB_RETRY_DELAYS = (0.2, 0.5, 1.0)

    async def verify_token(self, token: str) -> AccessToken | None:
        return await sync_to_async(self._verify_token_sync, thread_sensitive=True)(token)

    @staticmethod
    def _verify_token_sync(token: str) -> AccessToken | None:
        last_db_error = None
        attempts = len(MangoTokenVerifier.DB_RETRY_DELAYS) + 1
        for attempt in range(1, attempts + 1):
            close_old_connections()
            try:
                if token.startswith("mango_"):
                    user = UserQuerySelector.user().select_related("role").get(api_key=token)
                    expires_at = None
                else:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                    user = UserQuerySelector.user().select_related("role").get(id=payload.get("id"))
                    expires_at = payload.get("exp")
                permissions = sorted(PermissionMenuService.permission_keys_for_user(user))
                return AccessToken(
                    token=token,
                    client_id=user.username,
                    subject=str(user.id),
                    scopes=permissions,
                    expires_at=expires_at,
                    claims={"user_id": user.id, "role_id": user.role_id, "is_super_admin": user.is_super_admin},
                )
            except (User.DoesNotExist, jwt_exceptions.PyJWTError, TypeError, ValueError):
                return None
            except (OperationalError, InterfaceError, DjangoDbError) as error:
                last_db_error = error
                close_old_connections()
                if attempt >= attempts:
                    log.system.error(
                        f'MCP认证查询用户失败，数据库连接重试耗尽，异常类型：{type(error).__name__}，错误：{error}'
                    )
                    raise
                delay = MangoTokenVerifier.DB_RETRY_DELAYS[attempt - 1]
                log.system.warning(
                    f'MCP认证查询用户遇到数据库连接异常，{delay}秒后重试：'
                    f'第{attempt}/{attempts}次，异常类型：{type(error).__name__}，错误：{error}'
                )
                time.sleep(delay)
            except Exception as error:
                log.system.error(
                    f'MCP认证查询用户失败，异常类型：{type(error).__name__}，错误：{error}'
                )
                raise
            finally:
                close_old_connections()
        if last_db_error:
            raise last_db_error
        return None


TOKEN_VERIFIER = MangoTokenVerifier()


def bearer_token() -> str | None:
    return get_auth_token() or os.getenv("MANGO_MCP_TOKEN")


def permission_error(user: User, component_name: str, arguments: dict[str, Any]) -> dict | None:
    policy = component_policy(component_name)
    if policy is None:
        return fail("该 MCP 组件未配置权限策略", "MCP_POLICY_MISSING", {"component": component_name})
    if policy.public or policy.permission_key is None or PermissionMenuService.is_effective_super_admin(user):
        return None
    permissions = PermissionMenuService.permission_keys_for_user(user)
    required_key = policy.permission_key
    if component_name == 'update_ui_case' and 'publication_status' in (arguments.get('fields') or {}):
        required_key = 'ui.case:publish'
    if required_key not in permissions:
        return fail("没有调用该 MCP 功能的角色权限", "MCP_PERMISSION_DENIED",
                    {"component": component_name, "permission": required_key})
    domain, _ = _domain(component_name)
    if domain and _operation(component_name) == 'edit':
        page_key = DOMAIN_PERMISSIONS[domain]['base']
        if PermissionMenuService.payload_changes_status(page_key, arguments):
            status_key = f'{page_key}:status'
            if status_key not in permissions:
                return fail("没有调用该 MCP 功能的角色权限", "MCP_PERMISSION_DENIED",
                            {"component": component_name, "permission": status_key})
    if not policy.project_scoped:
        return None
    project_ids = resolve_project_product_ids(component_name, arguments)
    if _operation(component_name) != "base" and _has_scope_identifier(arguments) and not project_ids:
        return fail("无法确认目标数据所属的项目产品", "MCP_PROJECT_SCOPE_UNRESOLVED", {"component": component_name})
    if len(project_ids) > 1:
        return fail(
            "关联对象不属于同一个项目产品",
            "MCP_PROJECT_SCOPE_MISMATCH",
            {"component": component_name, "project_product_ids": sorted(project_ids)},
        )
    for project_id in project_ids:
        if not ProjectProductScopeService.has_project_product(user, project_id):
            return fail("没有目标项目产品的数据权限", "MCP_PROJECT_SCOPE_DENIED",
                        {"component": component_name, "project_product_id": project_id})
    return None


def resolve_project_product_ids(component_name: str, arguments: dict[str, Any]) -> set[int]:
    result = _resolve_nested_scope_ids(arguments)
    direct = arguments.get("project_product_id")
    if direct not in (None, ""):
        if "pytest_case" in component_name:
            from src.apps.auto_pytest.models import PytestProduct
            value = PytestQuerySelector.pytest_product().filter(id=int(direct)).values_list("project_product_id",
                                                                                            flat=True).first()
            if value is not None:
                result.add(value)
        else:
            result.add(int(direct))
    if component_name == "get_data_factory_case_config_resource" and arguments.get("source_id"):
        from src.apps.auto_api.models import ApiCase, ApiCaseDetailedParameter
        from src.apps.auto_ui.models import UiCase

        source_type = int(arguments.get("source_type") or 0)
        source_id = int(arguments["source_id"])
        if source_type == 1:
            value = ApiQuerySelector.api_case().filter(id=source_id).values_list("project_product_id",
                                                                                 flat=True).first()
        elif source_type == 2:
            value = UiQuerySelector.ui_case().filter(id=source_id).values_list("project_product_id", flat=True).first()
        elif source_type == 3:
            value = ApiQuerySelector.api_case_detailed_parameter().filter(id=source_id).values_list(
                "case_detailed__case__project_product_id", flat=True).first()
        else:
            value = None
        if value is not None:
            result.add(value)
    if "data_factory_case_config" in component_name or component_name == "bind_data_factory_to_case_source":
        source_project_id = _case_source_project_id(arguments.get("source_type"), arguments.get("source_id"))
        if source_project_id is not None:
            result.add(source_project_id)
    fields = arguments.get("fields")
    if isinstance(fields, dict):
        nested_project_id = fields.get("project_product_id") or fields.get("project_product")
        if nested_project_id:
            result.add(int(nested_project_id))
        for key, aliases in {
            "suite_id": ("suite_id", "suite"),
            "case_id": ("case_id", "case"),
            "page_id": ("page_id", "page"),
            "element_id": ("element_id", "element"),
            "entity_id": ("entity_id", "entity"),
            "template_id": ("template_id", "template"),
        }.items():
            value = next((fields.get(alias) for alias in aliases if fields.get(alias)), None)
            if value:
                arguments = {**arguments, key: value}
    for payload_name in ("items", "scope"):
        payload = arguments.get(payload_name)
        payload_items = payload if isinstance(payload, list) else [payload]
        for item in payload_items:
            if not isinstance(item, dict):
                continue
            nested_arguments = {
                key: value
                for key, value in item.items()
                if key in {
                    "project_product_id", "api_case", "api_case_id", "ui_case", "ui_case_id",
                    "api_case_detailed", "api_case_detailed_id", "api_case_detailed_parameter",
                    "api_case_detailed_parameter_id", "config_id", "id",
                }
            }
            if "config_id" not in nested_arguments and item.get("id") and "data_factory_case_config" in component_name:
                nested_arguments["config_id"] = item["id"]
            result.update(_resolve_nested_scope_ids(nested_arguments))
    for payload_name in ("snapshot_data", "heal_data", "element_payload"):
        payload = arguments.get(payload_name)
        if isinstance(payload, dict):
            element_id = payload.get("element_id") or payload.get("element") or payload.get("id")
            page_id = payload.get("page_id") or payload.get("page")
            if element_id:
                arguments = {**arguments, "element_id": element_id}
            if page_id:
                arguments = {**arguments, "page_id": page_id}
    for list_name in ("case_ids", "api_case_ids", "ui_case_ids", "element_ids", "coverage_case_ids"):
        values = arguments.get(list_name)
        if values:
            if list_name == "element_ids":
                singular_name = "element_id"
            elif list_name == "coverage_case_ids":
                singular_name = "coverage_case_id"
            else:
                singular_name = "case_id"
            for value in values:
                resolver_component = component_name
                if list_name == "api_case_ids":
                    resolver_component = "api_case"
                elif list_name == "ui_case_ids":
                    resolver_component = "ui_case"
                nested_arguments = {singular_name: value}
                result.update(resolve_project_product_ids(resolver_component, nested_arguments))
    if component_name == "sync_pytest_cases" and arguments.get("project_id"):
        from src.apps.auto_pytest.models import PytestProduct
        value = PytestQuerySelector.pytest_product().filter(id=int(arguments["project_id"])).values_list(
            "project_product_id", flat=True).first()
        if value is not None:
            result.add(value)
    resolvers = _object_resolvers(component_name)
    for argument_name, resolver in resolvers:
        value = arguments.get(argument_name)
        if value not in (None, ""):
            project_id = resolver(int(value))
            if project_id is not None:
                result.add(project_id)
    if component_name == "bind_functional_test_automation_case" and arguments.get("automation_case_id") is not None:
        automation_component = "api_case" if int(arguments.get("automation_type") or 0) == 0 else "ui_case"
        result.update(resolve_project_product_ids(automation_component, {"case_id": arguments["automation_case_id"]}))
    return result


def _resolve_nested_scope_ids(arguments: dict[str, Any]) -> set[int]:
    from src.apps.auto_api.models import ApiCase, ApiCaseDetailed, ApiCaseDetailedParameter
    from src.apps.auto_ui.models import UiCase
    from src.apps.data_factory.models import DataFactoryCaseConfig

    mappings = {
        "api_case_id": (ApiCase, "project_product_id"),
        "api_case": (ApiCase, "project_product_id"),
        "ui_case_id": (UiCase, "project_product_id"),
        "ui_case": (UiCase, "project_product_id"),
        "api_case_detailed_id": (ApiCaseDetailed, "case__project_product_id"),
        "api_case_detailed": (ApiCaseDetailed, "case__project_product_id"),
        "api_case_detailed_parameter_id": (ApiCaseDetailedParameter, "case_detailed__case__project_product_id"),
        "api_case_detailed_parameter": (ApiCaseDetailedParameter, "case_detailed__case__project_product_id"),
        "config_id": (DataFactoryCaseConfig, "template__project_product_id"),
    }
    result = set()
    direct = arguments.get("project_product_id")
    if direct:
        result.add(int(direct))
    for key, (model, lookup) in mappings.items():
        value = arguments.get(key)
        if value:
            project_id = AuthorizationScopeSelector.queryset(model).filter(id=int(value)).values_list(lookup,
                                                                                                      flat=True).first()
            if project_id is not None:
                result.add(project_id)
    return result


def _case_source_project_id(source_type, source_id) -> int | None:
    if source_type in (None, "") or source_id in (None, ""):
        return None

    source_type = int(source_type)
    source_id = int(source_id)
    if source_type == 1:
        return ApiQuerySelector.api_case().filter(id=source_id).values_list("project_product_id", flat=True).first()
    if source_type == 2:
        return UiQuerySelector.ui_case().filter(id=source_id).values_list("project_product_id", flat=True).first()
    if source_type == 3:
        return ApiQuerySelector.api_case_detailed_parameter().filter(id=source_id).values_list(
            "case_detailed__case__project_product_id", flat=True).first()
    return None


def _object_resolvers(component_name: str):
    from src.apps.auto_api.models import (
        ApiAuthConfig, ApiCase, ApiCaseDetailed, ApiCaseDetailedParameter,
        ApiHeaders, ApiInfo, ApiPublic, ModuleCoverageCase,
        ModuleCoverageInterfaceSnapshot, ModuleCoverageScan,
    )
    from src.apps.auto_pytest.models import PytestCase, PytestProduct
    from src.apps.auto_ui.models import Page, PageElement, PageSteps, PageStepsDetailed, UiAuthConfig, UiCase, \
        UiCaseStepsDetailed, UiElementHealRecord
    from src.apps.auto_ui.models import UiPublic
    from src.apps.data_factory.models import DataFactoryCaseConfig, DataFactoryDatasourceAlias, DataFactoryEntity, \
        DataFactoryExecution, DataFactoryTemplate
    from src.apps.functional_test.models import (
        FunctionalTestContextResource,
        FunctionalTestPlan,
        FunctionalTestPlanCase,
        ManualTestCase,
        ManualTestSuite,
    )
    from src.apps.task_center.models import Tasks
    from src.apps.test_center.models import ProductModule, TestObject, TestSuite, TestSuiteDetails

    def field(model, lookup="project_product_id"):
        return lambda value: AuthorizationScopeSelector.queryset(model).filter(id=value).values_list(lookup,
                                                                                                     flat=True).first()

    common = [
        ("api_info_id", field(ApiInfo)), ("header_id", field(ApiHeaders)),
        ("public_id", field(ApiPublic)), ("module_id", field(ProductModule)),
        ("test_object_id", field(TestObject)),
        ("datasource_alias_id", field(DataFactoryDatasourceAlias)), ("entity_id", field(DataFactoryEntity)),
        ("template_id", field(DataFactoryTemplate)), ("execution_id", field(DataFactoryExecution)),
        ("config_id", field(DataFactoryCaseConfig, "template__project_product_id")),
        ("page_id", field(Page)), ("element_id", field(PageElement, "page__project_product_id")),
        ("page_step_id", field(PageSteps)), ("suite_id", field(ManualTestSuite)),
        ("resource_id", field(FunctionalTestContextResource, "suite__project_product_id")),
        ("plan_id", field(FunctionalTestPlan)),
        ("plan_case_id", field(FunctionalTestPlanCase, "plan__project_product_id")),
        ("product_id", field(PytestProduct)),
        ("scheduled_task_id", field(Tasks)), ("test_suite_id", field(TestSuite)),
        ("test_suite_detail_id", field(TestSuiteDetails)),
        ("detail_id", field(PageStepsDetailed, "page_step__project_product_id")),
        ("record_id", field(UiElementHealRecord, "page__project_product_id")),
        ("source_page_id", field(Page)), ("target_page_id", field(Page)),
        ("scan_id", field(ModuleCoverageScan)),
        ("coverage_case_id", field(ModuleCoverageCase)),
        ("coverage_interface_id", field(ModuleCoverageInterfaceSnapshot)),
        ("target_interface_id", field(ModuleCoverageInterfaceSnapshot)),
        ("current_snapshot_id", field(ModuleCoverageInterfaceSnapshot)),
        ("previous_snapshot_id", field(ModuleCoverageInterfaceSnapshot)),
    ]
    if "ui_public" in component_name:
        common.insert(0, ("public_variable_id", field(UiPublic)))
    else:
        common.insert(0, ("public_variable_id", field(ApiPublic)))
    if "ui_auth_config" in component_name or component_name == "save_ui_manual_auth_cache":
        common.insert(0, ("auth_config_id", field(UiAuthConfig)))
    else:
        common.insert(0, ("auth_config_id", field(ApiAuthConfig)))
    if "api" in component_name:
        common.extend([
            ("case_id", field(ApiCase)), ("step_id", field(ApiCaseDetailed, "case__project_product_id")),
            ("scenario_id", field(ApiCaseDetailedParameter, "case_detailed__case__project_product_id")),
        ])
    elif "ui" in component_name:
        common.extend(
            [("case_id", field(UiCase)), ("case_step_id", field(UiCaseStepsDetailed, "case__project_product_id"))])
    elif "functional" in component_name:
        common.append(("case_id", field(ManualTestCase)))
    elif "pytest" in component_name:
        common.append(("case_id", field(PytestCase, "project_product__project_product_id")))
    return common


def _has_scope_identifier(arguments: dict[str, Any]) -> bool:
    ignored = {"user_id", "test_env_id", "case_people_id", "owner_id", "time_task_id", "notice_group_id"}
    for key, value in arguments.items():
        if value in (None, "", [], {}):
            continue
        if key in ignored:
            continue
        if key.endswith(("_id", "_ids")) or key in {"fields", "items", "scope", "snapshot_data", "heal_data",
                                                    "element_payload"}:
            return True
    return False


def filter_scoped_result(user: User, value: Any) -> Any:
    if PermissionMenuService.is_effective_super_admin(user) or ProjectProductScopeService.can_view_all_project_data(
            user):
        return value
    allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
    return _filter_value(value, allowed_ids)


def scope_queryset_for_user(user: User, queryset, lookup: str = "project_product_id"):
    if PermissionMenuService.is_effective_super_admin(user) or ProjectProductScopeService.can_view_all_project_data(
            user):
        return queryset
    allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
    return queryset.filter(**{f"{lookup}__in": allowed_ids}) if allowed_ids else queryset.none()


def _filter_value(value: Any, allowed_ids: set[int]) -> Any:
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                project_id = _project_id_from_result_item(item)
                if project_id is not None and project_id not in allowed_ids:
                    continue
            result.append(_filter_value(item, allowed_ids))
        return result
    if isinstance(value, dict):
        return {key: _filter_value(item, allowed_ids) for key, item in value.items()}
    return value


def _project_id_from_result_item(item: dict) -> int | None:
    value = item.get("project_product_id")
    if value not in (None, ""):
        return int(value)
    project_product = item.get("project_product")
    if isinstance(project_product, int):
        return project_product
    if isinstance(project_product, dict) and project_product.get("id") is not None:
        return int(project_product["id"])
    datasource_alias_id = item.get("datasource_alias_id")
    if datasource_alias_id:
        from src.apps.data_factory.models import DataFactoryDatasourceAlias
        return DataFactoryQuerySelector.data_factory_datasource_alias().filter(id=datasource_alias_id).values_list(
            "project_product_id", flat=True).first()
    return None


RESOURCE_URI_POLICIES = {
    "mango://skills/catalog": "get_mcp_skill_catalog_resource",
    "mango://skills/": "get_mcp_skill_resource",
    "mango://project-product/": "get_project_product_resource",
    "mango://api-info/": "get_api_info_resource",
    "mango://api-case/": "get_api_case_resource",
    "mango://data-factory/entity/": "get_data_factory_entity_resource",
    "mango://data-factory/template/": "get_data_factory_template_resource",
    "mango://data-factory/execution/": "get_data_factory_execution_resource",
    "mango://data-factory/case-config/": "get_data_factory_case_config_resource",
    "mango://ui-page/": "get_ui_page_resource",
    "mango://ui-page-step/": "get_ui_page_step_resource",
    "mango://ui-case/": "get_ui_case_resource",
    "mango://functional-test/suite/": "get_functional_test_suite_resource",
    "mango://functional-test/case/": "get_functional_test_case_resource",
    "mango://functional-test/context-resource/": "get_functional_test_context_resource",
    "mango://ai/task/": "get_ai_task_resource",
    "mango://ai/context/": "get_ai_context_resource",
    "mango://pytest-product/": "get_pytest_product_resource",
    "mango://pytest-case/": "get_pytest_case_resource",
}


class MangoAuthorizationMiddleware(Middleware):
    async def _access(self):
        access = get_access_token()
        if access is not None:
            return access

        # Keep non-HTTP and legacy in-memory MCP clients compatible.
        token = bearer_token()
        return await TOKEN_VERIFIER.verify_token(token) if token else None

    @staticmethod
    def _visible(access, component_name: str) -> bool:
        policy = component_policy(component_name)
        if policy is None:
            return False
        if policy.public:
            return True
        if access is None:
            return False
        if access.claims.get("is_super_admin"):
            return True
        return policy.permission_key is None or policy.permission_key in set(access.scopes)

    async def _authorize(self, component_name: str, arguments: dict[str, Any] | None = None, access=None):
        policy = component_policy(component_name)
        if policy and policy.public:
            return
        access = access or await self._access()
        if access is None:
            from src.interfaces.mcp.exceptions import (
                MCP_API_KEY_INVALID,
                MCP_AUTHORIZATION_REQUIRED,
                MCP_JWT_INVALID,
            )

            token = bearer_token()
            if not token:
                message = MCP_AUTHORIZATION_REQUIRED.message
            elif token.startswith("mango_"):
                message = MCP_API_KEY_INVALID.message
            else:
                message = MCP_JWT_INVALID.message
            raise AuthorizationError(message)
        user = await sync_to_async(UserQuerySelector.user().select_related("role").get, thread_sensitive=True)(
            id=int(access.subject))
        error = await sync_to_async(permission_error, thread_sensitive=True)(user, component_name, arguments or {})
        if error:
            from src.interfaces.mcp.common import log_mcp_tool_call_async

            log_mcp_tool_call_async(component_name, arguments or {}, error, status_code=403, user=user)
            raise AuthorizationError(error["message"])

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools = await call_next(context)
        access = await self._access()
        return [tool for tool in tools if self._visible(access, tool.name)]

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        access = await self._access()
        await self._authorize(context.message.name, context.message.arguments or {}, access=access)
        return await call_next(context)

    async def on_list_prompts(self, context: MiddlewareContext, call_next):
        prompts = await call_next(context)
        access = await self._access()
        return [prompt for prompt in prompts if self._visible(access, prompt.name)]

    async def on_get_prompt(self, context: MiddlewareContext, call_next):
        await self._authorize(context.message.name, context.message.arguments or {})
        return await call_next(context)

    async def on_list_resource_templates(self, context: MiddlewareContext, call_next):
        templates = await call_next(context)
        access = await self._access()
        return [template for template in templates if self._visible(access, getattr(template, "name", ""))]

    async def on_read_resource(self, context: MiddlewareContext, call_next):
        uri = str(context.message.uri)
        component_name = next((name for prefix, name in RESOURCE_URI_POLICIES.items() if uri.startswith(prefix)), "")
        arguments = _resource_arguments(component_name, uri)
        await self._authorize(component_name, arguments)
        return await call_next(context)


def _resource_arguments(component_name: str, uri: str) -> dict[str, Any]:
    if component_name == "get_data_factory_case_config_resource":
        parts = uri.rstrip("/").split("/")
        source_type, source_id = int(parts[-2]), parts[-1]
        return {"source_type": source_type, "source_id": source_id}
    tail = uri.rstrip("/").split("/")[-1]
    argument_names = {
        "get_project_product_resource": "project_product_id",
        "get_api_info_resource": "api_info_id",
        "get_api_case_resource": "case_id",
        "get_data_factory_entity_resource": "entity_id",
        "get_data_factory_template_resource": "template_id",
        "get_data_factory_execution_resource": "execution_id",
        "get_ui_page_resource": "page_id",
        "get_ui_page_step_resource": "page_step_id",
        "get_ui_case_resource": "case_id",
        "get_functional_test_suite_resource": "suite_id",
        "get_functional_test_case_resource": "case_id",
        "get_functional_test_context_resource": "resource_id",
        "get_pytest_product_resource": "product_id",
        "get_pytest_case_resource": "case_id",
        "get_mcp_skill_resource": "skill_name",
    }
    argument_name = argument_names.get(component_name)
    return {argument_name: tail} if argument_name else {}
