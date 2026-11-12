from rest_framework.viewsets import ViewSet
from src.apps.evaluation.selectors.scope import ensure_dataset_access
from src.apps.evaluation.api.serializers.dataset_item import DatasetItemSerializer
from src.apps.evaluation.api.views.support import paginate, request_user
from src.apps.evaluation.exceptions import EVALUATION_DATASET_VERSION_NOT_FOUND, EvaluationError
from src.apps.evaluation.models import EvaluationDatasetItem
from src.apps.evaluation.selectors.dataset_version import get_dataset_version
from src.apps.evaluation.selectors.querysets import EvaluationQuerySelector
from src.apps.evaluation.selectors.dataset_item import get_dataset_item
from src.apps.evaluation.services.dataset.dataset_item import EvaluationDatasetItemService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0082,
)


class DatasetItemViews(ViewSet):
    model = EvaluationDatasetItem
    serializer_class = DatasetItemSerializer

    @error_response("system")
    def list(self, request, version_id=None):
        """获取评测数据项列表"""
        version = EvaluationQuerySelector.dataset_versions().select_related("dataset").filter(id=version_id).first()
        if not version:
            raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
        ensure_dataset_access(request_user(request))
        queryset = version.items.all()
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(pk=int(search)) if search.isascii() and search.isdecimal() and len(search) < 20 else queryset.none()
        return ResponseData.success(RESPONSE_MSG_0001, paginate(request, queryset, DatasetItemSerializer))

    @error_response("system")
    def create(self, request, version_id=None):
        """创建评测数据项"""
        version = get_dataset_version(version_id, request_user(request))
        serializer = DatasetItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dataset_item = EvaluationDatasetItemService.save(values=serializer.validated_data, version=version)
        return ResponseData.success(RESPONSE_MSG_0005, DatasetItemSerializer(dataset_item).data)

    @error_response("system")
    def update(self, request, pk=None):
        """更新评测数据项"""
        dataset_item = get_dataset_item(pk, request_user(request))
        serializer = DatasetItemSerializer(dataset_item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        dataset_item = EvaluationDatasetItemService.save(values=serializer.validated_data, version=dataset_item.dataset_version, instance=dataset_item)
        return ResponseData.success(RESPONSE_MSG_0082, DatasetItemSerializer(dataset_item).data)

    @error_response("system")
    def delete(self, request, pk=None):
        """删除评测数据项"""
        EvaluationDatasetItemService.delete(get_dataset_item(pk, request_user(request)))
        return ResponseData.success(RESPONSE_MSG_0002)
