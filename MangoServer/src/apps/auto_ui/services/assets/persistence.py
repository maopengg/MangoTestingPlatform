"""UI 自动化模型写入的应用层公共实现。"""

from django.core.exceptions import FieldError
from django.core.paginator import Paginator
from django.db import transaction

from src.apps.auto_api.services.configuration.version import ApiConfigDiffService, ApiConfigSnapshotService
from src.apps.auto_ui.exceptions import AutoUiError
from src.common.database import ModelMutationValidationError, model_payload, save_model
from src.common.exceptions import SAVE_VALIDATION_FAILED, UPDATE_VALIDATION_FAILED


class UiPersistenceService:
    @staticmethod
    def create_model(model, payload: dict, presenter=model_payload) -> dict:
        try:
            with transaction.atomic():
                instance = save_model(model, payload)
                ApiConfigDiffService.record_instance_change(
                    instance,
                    action="create",
                    after_snapshot=ApiConfigSnapshotService.capture_for_instance(instance).snapshot,
                    source="internal",
                )
        except ModelMutationValidationError as error:
            raise AutoUiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error
        return presenter(instance)

    @staticmethod
    def update_model(instance, payload: dict, presenter=model_payload) -> dict:
        before_snapshot = ApiConfigSnapshotService.capture_for_instance(instance).snapshot
        try:
            with transaction.atomic():
                instance = save_model(
                    type(instance),
                    payload,
                    instance=instance,
                    partial=True,
                )
                ApiConfigDiffService.record_instance_change(
                    instance,
                    action="update",
                    before_snapshot=before_snapshot,
                    after_snapshot=ApiConfigSnapshotService.capture_for_instance(instance).snapshot,
                    source="internal",
                )
        except ModelMutationValidationError as error:
            raise AutoUiError(UPDATE_VALIDATION_FAILED, value=(error.errors,)) from error
        return presenter(instance)

    @staticmethod
    def create(serializer_class, payload: dict) -> dict:
        serializer = serializer_class(data=payload)
        if not serializer.is_valid():
            raise AutoUiError(SAVE_VALIDATION_FAILED, value=(serializer.errors,))
        with transaction.atomic():
            instance = serializer.save()
            ApiConfigDiffService.record_instance_change(
                instance,
                action="create",
                after_snapshot=ApiConfigSnapshotService.capture_for_instance(instance).snapshot,
                source="internal",
            )
        return dict(serializer.data)

    @staticmethod
    def update(instance, serializer_class, payload: dict) -> dict:
        before_snapshot = ApiConfigSnapshotService.capture_for_instance(instance).snapshot
        serializer = serializer_class(instance=instance, data=payload, partial=True)
        if not serializer.is_valid():
            raise AutoUiError(UPDATE_VALIDATION_FAILED, value=(serializer.errors,))
        with transaction.atomic():
            instance = serializer.save()
            ApiConfigDiffService.record_instance_change(
                instance,
                action="update",
                before_snapshot=before_snapshot,
                after_snapshot=ApiConfigSnapshotService.capture_for_instance(instance).snapshot,
                source="internal",
            )
        return dict(serializer.data)

    @staticmethod
    def paginate(queryset, page: int, page_size: int, serializer_class) -> dict:
        try:
            queryset = serializer_class.setup_eager_loading(queryset)
        except (AttributeError, FieldError):
            pass
        paginator = Paginator(queryset, int(page_size))
        current = int(page)
        if current > paginator.num_pages and paginator.num_pages > 0:
            current = paginator.num_pages
        page_obj = paginator.page(current)
        return {
            "items": [dict(item) for item in serializer_class(page_obj.object_list, many=True).data],
            "count": paginator.count,
            "page": current,
            "page_size": int(page_size),
        }

    @staticmethod
    def paginate_with_presenter(queryset, page: int, page_size: int, presenter) -> dict:
        paginator = Paginator(queryset, int(page_size))
        current = int(page)
        if current > paginator.num_pages and paginator.num_pages > 0:
            current = paginator.num_pages
        page_obj = paginator.page(current)
        return {
            "items": [presenter(item) for item in page_obj.object_list],
            "count": paginator.count,
            "page": current,
            "page_size": int(page_size),
        }

    @staticmethod
    @transaction.atomic
    def delete(instance) -> None:
        instance.delete()
