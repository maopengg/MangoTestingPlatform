from __future__ import annotations

import hashlib
from copy import deepcopy

from django.core.cache import cache
from pydantic import ValidationError

from src.apps.auto_ui.enums import ElementOperationEnum, UiPublicTypeEnum
from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_AGENT_CASE_CHANGED,
    UI_AGENT_REPORT_INVALID,
    UI_AGENT_RUNTIME_OPERATION_INVALID,
)
from src.apps.auto_ui.models import PageSteps, UiCaseStepsDetailed
from src.apps.auto_ui.schemas.agent_execution import AgentUiRuntimeOperationRequest
from src.apps.auto_ui.services.execution.agent.agent_execution import AgentUiExecutionService
from src.apps.auto_ui.services.cases.case_global_variable import UiCaseGlobalVariableService
from src.apps.auto_ui.services.execution.cases.test_case import TestCase
from src.apps.data_factory.services.datasource.data_source_execution_request import DataSourceExecutionRequestService
from src.common.testing import ObtainTestData


class AgentUiRuntimeOperationService:
    """统一处理代理 UI Case 中必须由服务端执行的运行时操作。"""

    IDEMPOTENCY_PREFIX = "agent-ui-runtime-result:v1"
    CACHE_TTL_SECONDS = AgentUiExecutionService.TOKEN_MAX_AGE_SECONDS

    @classmethod
    def execute(
            cls,
            *,
            execution_token: str,
            project_product_id: int,
            user_id: int,
            username: str,
            request: dict,
    ) -> dict:
        token_data, case = AgentUiExecutionService._execution_context(
            execution_token, user_id, project_product_id,
        )
        try:
            operation = AgentUiRuntimeOperationRequest.model_validate(request)
        except ValidationError as error:
            raise AutoUiError(
                UI_AGENT_REPORT_INVALID,
                value=(AgentUiExecutionService._validation_message(error),),
            ) from error

        cache_key = cls._idempotency_key(token_data["execution_id"], operation.idempotency_key)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return {**deepcopy(cached_result), "duplicate": True}

        test_data = cls._test_data(operation.runtime_variables)
        if operation.operation == "prepare_case":
            result = cls._prepare_case(case, token_data, test_data)
        elif operation.operation == "cleanup_case":
            result = cls._cleanup_case(case, token_data, test_data)
        else:
            result = cls._execute_node(
                case,
                token_data,
                test_data,
                operation,
                user_id=user_id,
                username=username,
            )
        cache.set(cache_key, result, cls.CACHE_TTL_SECONDS)
        return result

    @classmethod
    def _prepare_case(cls, case, token_data: dict, test_data: ObtainTestData) -> dict:
        executed = []
        before = test_data.get_all()
        for item in case.front_sql or []:
            if not cls._matches_environment(item, token_data["test_env"]):
                continue
            cls._execute_data_source(
                item=item,
                test_data=test_data,
                token_data=token_data,
                source_stage="case_front",
                require_cache_result=bool(item.get("key_list")),
            )
            executed.append("case_front_data_source")

        unsupported_public = []
        for item in UiCaseGlobalVariableService.list_public(
                case.project_product_id, token_data["test_env"], case.front_public,
        ):
            if item.type == UiPublicTypeEnum.SQL.value:
                cls._execute_data_source(
                    item={
                        "datasource_alias": item.datasource_alias_id,
                        "key": item.key,
                        "value": item.value,
                    },
                    test_data=test_data,
                    token_data=token_data,
                    source_stage="global_variable",
                    require_cache_result=True,
                    confirm_write=False,
                )
                executed.append("global_data_source")
            elif item.type == UiPublicTypeEnum.CODE.value:
                unsupported_public.append({"id": item.id, "key": item.key, "type": item.type})

        if unsupported_public:
            return cls._result(
                "blocked",
                "unsupported",
                "case_setup",
                "Case 包含代码型全局变量；服务端安全运行器尚不允许执行任意代码",
                unsupported_items=unsupported_public,
            )
        return cls._result(
            "completed",
            "server",
            "case_setup",
            "Case 前置和全局数据源操作已执行",
            executed_operations=executed,
            runtime_bindings=cls._changed_bindings(before, test_data.get_all()),
        )

    @classmethod
    def _cleanup_case(cls, case, token_data: dict, test_data: ObtainTestData) -> dict:
        executed = []
        before = test_data.get_all()
        for item in case.posterior_sql or []:
            if not cls._matches_environment(item, token_data["test_env"]):
                continue
            cls._execute_data_source(
                item=item,
                test_data=test_data,
                token_data=token_data,
                source_stage="case_posterior",
            )
            executed.append("case_posterior_data_source")
        return cls._result(
            "completed",
            "server",
            "case_cleanup",
            "Case 后置数据源操作已执行",
            executed_operations=executed,
            runtime_bindings=cls._changed_bindings(before, test_data.get_all()),
        )

    @classmethod
    def _execute_node(
            cls,
            case,
            token_data: dict,
            test_data: ObtainTestData,
            operation: AgentUiRuntimeOperationRequest,
            *,
            user_id: int,
            username: str,
    ) -> dict:
        if operation.step_index is None or operation.node_id is None:
            raise AutoUiError(
                UI_AGENT_RUNTIME_OPERATION_INVALID,
                value=("execute_node 必须提供 step_index 和 node_id",),
            )
        steps = token_data["steps"]
        if operation.step_index >= len(steps):
            raise AutoUiError(UI_AGENT_RUNTIME_OPERATION_INVALID, value=("step_index 超出范围",))
        snapshot_step = steps[operation.step_index]
        AgentUiExecutionService._validate_step_version(snapshot_step)
        node, children = cls._runtime_node(
            case,
            snapshot_step,
            operation.node_id,
            test_env=token_data["test_env"],
            user_id=user_id,
            username=username,
        )
        node_type = int(node["type"])

        if node_type == ElementOperationEnum.CUSTOM.value:
            return cls._result(
                "client_required",
                "agent_context",
                "custom_variable",
                "自定义变量应由 Skill 直接写入本次 Case 上下文，无需调用运行接口",
                node_id=operation.node_id,
                resolved_custom=test_data.replace(node.get("custom") or []),
                next_node_ids=children,
            )

        if node_type == ElementOperationEnum.SQL.value:
            before = test_data.get_all()
            for item in node.get("sql_execute") or []:
                cls._execute_data_source(
                    item=item,
                    test_data=test_data,
                    token_data=token_data,
                    source_stage="page_step_sql",
                    require_cache_result=True,
                    node_id=operation.node_id,
                    page_step_id=snapshot_step["page_step_id"],
                )
            return cls._result(
                "completed",
                "server",
                "data_source",
                "节点数据源操作已执行",
                node_id=operation.node_id,
                next_node_ids=children,
                runtime_bindings=cls._changed_bindings(before, test_data.get_all()),
            )

        if node_type == ElementOperationEnum.CONDITION.value:
            selected_node_id = operation.client_result.get("next_node_id")
            if selected_node_id is not None:
                try:
                    selected_node_id = int(selected_node_id)
                except (TypeError, ValueError) as error:
                    raise AutoUiError(
                        UI_AGENT_RUNTIME_OPERATION_INVALID, value=("条件分支节点 ID 无效",),
                    ) from error
                if selected_node_id not in children:
                    raise AutoUiError(
                        UI_AGENT_RUNTIME_OPERATION_INVALID, value=("条件分支不属于当前节点",),
                    )
                return cls._result(
                    "completed",
                    "server",
                    "condition",
                    "条件分支已确认",
                    node_id=operation.node_id,
                    next_node_id=selected_node_id,
                )
            return cls._result(
                "client_required",
                "browser",
                "condition",
                "需要读取页面状态后确认匹配分支",
                node_id=operation.node_id,
                resolved_node=cls._resolved_node(node, test_data),
                branch_candidates=children,
            )

        if node_type == ElementOperationEnum.FORCE_WAIT.value:
            resolved_node = cls._resolved_node(node, test_data)
            values = {item.get("f"): item.get("v") for item in resolved_node.get("ope_value") or []}
            return cls._result(
                "client_required",
                "client",
                "wait",
                "请在客户端执行等待",
                node_id=operation.node_id,
                wait_seconds=float(values.get("seconds", 1)),
                next_node_ids=children,
            )

        if node_type == ElementOperationEnum.PYTHON_CODE.value:
            return cls._result(
                "blocked",
                "unsupported",
                "python_code",
                "Python 节点依赖执行器运行对象，禁止在 MCP/Django 进程中直接执行",
                node_id=operation.node_id,
            )

        return cls._result(
            "client_required",
            "browser",
            "assertion" if node_type == ElementOperationEnum.ASS.value else "element_action",
            "节点参数已由服务端解析，请使用浏览器工具执行",
            node_id=operation.node_id,
            resolved_node=cls._resolved_node(node, test_data),
            next_node_ids=children,
        )

    @classmethod
    def _runtime_node(
            cls, case, snapshot_step: dict, node_id: int, *, test_env: int, user_id: int, username: str,
    ) -> tuple[dict, list[int]]:
        if snapshot_step["is_auth_step"]:
            page_step = PageSteps.objects.filter(id=snapshot_step["page_step_id"]).first()
            case_step = None
        else:
            case_step = UiCaseStepsDetailed.objects.filter(
                id=snapshot_step["case_step_id"], case_id=case.id,
            ).select_related("page_step").first()
            page_step = case_step.page_step if case_step else None
        if page_step is None:
            raise AutoUiError(UI_AGENT_CASE_CHANGED)
        runtime = TestCase(user_id, username, test_env, is_send=False).case_steps_model(
            page_step.id,
            case_steps_detailed=case_step,
            switch_step_open_url=bool(case_step.switch_step_open_url) if case_step else True,
            is_auth_step=snapshot_step["is_auth_step"],
            front_public_ids=case.front_public,
        )
        element = next((item for item in runtime.element_list if item.id == node_id), None)
        if element is None:
            raise AutoUiError(UI_AGENT_RUNTIME_OPERATION_INVALID, value=("节点不属于当前页面步骤",))
        node = element.model_dump(mode="json")
        if case_step:
            override = next(
                (
                    item
                    for item in case_step.case_data or []
                    if str(item.get("page_step_details_id")) == str(node_id)
                ),
                None,
            )
            if override:
                cls._apply_case_override(node, override)
        flow_node = cls._find_flow_node(runtime.flow_data, node_id)
        children = [int(item.id) for item in (flow_node.children if flow_node else [])]
        return node, children

    @staticmethod
    def _apply_case_override(node: dict, override: dict) -> None:
        node_type = int(node["type"])
        detail_data = deepcopy(override.get("page_step_details_data"))
        if node_type in {
            ElementOperationEnum.OPE.value,
            ElementOperationEnum.ASS.value,
            ElementOperationEnum.CONDITION.value,
            ElementOperationEnum.FORCE_WAIT.value,
        }:
            node["ope_value"] = detail_data or []
        elif node_type == ElementOperationEnum.SQL.value:
            node["sql_execute"] = detail_data or []
        elif node_type == ElementOperationEnum.CUSTOM.value:
            node["custom"] = detail_data or []
        elif node_type == ElementOperationEnum.PYTHON_CODE.value:
            node["func"] = (detail_data or [{}])[0].get("func")
        if override.get("condition_value") is not None:
            node["condition_value"] = deepcopy(override["condition_value"])

    @classmethod
    def _execute_data_source(
            cls,
            *,
            item: dict,
            test_data: ObtainTestData,
            token_data: dict,
            source_stage: str,
            require_cache_result: bool = False,
            confirm_write: bool = True,
            node_id: int | None = None,
            page_step_id: int | None = None,
    ) -> dict:
        operation_config = test_data.replace(item.get("value") if "value" in item else item.get("sql"))
        result = DataSourceExecutionRequestService.execute_operation(
            datasource_alias_id=item.get("datasource_alias"),
            project_product_id=token_data["project_product_id"],
            test_env=token_data["test_env"],
            operation_config=operation_config,
            confirm_write=confirm_write,
            source_context={
                "source_type": "agent_ui",
                "source_stage": source_stage,
                "case_id": token_data["case_id"],
                "page_step_id": page_step_id,
                "node_id": node_id,
                "execution_id": token_data["execution_id"],
            },
        )
        key = item.get("key") if "key" in item else item.get("key_list")
        if key not in [None, "", []]:
            record = cls._cache_record(key, result)
            if not record and require_cache_result:
                raise AutoUiError(
                    UI_AGENT_RUNTIME_OPERATION_INVALID,
                    value=(f"数据源操作没有返回可缓存结果，Key：{key}",),
                )
            if record:
                normalized_key = ",".join(str(part) for part in key) if isinstance(key, list) else str(key)
                test_data.set_sql_cache(normalized_key, record)
        return result

    @staticmethod
    def _cache_record(key, result: dict) -> dict | None:
        rows = result.get("rows") or []
        if rows and isinstance(rows[0], dict):
            source = rows[0].get("_source")
            return source if isinstance(source, dict) else rows[0]
        value = result.get("result")
        if result.get("command") == "HGETALL" and isinstance(value, list):
            value = dict(zip(value[::2], value[1::2]))
        if isinstance(value, dict):
            return value
        keys = key if isinstance(key, list) else [part.strip() for part in str(key or "").split(",")]
        keys = [part for part in keys if part]
        if isinstance(value, (list, tuple)):
            return {name: item for name, item in zip(keys, value)}
        return {keys[0]: value} if keys and value is not None else None

    @staticmethod
    def _resolved_node(node: dict, test_data: ObtainTestData) -> dict:
        result = deepcopy(node)
        for key in ("ope_value", "condition_value", "precondition", "postcondition"):
            if result.get(key) is not None:
                result[key] = test_data.replace(result[key])
        result.pop("func", None)
        return result

    @staticmethod
    def _test_data(runtime_variables: dict) -> ObtainTestData:
        result = ObtainTestData()
        for key, value in runtime_variables.items():
            result.set_cache(key, value)
        return result

    @staticmethod
    def _matches_environment(item: dict, test_env: int) -> bool:
        configured = item.get("test_envs") or []
        return not configured or test_env in configured

    @staticmethod
    def _find_flow_node(flow_node, node_id: int):
        if flow_node is None:
            return None
        if int(flow_node.id) == int(node_id):
            return flow_node
        for child in flow_node.children or []:
            found = AgentUiRuntimeOperationService._find_flow_node(child, node_id)
            if found:
                return found
        return None

    @staticmethod
    def _changed_bindings(before: dict, after: dict) -> dict:
        return {
            key: value
            for key, value in after.items()
            if key not in before or before[key] != value
        }

    @staticmethod
    def _idempotency_key(execution_id: str, idempotency_key: str) -> str:
        digest = hashlib.sha256(idempotency_key.encode()).hexdigest()
        return f"{AgentUiRuntimeOperationService.IDEMPOTENCY_PREFIX}:{execution_id}:{digest}"

    @staticmethod
    def _result(status: str, execution_mode: str, operation_type: str, summary: str, **extra) -> dict:
        return {
            "status": status,
            "execution_mode": execution_mode,
            "operation_type": operation_type,
            "summary": summary,
            **extra,
        }


__all__ = ["AgentUiRuntimeOperationService"]
