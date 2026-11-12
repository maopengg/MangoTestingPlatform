from django.db import transaction
from src.apps.auto_api.models import ApiCaseDetailedParameter
from src.apps.evaluation.enums import EvaluationVersionStatusEnum
from src.apps.evaluation.exceptions import (
    EVALUATION_PUBLISHED_VERSION_IMMUTABLE,
    EVALUATION_ITEM_SCHEMA_INVALID,
    EVALUATION_TARGET_ACCESS_DENIED,
    EvaluationError,
)
from src.apps.evaluation.formatters.payload import content_hash
from src.apps.evaluation.models import EvaluationDatasetVersion, EvaluationDatasetItem
from src.apps.evaluation.services.dataset.versioning import EvaluationVersionService
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.evaluation.selectors.scope import scope_queryset, ensure_dataset_access


class EvaluationApiCaseImportService:
    EXPECTED_KEYS = ("evaluation_expected", "expected", "expected_output", "ground_truth")

    @staticmethod
    def ensure_source_access(user):
        from src.apps.user.services.authorization.permission import PermissionMenuService
        if user is None or "api.case:read" not in PermissionMenuService.permission_keys_for_user(user):
            raise EvaluationError(EVALUATION_TARGET_ACCESS_DENIED)

    @classmethod
    def audit(cls, case_ids, user):
        cls.ensure_source_access(user)
        queryset = scope_queryset(ApiQuerySelector.api_case().filter(id__in=case_ids), user).select_related("project_product", "module")
        rows = []
        found_ids = set()
        for case in queryset.order_by("id"):
            found_ids.add(case.id)
            parameters = list(ApiCaseDetailedParameter.objects.filter(case_detailed__case=case))
            variants = case.parametrize if isinstance(case.parametrize, list) else []
            expected_rows = sum(
                cls._expected_from_variant(item)[0] is not None
                for item in variants if isinstance(item, dict)
            )
            extractor_count = sum(bool(item.posterior_response or item.posterior_response_text) for item in parameters)
            structured_assertion_count = sum(bool(item.ass_json_all or item.ass_jsonpath or item.ass_schema) for item in parameters)
            issues = []
            if not variants:
                issues.append("没有参数化用户/场景数据")
            if expected_rows < len(variants):
                issues.append("部分场景缺少显式预期输出")
            if not extractor_count:
                issues.append("没有从实际响应提取标准化业务结果")
            if not structured_assertion_count:
                issues.append("现有断言不足以验证结构化业务结果")
            rows.append({
                "case_id": case.id, "case_name": case.name,
                "project_product_id": case.project_product_id, "module_id": case.module_id,
                "variant_count": len(variants), "ground_truth_count": expected_rows,
                "output_extractor_count": extractor_count,
                "structured_assertion_count": structured_assertion_count,
                "ready": not issues, "issues": issues,
                "recommendation": "补齐每个用户场景的真值，并统一提取 contract_ids、behavior、message 后再导入",
            })
        for missing_id in sorted(set(case_ids) - found_ids):
            rows.append({
                "case_id": missing_id,
                "case_name": "",
                "ready": False,
                "issues": ["Case不存在或没有访问权限"],
                "recommendation": "确认Case ID及源项目产品的访问权限",
            })
        return rows

    @staticmethod
    def _expected_from_variant(variant):
        for key in EvaluationApiCaseImportService.EXPECTED_KEYS:
            if key in variant:
                return variant[key], key
        return None, None

    @classmethod
    @transaction.atomic
    def import_cases(cls, version_id, case_ids, *, user, allow_missing_expected=False):
        cls.ensure_source_access(user)
        ensure_dataset_access(user)
        version = EvaluationDatasetVersion.objects.select_for_update().select_related("dataset").filter(id=version_id).first()
        if not version:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=("数据集版本不存在",))
        if version.status != EvaluationVersionStatusEnum.DRAFT.value:
            raise EvaluationError(EVALUATION_PUBLISHED_VERSION_IMMUTABLE)
        cases = scope_queryset(ApiQuerySelector.api_case().filter(id__in=case_ids), user).order_by("id")
        imported, skipped = [], []
        for case in cases:
            variants = case.parametrize if isinstance(case.parametrize, list) else []
            for index, variant in enumerate(variants, start=1):
                if not isinstance(variant, dict):
                    skipped.append({"case_id": case.id, "index": index, "reason": "参数化数据不是对象"})
                    continue
                expected, expected_key = cls._expected_from_variant(variant)
                if expected is None and not allow_missing_expected:
                    skipped.append({"case_id": case.id, "index": index, "reason": "缺少效果真值"})
                    continue
                clean_input = {
                    key: value for key, value in variant.items()
                    if key not in cls.EXPECTED_KEYS
                }
                context = {}
                payload = {
                    "input_data": {"api_case_id": case.id, "case_name": case.name, "parameters": clean_input},
                    "expected_output": expected if isinstance(expected, dict) else {"value": expected},
                    "context": context,
                    "metadata": {"source_type": "api_case", "source_id": case.id, "source_index": index, "expected_source_key": expected_key},
                    "tags": list(dict.fromkeys(["api_case_import", *(case.scenario_tags or [])])),
                    "priority": f"P{case.level}" if case.level in (0, 1, 2, 3) else "P1",
                    "weight": 1, "enabled": expected is not None,
                }
                EvaluationVersionService.validate_item(version, payload)
                dataset_item, was_created = EvaluationDatasetItem.objects.update_or_create(
                    dataset_version=version, metadata__source_type="api_case",
                    metadata__source_id=case.id, metadata__source_index=index, defaults=payload,
                )
                dataset_item.content_hash = content_hash(EvaluationVersionService.item_payload(dataset_item))
                dataset_item.save(update_fields=["content_hash", "update_time"])
                imported.append({"id": dataset_item.id, "created": was_created})
        if imported:
            from src.apps.evaluation.services.dataset.dataset_item import EvaluationDatasetItemService
            EvaluationDatasetItemService.reset_quality_ack(version)
        return {"imported": imported, "skipped": skipped, "imported_count": len(imported), "skipped_count": len(skipped)}
