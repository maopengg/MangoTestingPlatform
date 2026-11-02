from jsonschema import validate as validate_json
from src.apps.evaluation.services.target_input import compile_target_input
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseRelease,
    ApiCaseRevision,
    ApiInfo,
    ApiInfoRelease,
    ApiInfoRevision,
)
from src.apps.auto_api.services.test_case.test_api_info import TestApiInfo
from src.apps.auto_api.services.test_case.test_case import TestCase
from src.apps.evaluation.exceptions import (
    EVALUATION_ADAPTER_UNSUPPORTED,
    EVALUATION_TARGET_CONFIG_INVALID,
    EVALUATION_TARGET_CALL_FAILED,
    EvaluationError,
)
from src.apps.evaluation.formatters.payload import apply_mapping, mask_sensitive


class BaseTargetAdapter:
    key = "base"

    @classmethod
    def validate_target(cls, target):
        return None

    @classmethod
    def execute(cls, *, target, dataset_item, mapping, execution, user_id):
        raise NotImplementedError

    @staticmethod
    def result(*, output, raw_output_ref=None, execution_ref=None):
        return {
            "output": mask_sensitive(output),
            "raw_output_ref": raw_output_ref or {},
            "execution_ref": execution_ref or {},
        }

    @staticmethod
    def ensure_response_available(response, *, failed=False):
        code = response.get("code") if response else None
        if response and (response.get("request_protocol_type") or response.get("response_mode")) == "sse":
            if failed or not response.get("sse_events") or response.get("sse_stop_reason") in ("timeout", "max_duration", "max_event_count"):
                raise EvaluationError(EVALUATION_TARGET_CALL_FAILED, value=(f"SSE {response.get('protocol_status') or code}: 未获得完整有效的响应流",))
        if code in (401, 403, 408, 429) or (isinstance(code, int) and code >= 500) or (failed and code is None):
            raise EvaluationError(EVALUATION_TARGET_CALL_FAILED, value=(f"HTTP {code}" if code is not None else "传输或协议错误",))


class StaticTargetAdapter(BaseTargetAdapter):
    key = "static"

    @classmethod
    def execute(cls, *, target, dataset_item, mapping, execution, user_id):
        source = target.executor_config.get("static_output") or {}
        output = apply_mapping(source, mapping.output_mapping)
        return cls.result(output=output)


class ApiCaseTargetAdapter(BaseTargetAdapter):
    key = "api_case"

    @classmethod
    def validate_target(cls, target):
        if not target.target_ref_id or not ApiCase.objects.filter(id=target.target_ref_id, project_product_id=target.project_product_id).exists():
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("API Case不存在",))
        config = target.executor_config or {}
        if not config.get("revision_id") and not config.get("release_id"):
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("API Case评测必须固定revision_id或release_id",))
        if config.get("revision_id") and not ApiCaseRevision.objects.filter(
            id=config["revision_id"], api_case_id=target.target_ref_id,
        ).exists():
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("API Case修订不存在或不属于当前Case",))
        if config.get("release_id") and not ApiCaseRelease.objects.filter(
            id=config["release_id"], api_case_id=target.target_ref_id,
        ).exists():
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("API Case发布版本不存在或不属于当前Case",))

    @classmethod
    def execute(cls, *, target, dataset_item, mapping, execution, user_id):
        cls.validate_target(target)
        compiled = compile_target_input(dataset_item, mapping.input_variable, getattr(mapping, "input_variables", None))
        config = target.executor_config or {}
        revision_id = config.get("revision_id")
        if not revision_id and config.get("release_id"):
            release = ApiCaseRelease.objects.filter(id=config["release_id"], api_case_id=target.target_ref_id).first()
            revision_id = release.revision_id if release else None
        if not revision_id:
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("API Case发布版本不存在或不属于当前Case",))
        runtime = TestCase(
            user_id=user_id,
            test_env=execution.test_env,
            case_id=target.target_ref_id,
            revision_id=revision_id,
            release_id=config.get("release_id"),
            update_case_status=False,
        )
        runtime.test_setup.timeout = int(config.get("_timeout_seconds") or runtime.test_setup.timeout or 60)
        result = runtime.test_case(case_sort=config.get("case_sort"), parametrize=compiled)
        raw = result.model_dump(mode="json")
        for step in raw.get("steps", []):
            cls.ensure_response_available(step.get("response"), failed=step.get("failure_category") == "protocol_call_failed")
        output = apply_mapping(raw, mapping.output_mapping)
        return cls.result(output=output, raw_output_ref={"trace_id": result.trace_id},
                          execution_ref={"type": "api_case", "id": target.target_ref_id, "trace_id": result.trace_id})


class ApiInfoTargetAdapter(BaseTargetAdapter):
    key = "api_info"

    @classmethod
    def validate_target(cls, target):
        from src.apps.auto_api.enums.protocol import ApiProtocolTypeEnum
        from src.apps.auto_api.selectors.revision import fixed_interface_contract
        if not target.target_ref_id or not ApiInfo.objects.filter(id=target.target_ref_id, project_product_id=target.project_product_id).exists():
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("API Info不存在",))
        config = target.executor_config or {}
        if not config.get("revision_id") and not config.get("release_id"):
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("API Info评测必须固定revision_id或release_id",))
        if config.get("revision_id") and not ApiInfoRevision.objects.filter(
            id=config["revision_id"], api_info_id=target.target_ref_id,
        ).exists():
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("API Info修订不存在或不属于当前接口",))
        if config.get("release_id") and not ApiInfoRelease.objects.filter(
            id=config["release_id"], api_info_id=target.target_ref_id,
        ).exists():
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("API Info发布版本不存在或不属于当前接口",))
        contract = fixed_interface_contract(target.target_ref_id, config.get("revision_id"), config.get("release_id"))
        allowed = (ApiProtocolTypeEnum.MCP.value,) if target.target_type == "mcp_tool" else (
            ApiProtocolTypeEnum.HTTP.value, ApiProtocolTypeEnum.SSE.value, ApiProtocolTypeEnum.MCP.value)
        if contract is None or contract["config"].get("protocol_type") not in allowed:
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("所选接口修订协议与测评目标类型不一致",))

    @classmethod
    def execute(cls, *, target, dataset_item, mapping, execution, user_id):
        cls.validate_target(target)
        config = target.executor_config or {}
        revision_id = config.get("revision_id")
        if not revision_id and config.get("release_id"):
            release = ApiInfoRelease.objects.filter(id=config["release_id"], api_info_id=target.target_ref_id).first()
            revision_id = release.revision_id if release else None
        if not revision_id:
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("API Info发布版本不存在或不属于当前接口",))
        runtime = TestApiInfo(user_id=user_id, test_env=execution.test_env)
        from src.apps.test_center.enums.environment import AutoTypeEnum
        runtime.test_setup.automation_type = AutoTypeEnum.EVALUATION.value
        runtime.test_setup.timeout = int(config.get("_timeout_seconds") or runtime.test_setup.timeout or 60)
        parameters = compile_target_input(dataset_item, mapping.input_variable, getattr(mapping, "input_variables", None))
        raw = runtime.api_info_run(
            target.target_ref_id, revision_id=revision_id, release_id=config.get("release_id"), runtime_parameters=parameters,
        )
        cls.ensure_response_available(raw, failed=raw.get("call_success") is False)
        output = apply_mapping(raw, mapping.output_mapping)
        return cls.result(output=output, raw_output_ref={"protocol_status": raw.get("protocol_status")},
                          execution_ref={"type": "api_info", "id": target.target_ref_id})


class McpToolTargetAdapter(BaseTargetAdapter):
    key = "mcp_tool"

    @classmethod
    def api_target(cls, target):
        from copy import copy
        api_info_id = (target.executor_config or {}).get("api_info_id")
        if not api_info_id:
            raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID,
                value=("MCP测评请重新绑定 API 自动化中的 MCP 接口及已发布修订",))
        result = copy(target)
        result.target_ref_id = api_info_id
        return result

    @classmethod
    def validate_target(cls, target):
        return ApiInfoTargetAdapter.validate_target(cls.api_target(target))

    @classmethod
    def execute(cls, *, target, **kwargs):
        return ApiInfoTargetAdapter.execute(target=cls.api_target(target), **kwargs)


class PythonTargetAdapter(BaseTargetAdapter):
    key = "script"

    @classmethod
    def validate_target(cls, target):
        from src.apps.evaluation.services.python_target import validate_python_target
        validate_python_target(target.executor_config.get("code") or "")

    @classmethod
    def execute(cls, *, target, dataset_item, mapping, execution, user_id):
        from src.apps.evaluation.services.python_target import run_python_target
        output = run_python_target(
            target.executor_config.get("code") or "",
            compile_target_input(dataset_item, mapping.input_variable, getattr(mapping, "input_variables", None)),
            (dataset_item.context or {}).get("target_visible") or {},
            int(target.executor_config.get("_timeout_seconds") or 60),
        )
        return cls.result(output=apply_mapping(output, mapping.output_mapping), execution_ref={"type": cls.key})


class EvaluationTargetAdapterRegistry:
    adapters = {item.key: item for item in (
        StaticTargetAdapter, ApiCaseTargetAdapter, ApiInfoTargetAdapter, McpToolTargetAdapter, PythonTargetAdapter,
    )}

    @classmethod
    def get(cls, key):
        adapter = cls.adapters.get(key)
        if not adapter:
            raise EvaluationError(EVALUATION_ADAPTER_UNSUPPORTED, value=(key,))
        return adapter
