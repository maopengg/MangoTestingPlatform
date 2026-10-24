import hashlib
import json
from typing import Any

from pydantic import ValidationError

from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiInfoRevision
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
from src.apps.perf.exceptions import (
    PERF_SCENARIO_CONFIG_PERF_INVALID,
    PerfError,
)
from src.apps.perf.models import PerfScenario
from src.apps.perf.schemas.execution import PerfScenarioIR
from src.apps.perf.services.functions import collect_perf_functions
from src.apps.perf.services.load_stage import PerfLoadStageService

SENSITIVE_KEYS = {"authorization", "cookie", "password", "passwd", "secret", "token", "api_key", "apikey"}


def is_sensitive_key(key: Any) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return normalized in SENSITIVE_KEYS or normalized.endswith(("_token", "_password", "_secret", "_api_key"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def snapshot_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "***" if is_sensitive_key(key) else redact_secrets(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def extract_secrets(value: Any, prefix: str = "") -> tuple[Any, dict[str, Any]]:
    secrets = {}
    if isinstance(value, dict):
        if is_sensitive_key(value.get("key", "")) and "value" in value:
            result = dict(value)
            result["value"] = "***"
            secrets[f"{prefix}.value" if prefix else "value"] = value.get("value")
            return result, secrets
        result = {}
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if is_sensitive_key(key):
                result[key] = "***"
                secrets[path] = item
            else:
                result[key], nested = extract_secrets(item, path)
                secrets.update(nested)
        return result, secrets
    if isinstance(value, list):
        result = []
        for index, item in enumerate(value):
            path = f"{prefix}.{index}" if prefix else str(index)
            cleaned, nested = extract_secrets(item, path)
            result.append(cleaned)
            secrets.update(nested)
        return result, secrets
    return value, secrets


def ensure_required_scenario_components(steps: list[dict], stages: list[dict]) -> None:
    missing = []
    if not steps:
        missing.append("来源 Case 至少需要 1 个可执行的 HTTP 步骤")
    if not stages:
        missing.append("请配置负载")
    if missing:
        raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("；".join(missing),))


class PerfScenarioCompiler:
    ASSERTION_OPERATOR_MAP = {
        "p_is_equal_to": "eq", "p_equals": "eq", "p_is_not_equal_to": "ne",
        "p_is_less_than": "lt", "p_is_less_than_or_equal_to": "lte",
        "p_is_greater_than": "gt", "p_is_greater_than_or_equal_to": "gte",
        "p_contains": "contains", "p_is_not_none": "exists", "p_is_none": "not_exists",
    }

    @classmethod
    def compile(cls, scenario: PerfScenario) -> tuple[dict, str]:
        snapshot, digest, _ = cls.compile_with_secrets(scenario)
        return snapshot, digest

    @staticmethod
    def _as_dict(value: Any) -> dict:
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return dict(item.split("=", 1) for item in value.split("&") if "=" in item)
        return {}

    @staticmethod
    def _variable_items(items: Any) -> list[dict]:
        result = []
        for item in items or []:
            if not isinstance(item, dict) or not item.get("key"):
                continue
            envs = item.get("test_envs") or item.get("test_env") or []
            if not isinstance(envs, list):
                envs = [envs]
            result.append({"key": str(item["key"]), "value": item.get("value"),
                           "test_envs": [int(value) for value in envs if str(value).isdigit()]})
        return result

    @classmethod
    def _assertion(cls, item: dict, source: str) -> dict | None:
        operator = cls.ASSERTION_OPERATOR_MAP.get(item.get("method"))
        if not operator:
            return None
        return {"source": source, "expression": str(item.get("actual") or ""), "operator": operator,
                "expected": item.get("expect")}

    @classmethod
    def _compile_parameter(cls, *, step: dict, parameter: dict, api_payload: dict, sort: int) -> dict:
        name = parameter.get("name") or f"步骤 {sort + 1}"
        if api_payload.get("protocol_type") != ApiProtocolTypeEnum.HTTP.value:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=(f"Case 步骤“{name}”不是 HTTP API",))
        body_type = parameter.get("body_type") or api_payload.get("body_type")
        if body_type == ApiBodyTypeEnum.MULTIPART.value:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID,
                            value=(f"Case 步骤“{name}”包含文件上传，性能模式暂不支持",))
        unsupported = []
        for field, label in (("front_sql", "前置 SQL"), ("front_func", "前置函数"), ("ass_sql", "SQL 断言"),
                             ("ass_schema", "Schema 断言"), ("posterior_sql", "后置 SQL"),
                             ("posterior_func", "后置函数"), ("posterior_file", "文件下载"),
                             ("sse_config", "SSE 配置")):
            if parameter.get(field):
                unsupported.append(label)
        if unsupported:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID,
                            value=(f"Case 步骤“{name}”包含性能模式暂不支持的能力：{'、'.join(unsupported)}",))
        body_config = parameter.get("body_config")
        body = None
        if isinstance(body_config, dict):
            body = body_config.get("body_text") if body_config.get("source_type") == "template" else body_config.get(
                "body", body_config)
        headers = {}
        headers.update(api_payload.get("headers") if isinstance(api_payload.get("headers"), dict) else {})
        headers.update(parameter.get("resolved_headers") if isinstance(parameter.get("resolved_headers"), dict) else {})
        checks = []
        for item in parameter.get("ass_jsonpath") or []:
            check = cls._assertion(item, "jsonpath")
            if check:
                checks.append(check)
        for item in parameter.get("ass_general") or []:
            check = cls._assertion(item, "variable")
            if check:
                checks.append(check)
        if parameter.get("ass_json_all") is not None:
            # API自动化中的“JSON 一致”会忽略响应里未配置的对象字段，
            # 性能编译结果必须保持相同语义，不能退化为整段 JSON 严格相等。
            checks.append(
                {"source": "json", "expression": "", "operator": "contains", "expected": parameter["ass_json_all"]})
        if parameter.get("ass_text_all") is not None:
            checks.append({"source": "text", "expression": "", "operator": "eq", "expected": parameter["ass_text_all"]})
        extractors = [
            {"name": str(item.get("key")), "source": "jsonpath", "expression": str(item.get("value")), "required": True}
            for item in parameter.get("posterior_response") or [] if item.get("key") and item.get("value")
        ]
        extractors.extend(
            {"name": str(item.get("key")), "source": "regex", "expression": str(item.get("value")), "required": True}
            for item in parameter.get("posterior_response_text") or [] if item.get("key") and item.get("value")
        )
        request = dict(api_payload)
        request["body_type"] = body_type
        return {
            "step_key": f"{step.get('logical_id') or step.get('id')}-{parameter.get('id') or sort}",
            "name": name, "sort": sort, "weight": 1,
            "think_time_ms": int(parameter.get("posterior_sleep") or 0) * 1000,
            "api_info_id": int(step.get("api_info_id") or step.get("api_info")),
            "api_revision_id": int(step.get("api_info_revision_id") or step.get("pinned_api_info_revision")),
            "api_revision_checksum": str(step.get("api_info_snapshot", {}).get("checksum") or ""),
            "request": request,
            "request_override": {"headers": headers, "params": cls._as_dict(parameter.get("params")), "body": body},
            "extractors": extractors, "checks": checks,
            "retries": int(parameter.get("error_retry") or 0),
            "retry_interval_ms": int(parameter.get("retry_interval") or 0) * 1000,
            "allow_failure": bool(parameter.get("allow_failure", False)),
        }

    @classmethod
    def compile_with_secrets(cls, scenario: PerfScenario) -> tuple[dict, str, dict[str, Any]]:
        release = scenario.source_case_release
        revision = scenario.source_case_revision
        if not scenario.source_api_case_id or not release or not revision:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("请先选择一个已发布的API自动化 Case",))
        if release.api_case_id != scenario.source_api_case_id or release.revision_id != revision.id:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("来源 Case、发布版本与固定修订不一致",))
        try:
            ApiCaseRevisionService.verify_execution_revision(revision)
        except AutoApiError as error:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID,
                            value=("来源 Case 修订不可执行或完整性校验失败",)) from error
        payload = revision.payload or {}
        case_payload = payload.get("api_case") or {}
        dependencies = payload.get("dependencies") or {}
        unsupported_case = []
        for field, label in (("front_sql", "前置 SQL"), ("posterior_sql", "后置 SQL"),
                             ("front_auth_config", "授权配置"), ("front_public", "全局变量依赖")):
            if case_payload.get(field):
                unsupported_case.append(label)
        if dependencies.get("data_factory_configs"):
            unsupported_case.append("数据工厂")
        if case_payload.get("parametrize"):
            unsupported_case.append("Case 参数组；请改用 perf_* 数据方法后重新发布 Case")
        try:
            collect_perf_functions(payload)
        except ValueError as error:
            unsupported_case.append(str(error))
        if unsupported_case:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID,
                            value=(f"来源 Case 包含性能模式暂不支持的能力：{'、'.join(unsupported_case)}",))

        raw_steps = payload.get("api_case_detailed") or []
        legacy_revision_ids = [int(item.get("api_info_revision_id") or item.get("pinned_api_info_revision")) for item in
                               raw_steps if not item.get("api_info_snapshot")]
        revisions = {item.id: item for item in ApiInfoRevision.objects.filter(id__in=legacy_revision_ids)}
        steps = []
        for source_step in sorted(raw_steps, key=lambda item: item.get("case_sort") or 0):
            api_snapshot = source_step.get("api_info_snapshot") or {}
            api_revision_id = int(
                source_step.get("api_info_revision_id") or source_step.get("pinned_api_info_revision") or 0)
            if api_snapshot:
                api_payload = ApiInfoRuntimeService.normalize_payload(api_snapshot.get("payload") or {})
                api_checksum = api_snapshot.get("checksum") or ""
            else:
                api_revision = revisions.get(api_revision_id)
                if not api_revision:
                    raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("来源 Case 引用的 API 修订不存在",))
                ApiInfoRevisionService.verify_revision(api_revision, executable=True)
                api_payload = ApiInfoRuntimeService.normalize_payload(api_revision.payload)
                api_checksum = api_revision.checksum
            for parameter in source_step.get("api_case_detailed_parameter") or []:
                compiled = cls._compile_parameter(step=source_step, parameter=parameter, api_payload=api_payload,
                                                  sort=len(steps))
                compiled["api_revision_checksum"] = api_checksum
                steps.append(compiled)

        case_headers = (payload.get("runtime") or {}).get("resolved_front_headers") or {}
        for step in steps:
            step["request_override"]["headers"] = {**case_headers, **step["request_override"]["headers"]}
        stages = PerfLoadStageService.build_stages(scenario)
        ensure_required_scenario_components(steps, stages)
        raw = {
            "schema_version": 1, "scenario_id": scenario.id, "scenario_version": scenario.version,
            "name": scenario.name, "project_product_id": scenario.project_product_id, "module_id": scenario.module_id,
            "engine": scenario.engine, "source_case_id": scenario.source_api_case_id,
            "source_case_release_id": release.id, "source_case_revision_id": revision.id,
            "source_case_revision_checksum": revision.checksum, "source_case_version_label": release.version_label,
            "initial_variables": cls._variable_items(case_payload.get("front_custom") or []),
            "execution_mode": "sequential", "load_type": scenario.load_type,
            "load_profile": PerfLoadStageService.serialize(scenario)["profile"],
            "total_iterations": scenario.total_iterations,
            "start_users": scenario.start_users,
            "user_wait_min_ms": scenario.user_wait_min_ms, "user_wait_max_ms": scenario.user_wait_max_ms,
            "steps": steps, "stages": stages,
            "performance_goal": {"template_key": scenario.goal_template_key, "p95_ms": scenario.goal_p95_ms,
                                 "max_error_rate": float(scenario.goal_max_error_rate),
                                 "min_load_achievement_rate": float(scenario.goal_min_load_achievement_rate)},
        }
        try:
            functions = collect_perf_functions(raw)
        except ValueError as error:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=(str(error),)) from error
        raw["perf_functions"] = functions
        raw["schema_version"] = 2 if functions else 1
        cleaned, runtime_secrets = extract_secrets(raw)
        try:
            snapshot = PerfScenarioIR.model_validate(cleaned).model_dump(mode="json")
        except ValidationError as exc:
            message = "; ".join(error["msg"] for error in exc.errors()[:5])
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=(message,)) from exc
        return snapshot, snapshot_hash(snapshot), runtime_secrets
