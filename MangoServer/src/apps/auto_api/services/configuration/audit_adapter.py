"""供通用 CRUD 调用的 API 配置审计适配器。"""

from src.apps.auto_api.services.configuration.version import ApiConfigDiffService, ApiConfigSnapshotService


class ModelCrudConfigAuditAdapter:
    @staticmethod
    def capture(instance):
        return ApiConfigSnapshotService.capture_for_instance(instance)

    @staticmethod
    def record_change(
            instance,
            *,
            action: str,
            before_snapshot=None,
            after_snapshot=None,
            operator_id=None,
            source: str = "page",
            summary=None,
    ):
        return ApiConfigDiffService.record_instance_change(
            instance,
            action=action,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            operator_id=operator_id,
            source=source,
            summary=summary,
        )

    @staticmethod
    def record_delete(instance, before_snapshot, *, operator_id=None, source="page"):
        target = ApiConfigSnapshotService.resolve_target(instance)
        if target is None:
            return None
        object_type, object_id = target
        return ApiConfigDiffService.record_change(
            object_type=object_type,
            object_id=object_id,
            action="delete",
            before_snapshot=before_snapshot,
            after_snapshot=ApiConfigSnapshotService.capture_target(object_type, object_id),
            operator_id=operator_id,
            source=source,
        )
