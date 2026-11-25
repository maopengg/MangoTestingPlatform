from django.db.models import Q

from src.apps.data_factory.models import SqlExecutionRecord
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class ExecutionAuditSelector:
    @staticmethod
    def search_batch(query, start, end, cursor=None, limit=25, *, product_ids=None):
        rows = SqlExecutionRecord.objects.filter(create_time__gte=start, create_time__lt=end)
        scope = [query.project_product_id] if query.project_product_id is not None else product_ids
        if scope is not None:
            rows = rows.filter(project_product_id__in=scope)
        if query.test_env is not None:
            rows = rows.filter(test_env=query.test_env)
        if cursor:
            rows = rows.filter(Q(create_time__lt=cursor[0]) | Q(create_time=cursor[0], id__lt=cursor[1]))
        return list(rows.only('id', 'create_time', 'source_type', 'source_id', 'source_stage', 'source_detail',
                              'result_truncated').order_by('-create_time', '-id')[:limit])

    @staticmethod
    def search_payload(record_id, max_length):
        from django.db.models import F, TextField
        from django.db.models.functions import Cast, JSONObject, Substr
        return SqlExecutionRecord.objects.filter(id=record_id).annotate(search_payload=Substr(Cast(JSONObject(**{
            '执行内容': F('sql_text'), '执行参数': F('sql_parameters'), '结果预览': F('result_preview'),
        }), TextField()), 1, max_length + 1)).values_list('search_payload', flat=True).first()

    @staticmethod
    def filter_case(queryset, case_id):
        from src.apps.data_factory.enums.execution import DataFactoryExecutionSourceEnum
        return queryset.filter(
            Q(source_detail__case_id=case_id)
            | Q(source_type='api_case', source_id=case_id)
            | Q(source_type='data_factory', source_detail__case_source_type=DataFactoryExecutionSourceEnum.API_CASE.value,
                source_detail__case_source_id=case_id))

    @staticmethod
    def case_operations_confirmed(detail_id, attempt, request_ids=()):
        own = Q(source_detail__case_detail_id=detail_id, source_detail__case_attempt=attempt)
        if request_ids:
            own |= Q(request_id__in=request_ids)
        return not SqlExecutionRecord.objects.filter(own).filter(
            Q(status='running') | Q(source_detail__outcome_unknown=True,
                source_detail__outcome_resolution__isnull=True)).exists()

    @staticmethod
    def permit_evidence(record_ids):
        return {record.id: record for record in SqlExecutionRecord.objects.filter(
            id__in=record_ids,
        ).only('id', 'request_id', 'database_id', 'source_detail', 'status', 'source_type', 'source_id', 'source_stage',
               'datasource_alias_id', 'project_product_id', 'test_env')}

    @staticmethod
    def request_evidence(request_ids):
        return {record.request_id: record for record in SqlExecutionRecord.objects.filter(
            request_id__in=request_ids).only('id', 'request_id', 'database_id', 'source_detail', 'status',
                'source_type', 'source_id', 'source_stage', 'datasource_alias_id', 'project_product_id', 'test_env')}

    @staticmethod
    def visible(user):
        queryset = SqlExecutionRecord.objects.select_related('project_product', 'datasource_alias', 'database')
        if user is None:
            return queryset.none()
        keys = PermissionMenuService.permission_keys_for_user(user)
        if 'system.sql_execution:read' not in keys:
            return queryset.none()
        if PermissionMenuService.is_effective_super_admin(user):
            return queryset
        product_scope = Q(project_product_id__isnull=False)
        if not ProjectProductScopeService.can_view_all_project_data(user):
            product_scope &= Q(project_product_id__in=ProjectProductScopeService.project_product_ids_for_user(user))
        # 全局连接当前没有产品归属；读取需要连接管理菜单权限，不能借用产品可见范围。
        if 'config.datasource:read' in keys:
            product_scope |= Q(project_product_id__isnull=True) & (
                Q(database_id__isnull=False) | Q(source_detail__target_kind='connection')
            )
        return queryset.filter(product_scope)

    @staticmethod
    def factory_records(execution_id):
        from src.apps.data_factory.models import DataFactoryExecutionItem

        # 工厂审计的 source_id 为执行或明细 ID；JSON 执行 ID 再次消除两种 ID 的碰撞。
        # NULL 来源保留历史兼容，不能只按 JSON 在百万级审计表上全量扫描。
        source_ids = [execution_id, *DataFactoryExecutionItem.objects.filter(
            execution_id=execution_id).values_list('id', flat=True)]
        rows = SqlExecutionRecord.objects.filter(
            Q(source_id__in=source_ids) | Q(source_id__isnull=True),
            source_type='data_factory', source_detail__execution_id=execution_id)
        ids = list(rows.order_by('create_time', 'id').values_list('id', flat=True))
        # 只排序轻量 ID，再按主键读取正文，避免 JSON/长文本进入 MySQL 排序缓冲区。
        payloads = SqlExecutionRecord.objects.filter(id__in=ids).order_by().in_bulk()
        return [payloads[pk] for pk in ids if pk in payloads]
