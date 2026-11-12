"""Case configuration, target binding and read-only grading preview."""

from copy import deepcopy
from types import SimpleNamespace
from django.db import transaction
from pydantic import ValidationError
from src.apps.evaluation.constants import TARGET_EXECUTION_PERMISSIONS
from src.apps.evaluation.enums import EvaluationStatusEnum, EvaluationVersionStatusEnum
from src.apps.evaluation.exceptions import EVALUATION_OBJECT_NOT_FOUND, EVALUATION_TARGET_ACCESS_DENIED, EvaluationError
from src.apps.evaluation.formatters.payload import plaintext_secret_paths
from src.apps.evaluation.formatters.case_description import case_description, scenario_description
from src.apps.evaluation.models import EvaluationCase
from src.apps.evaluation.schemas import EvaluationCaseConfig
from src.apps.evaluation.selectors.scope import ensure_product_scope
from src.apps.evaluation.services.targets.adapters import EvaluationTargetAdapterRegistry
from src.apps.evaluation.services.grading.grading import resolve_graders, validate_bindings
from src.apps.evaluation.services.assets.validation import invalid_config, validate_relation
from src.apps.user.services.authorization.permission import PermissionMenuService


class EvaluationCaseService:
    @staticmethod
    def normalize(values, instance=None):
        values = dict(validate_relation(dict(values), instance))
        product = values.get("project_product", getattr(instance, "project_product", None))
        if product is None:
            raise invalid_config("请指定项目产品")
        if instance is not None and product and product.id != instance.project_product_id:
            raise invalid_config("已有 Case 不可更换项目产品")
        if instance is not None and values and not {"config", "dataset_version", "status"}.intersection(values):
            return values
        if "config" in values or "description" in values:
            raw = deepcopy(values.get("config", getattr(instance, "config", {})))
            legacy = raw.get("assessment") or (getattr(instance, "config", {}) or {}).get("assessment")
            if legacy:
                if instance is None or "description" not in values:
                    values["description"] = scenario_description(values.get("description", getattr(instance, "description", None)), legacy)
                raw.pop("assessment", None)
                values["config"] = raw
        version = values.get("dataset_version", getattr(instance, "dataset_version", None))
        status = values.get("status", getattr(instance, "status", EvaluationStatusEnum.DRAFT.value))
        raw = values.get("config", getattr(instance, "config", {}))
        if version is None:
            if status != EvaluationStatusEnum.DRAFT.value:
                raise invalid_config("请先配置已发布数据集版本，再启用 Case")
            if raw == {}:
                if instance is None or "config" in values:
                    values["config"] = {}
                return values
        elif version.status != EvaluationVersionStatusEnum.PUBLISHED.value:
            raise invalid_config("Case 必须绑定已发布的数据集版本")
        if plaintext_secret_paths(raw):
            raise invalid_config("敏感配置必须使用凭据引用")
        raw = deepcopy(raw)
        binding = raw.get("target") or {}
        if binding.get("type") == "api_info":
            # These former target parameters never affected an individual interface.
            parameters = binding.get("parameters") or {}
            parameters.pop("case_sort", None)
            parameters.pop("static_output", None)
            binding["parameters"] = parameters
        if binding.get("type") == "api_info" and binding.get("ref_id"):
            from src.apps.evaluation.selectors.target import published_interfaces
            interface = published_interfaces(product.id).filter(pk=binding["ref_id"]).first()
            if interface is None or not interface.published_release_id:
                raise invalid_config("请选择当前项目产品下已发布的 HTTP 或 SSE 接口")
            binding["version_ref"] = {"kind": "api_info_release", "id": interface.published_release_id}
        try:
            config = EvaluationCaseConfig.model_validate(raw)
        except ValidationError as error:
            raise invalid_config(str(error)) from error
        if config.target.type.value not in EvaluationTargetAdapterRegistry.adapters:
            raise invalid_config("目标类型未注册")
        validate_bindings(config.grading.default_graders + config.grading.required_graders, require_weight=False)
        for item in EvaluationCaseService.selected_items(version, config) if version is not None else []:
            resolve_graders(config.grading, item.grading_config)
        if "config" in values or instance is None:
            values["config"] = config.model_dump(mode="json")
            values["config"].pop("assessment", None)
        return values

    @staticmethod
    def selected_items(version, config, item_ids=None):
        if version is None:
            raise invalid_config("请先在详情页配置评测数据集和发布版本")
        items = list(version.items.filter(enabled=True).order_by("id"))
        configured = set(config.data_selection.item_ids)
        available = {item.id for item in items}
        if configured - available:
            raise invalid_config("配置引用了不存在或停用的数据条目")
        allowed = available - configured if config.data_selection.exclude else configured or available
        if item_ids is not None:
            requested = set(item_ids)
            if not requested or len(requested) != len(item_ids) or requested - allowed:
                raise invalid_config("执行范围不能为空、重复或超出 Case 的数据选择")
            allowed = requested
        selected = [item for item in items if item.id in allowed]
        if not selected:
            raise invalid_config("Case 没有可执行的数据条目")
        from src.apps.evaluation.schemas.dataset import EvaluationDatasetSchema
        dataset_config = EvaluationDatasetSchema.model_validate(getattr(version, "schema_snapshot", {}) or {})
        if dataset_config.workflow.sequence.value != "independent":
            group_orders = {}
            for item in selected:
                scenario = item.scenario or {}
                if scenario.get("group_key"):
                    group_orders[scenario["group_key"]] = max(group_orders.get(scenario["group_key"], 0), scenario.get("order", 0))
            for item in items:
                scenario = item.scenario or {}
                if item.id not in allowed and scenario.get("group_key") in group_orders and scenario.get("order", 0) <= group_orders[scenario["group_key"]]:
                    item._dependency_only = True
                    selected.append(item)
            selected.sort(key=lambda item: item.id)
        return selected

    @classmethod
    @transaction.atomic
    def save(cls, *, values, instance=None):
        if instance is not None:
            instance = EvaluationCase.objects.select_for_update().select_related("project_product", "dataset_version__dataset").get(pk=instance.pk)
        normalized = cls.normalize(values, instance)
        case = instance or EvaluationCase()
        for key, value in normalized.items():
            setattr(case, key, value)
        if "description" in normalized and isinstance(case.config, dict) and "assessment" in case.config:
            case.config = deepcopy(case.config)
            case.config.pop("assessment", None)
        case.save()
        return case

    @staticmethod
    def runtime_target(binding, product_id):
        parameters = dict(binding.get("parameters") or {})
        version = binding.get("version_ref")
        if version:
            kind = version["kind"]
            field = "mcp_tool_snapshot_id" if kind == "mcp_tool_snapshot" else "revision_id" if kind.endswith("_revision") else "release_id"
            parameters[field] = version["id"]
        return SimpleNamespace(target_type=binding["type"], target_ref_id=binding.get("ref_id"), executor_config=parameters, project_product_id=product_id)

    @classmethod
    def target(cls, case, config=None):
        parsed = EvaluationCaseConfig.model_validate(config if config is not None else case.config)
        return cls.runtime_target(parsed.target.model_dump(mode="json"), case.project_product_id)

    @classmethod
    def validate_execution(cls, case, user):
        ensure_product_scope(user, case.project_product_id)
        if case.status != EvaluationStatusEnum.ENABLED.value:
            raise invalid_config("Case 未启用")
        cls.require_configuration(case)
        values = cls.normalize({"config": case.config}, case)
        config = EvaluationCaseConfig.model_validate(values["config"])
        if config.target.type.value not in ("api_info", "script"):
            raise invalid_config("当前仅支持接口管理和 Python 脚本，请重新选择被测目标")
        if config.target.type.value == "api_info" and config.target.ref_id is None:
            raise invalid_config("请选择已发布的 HTTP 或 SSE 接口")
        target = cls.target(case, values["config"])
        cls.ensure_target_access(target, user)
        EvaluationTargetAdapterRegistry.get(target.target_type).validate_target(target)
        return config, target

    @staticmethod
    def ensure_target_access(target, user):
        ensure_product_scope(user, target.project_product_id)
        if user is None:
            raise EvaluationError(EVALUATION_TARGET_ACCESS_DENIED)
        permission = TARGET_EXECUTION_PERMISSIONS.get(target.target_type)
        if permission and permission not in PermissionMenuService.permission_keys_for_user(user):
            raise EvaluationError(EVALUATION_TARGET_ACCESS_DENIED)

    @classmethod
    def validate(cls, case_id, user):
        case = EvaluationCase.objects.select_related("dataset_version__dataset", "project_product").filter(pk=case_id).first()
        if case is None:
            raise EvaluationError(EVALUATION_OBJECT_NOT_FOUND)
        ensure_product_scope(user, case.project_product_id)
        cls.require_configuration(case)
        values = cls.normalize({"config": case.config}, case)
        config = EvaluationCaseConfig.model_validate(values["config"])
        target = cls.target(case, values["config"])
        cls.ensure_target_access(target, user)
        EvaluationTargetAdapterRegistry.get(target.target_type).validate_target(target)
        return {"valid": True, "item_count": len(cls.selected_items(case.dataset_version, config))}

    @classmethod
    def grading_preview(cls, case, user):
        ensure_product_scope(user, case.project_product_id)
        cls.require_configuration(case)
        config = EvaluationCaseConfig.model_validate(case.config)
        return {"items": [
            {"item_id": item.id, "graders": [{**binding.model_dump(mode="json"), "source": source} for binding, source in resolve_graders(config.grading, item.grading_config)]}
            for item in cls.selected_items(case.dataset_version, config)
        ]}

    @staticmethod
    def require_configuration(case):
        if case.dataset_version_id is None or not case.config:
            raise invalid_config("请先在详情页配置评测数据、被测目标和评分规则")

    @classmethod
    @transaction.atomic
    def copy(cls, case, user):
        ensure_product_scope(user, case.project_product_id)
        for index in range(1, 1001):
            name = f"{case.name[:110]} 副本 {index}"
            if not EvaluationCase.objects.filter(project_product_id=case.project_product_id, name=name).exists():
                return cls.save(values={"name": name, "project_product": case.project_product, "module": case.module,
                    "dataset_version": case.dataset_version, "config": deepcopy(case.config), "description": case_description(case),
                    "owner": user, "update_user": user, "status": EvaluationStatusEnum.DRAFT.value})
        raise invalid_config("无法生成可用的副本名称")
