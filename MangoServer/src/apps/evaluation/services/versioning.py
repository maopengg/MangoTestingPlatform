import json
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.utils import timezone
from jsonschema import Draft202012Validator, SchemaError, ValidationError as JsonSchemaValidationError
from pydantic import ValidationError
from src.apps.evaluation.enums import EvaluationVersionStatusEnum, EvaluationStatusEnum
from src.apps.evaluation.exceptions import (
    EVALUATION_DATASET_VERSION_NOT_FOUND,
    EVALUATION_PUBLISHED_VERSION_IMMUTABLE,
    EVALUATION_ITEM_SCHEMA_INVALID,
    EvaluationError,
)
from src.apps.evaluation.formatters.payload import content_hash, plaintext_secret_paths
from src.apps.evaluation.models import EvaluationDatasetVersion
from src.apps.evaluation.schemas import (
    EvaluationDatasetSchema,
)


class EvaluationVersionService:
    @classmethod
    def dataset_quality(cls, version):
        items = list(version.items.all())
        errors = []
        warnings = []
        if not items:
            errors.append({"key": "empty_dataset", "message": "数据集至少需要一个数据条目"})
        tags = {}
        labels = {}
        fingerprints = {}
        split_fingerprints = {}
        missing_expected = 0
        for dataset_item in items:
            for tag in dataset_item.tags or []:
                tags[tag] = tags.get(tag, 0) + 1
            if not dataset_item.expected_output:
                missing_expected += 1
            label = (dataset_item.expected_output or {}).get("label")
            if label is not None:
                labels[str(label)] = labels.get(str(label), 0) + 1
            fingerprint = content_hash({
                "input": dataset_item.input_data,
                "expected": dataset_item.expected_output,
                "context": dataset_item.context,
                "scenario": getattr(dataset_item, "scenario", {}) or {},
                "data_source": getattr(dataset_item, "data_source", {}) or {},
            })
            fingerprints.setdefault(fingerprint, []).append(dataset_item.id)
            split = str((dataset_item.metadata or {}).get("split") or "")
            if split:
                split_fingerprints.setdefault(fingerprint, set()).add(split)
            try:
                cls.validate_item(version, cls.item_payload(dataset_item))
            except EvaluationError as error:
                errors.append({"key": "invalid_item", "item_id": dataset_item.id, "message": error.msg})
        duplicate_groups = [values for values in fingerprints.values() if len(values) > 1]
        leakage_groups = [sorted(fingerprints[key]) for key, splits in split_fingerprints.items() if len(splits) > 1]
        if not any(item.enabled for item in items):
            errors.append({"key": "no_enabled_items", "message": "数据集至少需要一个启用的数据条目"})
        if leakage_groups:
            errors.append({"key": "split_leakage", "message": "相同数据在不同分区出现，不能发布"})
        if missing_expected:
            warnings.append({"key": "missing_expected", "count": missing_expected, "message": "数据条目缺少静态期望或动态 Oracle"})
        if duplicate_groups:
            warnings.append({"key": "duplicate_content", "groups": duplicate_groups[:20], "message": "存在内容完全重复的数据条目"})
        if leakage_groups:
            warnings.append({"key": "split_leakage", "groups": leakage_groups[:20], "message": "相同数据条目出现在不同数据分区"})
        if labels and max(labels.values()) / sum(labels.values()) > 0.8:
            warnings.append({"key": "label_imbalance", "distribution": labels, "message": "分类标签分布明显不均衡"})
        return {
            "valid": not errors,
            "item_count": len(items),
            "enabled_count": sum(item.enabled for item in items),
            "missing_expected_count": missing_expected,
            "tag_distribution": tags,
            "label_distribution": labels,
            "errors": errors,
            "warnings": warnings,
            "warning_acknowledged": bool(version.quality_warning_acknowledged_at),
        }

    @staticmethod
    def validate_dataset_schema(schema):
        try:
            config = EvaluationDatasetSchema.model_validate(schema or {})
            for item in (
                config.input_schema, config.expected_schema,
                config.context_schema, config.metadata_schema,
            ):
                Draft202012Validator.check_schema(item or {})
            return config
        except (ValidationError, SchemaError) as error:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=(str(error),)) from error

    @classmethod
    def validate_item(cls, version, sample_data):
        for field in ("expected_output", "context", "metadata", "grading_config"):
            if not isinstance(sample_data.get(field, {}), dict):
                raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=(f"{field} 必须是 JSON 对象",))
        if sample_data.get("input_data", {}) is None:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=("输入不能为 null",))
        try:
            json.dumps(sample_data, allow_nan=False)
        except (ValueError, TypeError) as error:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=("数据必须是有限数值组成的 JSON",)) from error
        schema = cls.validate_dataset_schema(version.schema_snapshot)
        from src.apps.evaluation.services.item_source import validate_item_source
        validate_item_source(sample_data.get("data_source"))
        from src.apps.evaluation.schemas.workflow import EvaluationItemScenario
        from src.apps.evaluation.services.target_input import compile_target_input
        from types import SimpleNamespace
        try:
            scenario = EvaluationItemScenario.model_validate(sample_data.get("scenario") or {})
            if scenario.turns and schema.workflow.sequence.value == "independent":
                raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=("包含轮次的条目需要选择多轮对话或时序执行",))
            for turn in scenario.turns or [SimpleNamespace(input_data=sample_data.get("input_data", {}))]:
                if getattr(turn, "kind", None) is not None and turn.kind.value == "material":
                    continue
                if not any(step.stage.value == "reference" for step in schema.workflow.steps):
                    compile_target_input(SimpleNamespace(input_data=turn.input_data), input_variables=[item.model_dump() for item in schema.input_variables])
        except ValidationError as error:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=(str(error),)) from error
        from src.apps.evaluation.schemas.case import EvaluationItemGrading
        from src.apps.evaluation.services.grading import validate_bindings
        try:
            grading = EvaluationItemGrading.model_validate(sample_data.get("grading_config") or {})
            validate_bindings(grading.graders, require_weight=False)
        except ValidationError as error:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=(str(error),)) from error

        tags = sample_data.get("tags") or []
        if not isinstance(tags, list) or any(not isinstance(item, str) or len(item) > 64 for item in tags):
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=("tags必须是长度不超过64的字符串数组",))
        if sample_data.get("priority") not in {"P0", "P1", "P2", "P3"}:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=("priority必须是P0、P1、P2或P3",))
        try:
            weight = Decimal(str(sample_data.get("weight", 1)))
            if not weight.is_finite() or weight <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=("weight必须大于0",))
        secret_paths = plaintext_secret_paths(sample_data)
        if secret_paths:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=(
                f"敏感字段必须使用密钥引用：{', '.join(secret_paths[:5])}",
            ))
        mapping = {
            "input_data": schema.input_schema,
            "expected_output": schema.expected_schema,
            "context": schema.context_schema,
            "metadata": schema.metadata_schema,
        }
        try:
            for field, field_schema in mapping.items():
                if field_schema:
                    samples = scenario.turns if scenario.turns and field != "metadata" else [sample_data]
                    for sample in samples:
                        if not isinstance(sample, dict) and sample.kind.value == "material":
                            continue
                        value = sample.get(field, {}) if isinstance(sample, dict) else getattr(sample, field)
                        if field == "expected_output" and (not getattr(sample, "score", True) or not value and any(step.stage.value == "reference" for step in schema.workflow.steps)):
                            continue
                        if "${{" in json.dumps(value, ensure_ascii=False):
                            continue  # References are validated against the schema after runtime resolution.
                        Draft202012Validator(field_schema).validate(value)
        except JsonSchemaValidationError as error:
            path = ".".join(str(item) for item in error.path)
            message = f"{field}{'.' + path if path else ''}: {error.message}"
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=(message,)) from error

    @staticmethod
    def item_payload(dataset_item):
        return {
            "input_data": dataset_item.input_data,
            "expected_output": dataset_item.expected_output,
            "context": dataset_item.context,
            "metadata": dataset_item.metadata,
            "tags": dataset_item.tags,
            "priority": dataset_item.priority,
            "weight": str(Decimal(str(dataset_item.weight)).normalize()),
            "enabled": dataset_item.enabled,
            "grading_config": dataset_item.grading_config,
            "scenario": getattr(dataset_item, "scenario", {}) or {},
            "data_source": getattr(dataset_item, "data_source", {}) or {},
        }

    @classmethod
    @transaction.atomic
    def publish_dataset_version(cls, version_id, user):
        from src.apps.evaluation.selectors.scope import ensure_dataset_access
        ensure_dataset_access(user)
        version = EvaluationDatasetVersion.objects.select_for_update().select_related("dataset").filter(id=version_id).first()
        if not version:
            raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
        if version.status != EvaluationVersionStatusEnum.DRAFT.value:
            raise EvaluationError(EVALUATION_PUBLISHED_VERSION_IMMUTABLE)
        from src.apps.evaluation.services.workflow_resources import freeze_dataset_configuration
        version.schema_snapshot = freeze_dataset_configuration(version.schema_snapshot, user, publishing=True).model_dump(mode="json")
        items = list(version.items.order_by("id"))
        if not items:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=("数据集至少需要一个数据条目",))
        for dataset_item in items:
            from src.apps.evaluation.services.item_source import freeze_item_source
            dataset_item.data_source = freeze_item_source(dataset_item.data_source, user)
            cls.validate_item(version, cls.item_payload(dataset_item))
            dataset_item.content_hash = content_hash(cls.item_payload(dataset_item))
            dataset_item.save(update_fields=["data_source", "content_hash", "update_time"])
        quality_report = cls.dataset_quality(version)
        if quality_report["errors"]:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=(quality_report["errors"][0]["message"],))
        if quality_report["warnings"] and not version.quality_warning_acknowledged_at:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=("数据质量存在警告，请先确认质量报告",))
        version.content_hash = content_hash({
            "schema": version.schema_snapshot,
            "items": [cls.item_payload(item) for item in items],
        })
        version.status = EvaluationVersionStatusEnum.PUBLISHED.value
        version.published_by = user
        version.published_at = timezone.now()
        version.quality_report = quality_report
        version.save(update_fields=["schema_snapshot", "content_hash", "status", "published_by", "published_at", "quality_report", "update_time"])
        if version.dataset.status == EvaluationStatusEnum.DRAFT.value:
            version.dataset.status = EvaluationStatusEnum.ENABLED.value
            version.dataset.save(update_fields=["status", "update_time"])
        return version

    @staticmethod
    def target_version_checksum(target):
        config = target.executor_config or {}
        if target.target_type == "api_case":
            from src.apps.auto_api.models import ApiCaseRelease, ApiCaseRevision
            revision_id = config.get("revision_id")
            if not revision_id and config.get("release_id"):
                revision_id = ApiCaseRelease.objects.filter(id=config["release_id"]).values_list("revision_id", flat=True).first()
            return ApiCaseRevision.objects.filter(id=revision_id, api_case_id=target.target_ref_id).values_list("checksum", flat=True).first() or ""
        if target.target_type == "api_info":
            from src.apps.auto_api.models import ApiInfoRelease, ApiInfoRevision
            revision_id = config.get("revision_id")
            if not revision_id and config.get("release_id"):
                revision_id = ApiInfoRelease.objects.filter(id=config["release_id"]).values_list("revision_id", flat=True).first()
            return ApiInfoRevision.objects.filter(id=revision_id, api_info_id=target.target_ref_id).values_list("checksum", flat=True).first() or ""
        if target.target_type == "mcp_tool":
            from src.apps.auto_api.models import ApiInfoRevision
            return ApiInfoRevision.objects.filter(id=config.get("revision_id"),
                api_info_id=config.get("api_info_id")).values_list("checksum", flat=True).first() or ""
        return content_hash(config)

    @staticmethod
    def next_dataset_version(dataset):
        latest = dataset.versions.order_by("-version_no").values_list("version_no", flat=True).first() or 0
        return latest + 1
