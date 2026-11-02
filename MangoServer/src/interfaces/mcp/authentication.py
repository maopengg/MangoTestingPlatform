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
from src.apps.user.services.mcp_permission_registry import MCP_PERMISSION_RULES
from src.apps.user.selectors.authorization import AuthorizationScopeSelector
from src.apps.user.selectors.querysets import UserQuerySelector
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.logging import log
from src.interfaces.mcp.common import fail, get_auth_token


@dataclass(frozen=True)
class McpComponentPolicy:
    permission_key: str | None
    project_scoped: bool = True
    public: bool = False
    additional_permission_keys: tuple[str, ...] = ()
    requires_resolved_scope: bool = False


def component_policy(name: str) -> McpComponentPolicy | None:
    rule = MCP_PERMISSION_RULES.get(name)
    return McpComponentPolicy(**rule) if rule is not None else None


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
        required_key = 'ui.case:change'
    if required_key not in permissions:
        return fail("没有调用该 MCP 功能的角色权限", "MCP_PERMISSION_DENIED",
                    {"component": component_name, "permission": required_key})
    if not set(policy.additional_permission_keys) <= permissions:
        return fail('没有关联资源的查看权限', 'MCP_PERMISSION_DENIED', {'component': component_name})
    if not policy.project_scoped:
        return None
    project_ids = resolve_project_product_ids(component_name, arguments)
    if not project_ids and (policy.requires_resolved_scope or (
            policy.permission_key and not policy.permission_key.endswith(":read") and _has_scope_identifier(arguments)
    )):
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
        granted = set(access.scopes)
        return (policy.permission_key is None or policy.permission_key in granted) and set(
            policy.additional_permission_keys,
        ) <= granted

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
