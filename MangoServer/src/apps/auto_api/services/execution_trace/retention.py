from time import monotonic

from django.db import transaction
from django.db.models import Exists, OuterRef, Q

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStatus
from src.apps.auto_api.models import ApiCaseExecutionTrace, ApiCaseExecutionStep
from src.apps.auto_api.models.resource_cleanup import ApiCaseExecutionResource
from src.apps.auto_api.models.callback import ApiCaseCallbackRun


class ApiTraceRetentionService:
    CHILD_BATCH_SIZE = 500
    MAX_BATCHES = 200
    RUN_SECONDS = 30

    @staticmethod
    def eligible(cutoff):
        owned = ApiCaseExecutionResource.objects.filter(trace_id=OuterRef('pk'))
        callbacks = ApiCaseCallbackRun.objects.filter(trace_id=OuterRef('pk'))
        return ApiCaseExecutionTrace.objects.filter(
            create_time__lt=cutoff, finished_at__isnull=False,
            status__in=[ApiCaseTraceStatus.SUCCESS, ApiCaseTraceStatus.FAIL, ApiCaseTraceStatus.SKIP],
        ).annotate(has_resource=Exists(owned), has_callback=Exists(callbacks)).filter(
            has_resource=False, has_callback=False).filter(
            Q(summary__review_required=False) | Q(summary__review_required__isnull=True))

    @classmethod
    def delete_batch(cls, cutoff):
        # 锁住一个已结束的父记录，每次只删除有限子记录；失败仅回滚本批，可从剩余记录续跑。
        with transaction.atomic():
            trace = cls.eligible(cutoff).select_for_update(skip_locked=True).order_by('id').first()
            if trace is None:
                return 0
            children = list(ApiCaseExecutionStep.objects.filter(trace_id=trace.id).order_by('id').values_list(
                'id', flat=True)[:cls.CHILD_BATCH_SIZE])
            if children:
                return ApiCaseExecutionStep.objects.filter(trace_id=trace.id, id__in=children).delete()[0]
            # 受保护资源引用由外键继续兜底，不绕过 Django Collector。
            return trace.delete()[0]

    @classmethod
    def cleanup(cls, cutoff):
        started, deleted, batches = monotonic(), 0, 0
        while batches < cls.MAX_BATCHES and monotonic() - started < cls.RUN_SECONDS:
            count = cls.delete_batch(cutoff)
            if not count:
                break
            deleted += count
            batches += 1
        return {'deleted_count': deleted, 'batches': batches,
                'has_more': cls.eligible(cutoff).exists()}
