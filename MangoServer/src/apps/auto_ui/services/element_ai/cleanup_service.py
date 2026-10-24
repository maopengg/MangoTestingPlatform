from datetime import timedelta

from django.db.models import Count, QuerySet
from django.utils import timezone

from src.apps.auto_ui.models import UiElementHealRecord, UiElementSnapshot
from src.apps.system.services.system_config import SystemConfigService


class ElementAiCleanupService:
    """限制元素 AI 基线和自愈历史，避免大 JSON 记录无限增长。"""

    PENDING_HEAL_STATUSES = (1, 2, 5)
    PENDING_HEAL_RETENTION_DAYS = 30
    RESOLVED_HEAL_RETENTION_DAYS = 90
    INACTIVE_SNAPSHOT_RETENTION_DAYS = 7
    PENDING_HEAL_KEEP_PER_SCOPE = 20
    RESOLVED_HEAL_KEEP_PER_SCOPE = 50
    ACTIVE_SNAPSHOT_KEEP_PER_SCOPE = 5
    DELETE_BATCH_SIZE = 500

    @classmethod
    def cleanup(cls) -> dict:
        now = timezone.now()
        pending_retention_days = SystemConfigService.get_ranged_int('UI_PENDING_HEAL_RETENTION_DAYS')
        resolved_retention_days = SystemConfigService.get_ranged_int('UI_RESOLVED_HEAL_RETENTION_DAYS')
        inactive_retention_days = SystemConfigService.get_ranged_int('UI_INACTIVE_SNAPSHOT_RETENTION_DAYS')
        pending_cutoff = now - timedelta(days=pending_retention_days)
        resolved_cutoff = now - timedelta(days=resolved_retention_days)
        inactive_snapshot_cutoff = now - timedelta(days=inactive_retention_days)

        expired_pending_heal_count = cls._delete_queryset(
            UiElementHealRecord.objects.filter(
                status__in=cls.PENDING_HEAL_STATUSES,
                create_time__lt=pending_cutoff,
            )
        )
        expired_resolved_heal_count = cls._delete_queryset(
            UiElementHealRecord.objects.exclude(
                status__in=cls.PENDING_HEAL_STATUSES,
            ).filter(create_time__lt=resolved_cutoff)
        )
        capped_pending_heal_count = cls._trim_scopes(
            UiElementHealRecord.objects.filter(status__in=cls.PENDING_HEAL_STATUSES),
            cls.PENDING_HEAL_KEEP_PER_SCOPE,
        )
        capped_resolved_heal_count = cls._trim_scopes(
            UiElementHealRecord.objects.exclude(status__in=cls.PENDING_HEAL_STATUSES),
            cls.RESOLVED_HEAL_KEEP_PER_SCOPE,
        )
        inactive_snapshot_count = cls._delete_queryset(
            UiElementSnapshot.objects.exclude(status=1).filter(
                create_time__lt=inactive_snapshot_cutoff,
            )
        )
        capped_active_snapshot_count = cls._trim_scopes(
            UiElementSnapshot.objects.filter(status=1),
            cls.ACTIVE_SNAPSHOT_KEEP_PER_SCOPE,
        )

        heal_deleted_count = (
                expired_pending_heal_count
                + expired_resolved_heal_count
                + capped_pending_heal_count
                + capped_resolved_heal_count
        )
        snapshot_deleted_count = inactive_snapshot_count + capped_active_snapshot_count
        return {
            'pending_heal_retention_days': pending_retention_days,
            'resolved_heal_retention_days': resolved_retention_days,
            'inactive_snapshot_retention_days': inactive_retention_days,
            'pending_heal_keep_per_scope': cls.PENDING_HEAL_KEEP_PER_SCOPE,
            'resolved_heal_keep_per_scope': cls.RESOLVED_HEAL_KEEP_PER_SCOPE,
            'active_snapshot_keep_per_scope': cls.ACTIVE_SNAPSHOT_KEEP_PER_SCOPE,
            'expired_pending_heal_count': expired_pending_heal_count,
            'expired_resolved_heal_count': expired_resolved_heal_count,
            'capped_pending_heal_count': capped_pending_heal_count,
            'capped_resolved_heal_count': capped_resolved_heal_count,
            'inactive_snapshot_count': inactive_snapshot_count,
            'capped_active_snapshot_count': capped_active_snapshot_count,
            'heal_deleted_count': heal_deleted_count,
            'snapshot_deleted_count': snapshot_deleted_count,
            'deleted_count': heal_deleted_count + snapshot_deleted_count,
        }

    @classmethod
    def trim_heal_scope(cls, element_id: int, test_env: int) -> dict:
        scope = UiElementHealRecord.objects.filter(
            element_id=element_id,
            test_env=test_env,
        )
        pending_deleted_count = cls._trim_scopes(
            scope.filter(status__in=cls.PENDING_HEAL_STATUSES),
            cls.PENDING_HEAL_KEEP_PER_SCOPE,
        )
        resolved_deleted_count = cls._trim_scopes(
            scope.exclude(status__in=cls.PENDING_HEAL_STATUSES),
            cls.RESOLVED_HEAL_KEEP_PER_SCOPE,
        )
        return {
            'pending_deleted_count': pending_deleted_count,
            'resolved_deleted_count': resolved_deleted_count,
            'deleted_count': pending_deleted_count + resolved_deleted_count,
        }

    @classmethod
    def _trim_scopes(cls, queryset: QuerySet, keep_count: int) -> int:
        if keep_count < 1:
            return cls._delete_queryset(queryset)
        scopes = (
            queryset.values('element_id', 'test_env')
            .annotate(total=Count('id'))
            .filter(total__gt=keep_count)
        )
        deleted_count = 0
        for scope in scopes.iterator(chunk_size=200):
            scoped_queryset = queryset.filter(
                element_id=scope['element_id'],
                test_env=scope['test_env'],
            )
            while True:
                old_ids = list(
                    scoped_queryset.order_by('-id')
                    .values_list('id', flat=True)[keep_count:keep_count + cls.DELETE_BATCH_SIZE]
                )
                if not old_ids:
                    break
                queryset.model.objects.filter(id__in=old_ids).delete()
                deleted_count += len(old_ids)
        return deleted_count

    @classmethod
    def _delete_queryset(cls, queryset: QuerySet) -> int:
        deleted_count = 0
        while True:
            ids = list(
                queryset.order_by('id')
                .values_list('id', flat=True)[:cls.DELETE_BATCH_SIZE]
            )
            if not ids:
                break
            queryset.model.objects.filter(id__in=ids).delete()
            deleted_count += len(ids)
        return deleted_count
