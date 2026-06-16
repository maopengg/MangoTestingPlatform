# -*- coding: utf-8 -*-
import hashlib
import json
from typing import Any

from src.apps.functional_test.models import (
    FunctionalTestContextResource,
    ManualTestAutomationBinding,
    ManualTestCase,
    ManualTestSuite,
)
from src.common.enums.manual_test_enum import (
    FunctionalTestContextContentTypeEnum,
    FunctionalTestContextKeyEnum,
    ManualTestAutomationImpactStatusEnum,
    ManualTestChangeStatusEnum,
    ManualTestOptimizeStatusEnum,
    ManualTestRelationTypeEnum,
    ManualTestSourceTypeEnum,
    ManualTestSyncStatusEnum,
    ManualTestTypeEnum,
)
from src.common.enums.tools_enum import (
    ApiCaseScenarioLayerEnum,
    ApiCaseScenarioTagEnum,
    ApiCaseScenarioTypeEnum,
    CaseLevelEnum,
)


MAX_CASES_PER_IMPORT = 200


ENUM_FIELD_MAP = {
    "test_types": ManualTestTypeEnum,
    "priority": CaseLevelEnum,
    "scenario_layer": ApiCaseScenarioLayerEnum,
    "scenario_type": ApiCaseScenarioTypeEnum,
    "scenario_tags": ApiCaseScenarioTagEnum,
    "change_status": ManualTestChangeStatusEnum,
    "automation_impact_status": ManualTestAutomationImpactStatusEnum,
}

ENUM_SYNONYMS = {
    "priority": {"高": 0, "p0": 0, "紧急": 0, "中": 1, "p1": 1, "低": 2, "p2": 2, "极低": 3, "p3": 3},
    "scenario_layer": {
        "api": ApiCaseScenarioLayerEnum.API.value,
        "接口": ApiCaseScenarioLayerEnum.API.value,
        "接口层": ApiCaseScenarioLayerEnum.API.value,
        "组件": ApiCaseScenarioLayerEnum.API.value,
        "组件层": ApiCaseScenarioLayerEnum.API.value,
        "接口/组件层": ApiCaseScenarioLayerEnum.API.value,
        "component": ApiCaseScenarioLayerEnum.API.value,
        "integration": ApiCaseScenarioLayerEnum.INTEGRATION.value,
        "集成": ApiCaseScenarioLayerEnum.INTEGRATION.value,
        "集成层": ApiCaseScenarioLayerEnum.INTEGRATION.value,
        "integration集成": ApiCaseScenarioLayerEnum.INTEGRATION.value,
        "e2e": ApiCaseScenarioLayerEnum.E2E.value,
        "端到端": ApiCaseScenarioLayerEnum.E2E.value,
        "端到端层": ApiCaseScenarioLayerEnum.E2E.value,
    },
    "scenario_type": {
        "normal": ApiCaseScenarioTypeEnum.NORMAL.value,
        "正常": ApiCaseScenarioTypeEnum.NORMAL.value,
        "正常场景": ApiCaseScenarioTypeEnum.NORMAL.value,
        "success": ApiCaseScenarioTypeEnum.NORMAL.value,
        "exception": ApiCaseScenarioTypeEnum.EXCEPTION.value,
        "异常": ApiCaseScenarioTypeEnum.EXCEPTION.value,
        "异常场景": ApiCaseScenarioTypeEnum.EXCEPTION.value,
        "error": ApiCaseScenarioTypeEnum.EXCEPTION.value,
        "boundary": ApiCaseScenarioTypeEnum.BOUNDARY.value,
        "边界": ApiCaseScenarioTypeEnum.BOUNDARY.value,
        "边界场景": ApiCaseScenarioTypeEnum.BOUNDARY.value,
        "permission": ApiCaseScenarioTypeEnum.PERMISSION.value,
        "权限": ApiCaseScenarioTypeEnum.PERMISSION.value,
        "权限场景": ApiCaseScenarioTypeEnum.PERMISSION.value,
        "auth": ApiCaseScenarioTypeEnum.PERMISSION.value,
        "data": ApiCaseScenarioTypeEnum.DATA.value,
        "数据": ApiCaseScenarioTypeEnum.DATA.value,
        "数据场景": ApiCaseScenarioTypeEnum.DATA.value,
        "flow": ApiCaseScenarioTypeEnum.FLOW.value,
        "流程": ApiCaseScenarioTypeEnum.FLOW.value,
        "流程场景": ApiCaseScenarioTypeEnum.FLOW.value,
    },
    "scenario_tags": {
        "smoke": ApiCaseScenarioTagEnum.SMOKE.value,
        "冒烟": ApiCaseScenarioTagEnum.SMOKE.value,
        "regression": ApiCaseScenarioTagEnum.REGRESSION.value,
        "回归": ApiCaseScenarioTagEnum.REGRESSION.value,
        "main_flow": ApiCaseScenarioTagEnum.MAIN_FLOW.value,
        "主流程": ApiCaseScenarioTagEnum.MAIN_FLOW.value,
        "core_link": ApiCaseScenarioTagEnum.CORE_LINK.value,
        "核心链路": ApiCaseScenarioTagEnum.CORE_LINK.value,
        "high_frequency": ApiCaseScenarioTagEnum.HIGH_FREQUENCY.value,
        "高频": ApiCaseScenarioTagEnum.HIGH_FREQUENCY.value,
        "blocking": ApiCaseScenarioTagEnum.BLOCKING.value,
        "阻塞": ApiCaseScenarioTagEnum.BLOCKING.value,
        "online_inspection": ApiCaseScenarioTagEnum.PRODUCTION_INSPECTION.value,
        "线上巡检": ApiCaseScenarioTagEnum.PRODUCTION_INSPECTION.value,
        "production_inspection": ApiCaseScenarioTagEnum.PRODUCTION_INSPECTION.value,
        "生产巡检": ApiCaseScenarioTagEnum.PRODUCTION_INSPECTION.value,
        "production_regression": ApiCaseScenarioTagEnum.PRODUCTION_REGRESSION.value,
        "生产回归": ApiCaseScenarioTagEnum.PRODUCTION_REGRESSION.value,
    },
    "test_types": {
        "手工": ManualTestTypeEnum.MANUAL.value,
        "手工测试": ManualTestTypeEnum.MANUAL.value,
        "manual_test": ManualTestTypeEnum.MANUAL.value,
        "api": ManualTestTypeEnum.API.value,
        "api_automation": ManualTestTypeEnum.API.value,
        "接口": ManualTestTypeEnum.API.value,
        "接口自动化": ManualTestTypeEnum.API.value,
        "ui": ManualTestTypeEnum.UI.value,
        "ui_automation": ManualTestTypeEnum.UI.value,
        "界面": ManualTestTypeEnum.UI.value,
        "界面自动化": ManualTestTypeEnum.UI.value,
        "pytest": ManualTestTypeEnum.PYTEST.value,
        "单元自动化": ManualTestTypeEnum.PYTEST.value,
        "perf": ManualTestTypeEnum.PERF.value,
        "性能": ManualTestTypeEnum.PERF.value,
        "monitoring": ManualTestTypeEnum.MONITORING.value,
        "监控": ManualTestTypeEnum.MONITORING.value,
    },
}


def _hash_text(value: str | None) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _normalize_label(value: Any) -> str:
    return str(value).strip().lower()


class FunctionalTestContextResourceService:
    @classmethod
    def render_suite_context(cls, suite: ManualTestSuite, context_keys: list[str]) -> dict:
        resources = list(
            FunctionalTestContextResource.objects.filter(
                suite=suite,
                context_key__in=context_keys,
                enabled=True,
            ).order_by("context_key", "id")
        )
        grouped = {key: [] for key in context_keys}
        for resource in resources:
            grouped.setdefault(resource.context_key, []).append(cls.render_resource(resource))
        return {key: "\n\n".join(items) for key, items in grouped.items()}

    @staticmethod
    def render_resource(resource: FunctionalTestContextResource) -> str:
        parts = [f"标题：{resource.title}", f"资料类型：{resource.content_type}"]
        if resource.content_type == FunctionalTestContextContentTypeEnum.URL.value:
            parts.append(f"URL类型：{resource.url_type}")
        if resource.content:
            parts.append(f"内容：{resource.content}")
        if resource.file_name or resource.file_path:
            parts.append(f"文件：{resource.file_name or ''} {resource.file_path or ''}".strip())
        if resource.extracted_text:
            parts.append(f"解析文本：{resource.extracted_text}")
        return "\n".join(parts)


def enum_label(enum_cls, key: Any) -> str:
    return enum_cls.obj().get(key) or enum_cls.obj().get(str(key)) or str(key)


class ManualEnumMapper:
    @classmethod
    def map_value(cls, field: str, value: Any) -> tuple[Any, dict | None]:
        enum_cls = ENUM_FIELD_MAP.get(field)
        if enum_cls is None:
            return value, None
        if field in ("test_types", "scenario_tags"):
            values = value if isinstance(value, list) else ([] if value in (None, "") else [value])
            mapped = []
            warnings = []
            for item in values:
                mapped_item, warning = cls.map_single(field, item, enum_cls)
                if warning:
                    warnings.append(warning)
                elif mapped_item not in mapped:
                    mapped.append(mapped_item)
            return mapped, {"field": field, "items": warnings} if warnings else None
        return cls.map_single(field, value, enum_cls)

    @classmethod
    def map_single(cls, field: str, value: Any, enum_cls) -> tuple[Any, dict | None]:
        raw = value
        if isinstance(value, dict):
            value = value.get("value", value.get("label"))
        valid_keys = enum_cls.get_key_list()
        if value in valid_keys:
            return value, None
        try:
            int_value = int(value)
            if int_value in valid_keys:
                return int_value, None
        except (TypeError, ValueError):
            pass
        label_map = enum_cls.reversal_obj()
        if value in label_map:
            return label_map[value], None
        normalized = _normalize_label(value)
        synonyms = ENUM_SYNONYMS.get(field, {})
        if normalized in synonyms:
            return synonyms[normalized], None
        for label, key in label_map.items():
            if _normalize_label(label) == normalized:
                return key, None
        return None, {"field": field, "raw": raw, "message": "枚举值无法确定，请人工确认"}


class ManualTestValidationService:
    @classmethod
    def normalize_suite_cases(cls, payload: dict) -> dict:
        suite = payload.get("suite") or {}
        cases = payload.get("cases") or []
        warnings = list(payload.get("warnings") or [])
        if not isinstance(suite, dict) or not isinstance(cases, list):
            return {"valid": False, "status": "invalid", "errors": ["解析输出必须包含 suite 对象和 cases 数组"], "suite": {}, "cases": []}
        if len(cases) > MAX_CASES_PER_IMPORT:
            return {"valid": False, "status": "invalid", "errors": [f"单次最多允许导入 {MAX_CASES_PER_IMPORT} 条 case"], "suite": suite, "cases": []}
        suite, suite_warnings = cls._normalize_suite(suite)
        normalized_cases = []
        errors = []
        warnings.extend(suite_warnings)
        for index, case in enumerate(cases, start=1):
            if not isinstance(case, dict):
                errors.append(f"第 {index} 条 case 不是对象")
                continue
            normalized, case_warnings, case_errors = cls._normalize_case(case, index)
            normalized_cases.append(normalized)
            warnings.extend(case_warnings)
            errors.extend(case_errors)
        if not suite.get("requirement_name"):
            errors.append("需求名称不能为空")
        if not normalized_cases:
            errors.append("至少需要一条 case")
        status = "invalid" if errors else ("need_confirm" if warnings else "valid")
        return {
            "valid": not errors and not warnings,
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "suite": suite,
            "cases": normalized_cases,
        }

    @staticmethod
    def _normalize_suite(suite: dict) -> tuple[dict, list]:
        data = dict(suite)
        warnings = []
        for key in ("source_url",):
            value = data.get(key)
            if value and not str(value).startswith(("http://", "https://")):
                warnings.append({"field": key, "raw": value, "message": "链接格式需要人工确认"})
        return data, warnings

    @staticmethod
    def _normalize_case(case: dict, index: int) -> tuple[dict, list, list]:
        data = dict(case)
        warnings = []
        errors = []
        if not data.get("title"):
            errors.append(f"第 {index} 条 case 标题不能为空")
        if len(str(data.get("title") or "")) > 256:
            errors.append(f"第 {index} 条 case 标题不能超过256字符")
        for field in ("test_types", "priority", "scenario_layer", "scenario_type", "scenario_tags"):
            mapped, warning = ManualEnumMapper.map_value(field, data.get(field))
            if mapped is not None:
                data[field] = mapped
            if warning:
                warnings.append(warning)
        data["test_types"] = data.get("test_types") or [ManualTestTypeEnum.MANUAL.value]
        if data.get("priority") not in CaseLevelEnum.get_key_list():
            data["priority"] = CaseLevelEnum.P1.value
        if data.get("scenario_layer") not in ApiCaseScenarioLayerEnum.get_key_list():
            data["scenario_layer"] = ApiCaseScenarioLayerEnum.API.value
        if data.get("scenario_type") not in ApiCaseScenarioTypeEnum.get_key_list():
            data["scenario_type"] = ApiCaseScenarioTypeEnum.NORMAL.value
        data["scenario_tags"] = data.get("scenario_tags") or []
        for field in ("project_product", "project_product_id", "module", "module_id"):
            value = data.get(field)
            if value in (None, ""):
                continue
            try:
                data[field] = int(value)
            except (TypeError, ValueError):
                warnings.append({"field": field, "raw": value, "message": "项目产品或模块ID需要人工确认"})
        data["case_no"] = str(data.get("case_no") or "").strip()
        source_text = data.get("source_text") or data.get("test_point") or data.get("title") or ""
        data["source_hash"] = _hash_text(source_text)
        return data, warnings, errors
