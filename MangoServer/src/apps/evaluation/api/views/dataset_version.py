from rest_framework.viewsets import ViewSet
from src.apps.evaluation.selectors.scope import ensure_dataset_access
from src.apps.evaluation.api.serializers.dataset_version import DatasetVersionSerializer
from src.apps.evaluation.api.views.support import paginate, request_user
from src.apps.evaluation.exceptions import (
    EVALUATION_DATASET_VERSION_NOT_FOUND,
    EVALUATION_OBJECT_NOT_FOUND,
    EvaluationError,
)
from src.apps.evaluation.models import EvaluationDatasetVersion
from src.apps.evaluation.selectors.dataset_version import get_dataset_version, version_diff
from src.apps.evaluation.selectors.querysets import EvaluationQuerySelector
from src.apps.evaluation.services.dataset.dataset_version import EvaluationDatasetVersionService
from src.apps.evaluation.services.dataset.importing import EvaluationApiCaseImportService
from src.apps.evaluation.services.dataset.versioning import EvaluationVersionService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0005, RESPONSE_MSG_0082


class DatasetVersionViews(ViewSet):
    model = EvaluationDatasetVersion
    serializer_class = DatasetVersionSerializer

    @error_response("system")
    def list(self, request, dataset_id=None):
        """获取评测数据集版本列表"""
        dataset = EvaluationQuerySelector.datasets().filter(id=dataset_id).first()
        if not dataset:
            raise EvaluationError(EVALUATION_OBJECT_NOT_FOUND)
        ensure_dataset_access(request_user(request))
        versions = EvaluationQuerySelector.dataset_versions().filter(dataset_id=dataset.id)
        return ResponseData.success(RESPONSE_MSG_0001, paginate(request, versions, DatasetVersionSerializer))

    @error_response("system")
    def retrieve(self, request, pk=None):
        """获取评测数据集版本详情"""
        version = EvaluationQuerySelector.dataset_versions().select_related("dataset").filter(id=pk).first()
        if not version:
            raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
        ensure_dataset_access(request_user(request))
        return ResponseData.success(RESPONSE_MSG_0001, DatasetVersionSerializer(version).data)

    @error_response("system")
    def workflow_resources(self, request, pk=None):
        """获取数据集工作流可用资源"""
        from src.apps.evaluation.selectors.workflow import resource_choices
        from src.apps.evaluation.enums.workflow import EvaluationWorkflowActionEnum
        from src.apps.evaluation.services.assets.validation import invalid_config
        get_dataset_version(pk, request_user(request))
        try:
            action = EvaluationWorkflowActionEnum(request.query_params.get("action"))
            product_id = int(request.query_params.get("project_product_id"))
            page = max(1, int(request.query_params.get("page") or 1))
            module_id = int(request.query_params["module_id"]) if request.query_params.get("module_id") else None
        except (ValueError, TypeError) as error:
            raise invalid_config("请选择有效的流程类型与项目产品") from error
        return ResponseData.success(RESPONSE_MSG_0001, resource_choices(action, request_user(request), product_id,
            search=request.query_params.get("search") or "", page=page, module_id=module_id))

    @error_response("system")
    def input_preview(self, request, pk=None):
        """预览评测数据集输入"""
        from types import SimpleNamespace
        from pydantic import ValidationError
        from src.apps.evaluation.schemas.dataset import EvaluationDatasetSchema
        from src.apps.evaluation.services.targets.target_input import compile_target_input
        from src.apps.evaluation.services.assets.validation import invalid_config
        from src.apps.evaluation.formatters.payload import mask_sensitive
        get_dataset_version(pk, request_user(request))
        try:
            config = EvaluationDatasetSchema.model_validate({"input_variables": request.data.get("input_variables")})
        except ValidationError as error:
            raise invalid_config(str(error)) from error
        result = compile_target_input(SimpleNamespace(input_data=request.data.get("input_data")),
            input_variables=[item.model_dump() for item in config.input_variables])
        return ResponseData.success(RESPONSE_MSG_0001, mask_sensitive(result))

    @error_response("system")
    def create(self, request, dataset_id=None):
        """创建评测数据集版本"""
        serializer = DatasetVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = EvaluationDatasetVersionService.create(
            dataset_id=dataset_id, values=serializer.validated_data, user=request_user(request),
            source_version_id=request.data.get("source_version_id"),
        )
        return ResponseData.success(RESPONSE_MSG_0005, DatasetVersionSerializer(version).data)

    @error_response("system")
    def update(self, request, pk=None):
        """更新评测数据集版本"""
        version = get_dataset_version(pk, request_user(request))
        serializer = DatasetVersionSerializer(version, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        version = EvaluationDatasetVersionService.update(version, serializer.validated_data)
        return ResponseData.success(RESPONSE_MSG_0082, DatasetVersionSerializer(version).data)

    @error_response("system")
    def delete(self, request, pk=None):
        """删除评测数据集版本"""
        EvaluationDatasetVersionService.delete(pk, request_user(request))
        return ResponseData.success(RESPONSE_MSG_0082)

    @error_response("system")
    def publish(self, request, pk=None):
        """发布评测数据集版本"""
        version = EvaluationQuerySelector.dataset_versions().select_related("dataset").filter(id=pk).first()
        if not version:
            raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
        ensure_dataset_access(request_user(request))
        version = EvaluationVersionService.publish_dataset_version(pk, request_user(request))
        return ResponseData.success(RESPONSE_MSG_0082, DatasetVersionSerializer(version).data)

    @error_response("system")
    def quality(self, request, pk=None):
        """获取评测数据集质量检查结果"""
        version = EvaluationQuerySelector.dataset_versions().select_related("dataset").filter(id=pk).first()
        if not version:
            raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
        ensure_dataset_access(request_user(request))
        return ResponseData.success(RESPONSE_MSG_0001, EvaluationVersionService.dataset_quality(version))

    @error_response("system")
    def acknowledge_quality(self, request, pk=None):
        """确认评测数据集质量检查结果"""
        version = get_dataset_version(pk, request_user(request))
        report = EvaluationDatasetVersionService.acknowledge_quality(version, request_user(request))
        return ResponseData.success(RESPONSE_MSG_0082, report)

    @error_response("system")
    def diff(self, request, pk=None):
        """比较评测数据集版本版本差异"""
        current = get_dataset_version(pk, request_user(request))
        baseline = get_dataset_version(request.query_params.get("baseline_version_id"), request_user(request))
        return ResponseData.success(RESPONSE_MSG_0001, version_diff(current, baseline))

    @error_response("system")
    def audit_api_cases(self, request, pk=None):
        """检查评测数据集可导入的 API 用例"""
        EvaluationApiCaseImportService.ensure_source_access(request_user(request))
        version = EvaluationQuerySelector.dataset_versions().select_related("dataset").filter(id=pk).first()
        if not version:
            raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
        ensure_dataset_access(request_user(request))
        case_ids = request.data.get("case_ids") or []
        return ResponseData.success(RESPONSE_MSG_0001, {
            "items": EvaluationApiCaseImportService.audit(case_ids, request_user(request)),
        })

    @error_response("system")
    def import_api_cases(self, request, pk=None):
        """将 API 用例导入评测数据集"""
        EvaluationApiCaseImportService.ensure_source_access(request_user(request))
        version = EvaluationQuerySelector.dataset_versions().select_related("dataset").filter(id=pk).first()
        if not version:
            raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
        ensure_dataset_access(request_user(request))
        result = EvaluationApiCaseImportService.import_cases(
            version.id, request.data.get("case_ids") or [], user=request_user(request),
            allow_missing_expected=bool(request.data.get("allow_missing_expected", False)),
        )
        return ResponseData.success(RESPONSE_MSG_0005, result)
