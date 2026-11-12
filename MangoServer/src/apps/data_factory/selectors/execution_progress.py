from django.db.models import Max, Q

from src.apps.data_factory.models import DataFactoryExecution, SqlExecutionRecord
from src.apps.data_factory.enums import DataFactoryExecutionStatusEnum, DataFactoryCleanupStatusEnum
from src.apps.data_factory.constants import CLEANUP_REPORT_CONTEXT_KEY
from src.apps.data_factory.enums.audit import DatasourceAuditStageEnum


class DatasourceExecutionProgressSelector:
    @staticmethod
    def latest_successful_operations(owners, since):
        """仅返回当前执行代次真实完成的数据源操作时间，不读取操作内容或结果。"""
        direct = Q()
        for owner in owners:
            direct |= Q(source_detail__case_detail_id=owner['detail_id'],
                        source_detail__case_attempt=owner['attempt'])
        if not direct:
            return {}
        # context 的键以双下划线开头，显式 JSON KeyTransform 避免把路径拆成空段。
        from django.db.models.fields.json import KeyTransform
        executions = DataFactoryExecution.objects.alias(
            platform_cleanup_report=KeyTransform(CLEANUP_REPORT_CONTEXT_KEY, 'context'))
        factory = Q()
        for owner in owners:
            factory |= Q(platform_cleanup_report__parent_case_detail_id=owner['detail_id'],
                         platform_cleanup_report__parent_attempt=owner['attempt'])
        mapped = dict(executions.filter(factory).filter(
                Q(status=DataFactoryExecutionStatusEnum.PROCEED.value)
                | Q(cleanup_status=DataFactoryCleanupStatusEnum.NOT_CLEANED.value)).annotate(
                    progress_owner=KeyTransform('parent_case_detail_id',
                                                KeyTransform(CLEANUP_REPORT_CONTEXT_KEY, 'context'))
                ).values_list('id', 'progress_owner'))
        if mapped:
            direct |= Q(source_type='data_factory', source_detail__execution_id__in=list(mapped))
        rows = SqlExecutionRecord.objects.filter(direct, status='success', create_time__gte=since).exclude(
            source_stage__in=[DatasourceAuditStageEnum.CONNECT.value, DatasourceAuditStageEnum.TEST_CONNECTION.value,
                              DatasourceAuditStageEnum.NETWORK_PROBE.value]).order_by().values(
                'source_detail__case_detail_id', 'source_detail__execution_id').annotate(latest=Max('update_time'))
        latest = {}
        for row in rows:
            detail_id = mapped.get(row['source_detail__execution_id']) or row['source_detail__case_detail_id']
            if detail_id is not None:
                latest[detail_id] = max(latest.get(detail_id, row['latest']), row['latest'])
        return latest
