import json
from pydantic import ValidationError
from src.apps.evaluation.api.serializers.dataset import DatasetSerializer
from src.apps.evaluation.models import EvaluationDataset
from src.apps.evaluation.selectors.querysets import EvaluationQuerySelector
from src.apps.evaluation.selectors.assets import filter_dataset_task_types
from src.apps.evaluation.schemas.assets import EvaluationDatasetTaskTypes
from src.apps.evaluation.services.validation import invalid_config
from src.apps.evaluation.selectors.scope import ensure_dataset_access, scope_dataset_queryset
from src.apps.evaluation.api.views.support import request_user
from src.common.responses.model_crud import ModelCRUD


class DatasetCRUD(ModelCRUD):
    model = EvaluationDataset
    queryset = EvaluationQuerySelector.datasets()
    serializer_class = DatasetSerializer
    serializer = DatasetSerializer
    page_permission_key = "evaluation.dataset"

    def is_valid_query_param(self, key):
        if key == "task_types":
            return False
        return super().is_valid_query_param(key)

    def filter_queryset_by_data_scope(self, request, queryset):
        queryset = scope_dataset_queryset(queryset, request_user(request))
        raw = request.query_params.get("task_types")
        if raw:
            try:
                parsed = json.loads(raw)
                task_types = EvaluationDatasetTaskTypes.model_validate({"task_type": parsed}).task_type if parsed != [] else []
            except (json.JSONDecodeError, ValidationError) as error:
                raise invalid_config("任务类型筛选必须为字符串数组") from error
            queryset = filter_dataset_task_types(queryset, task_types)
        return queryset

    def has_data_scope_permission(self, request, data):
        ensure_dataset_access(request_user(request))
        return True

    def has_instance_data_scope_permission(self, request, instance):
        ensure_dataset_access(request_user(request))
        return True
