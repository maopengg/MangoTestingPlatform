from django.db.models import Q

from src.apps.data_factory.models import SqlExecutionRecord
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class ExecutionAuditSelector:
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
            product_scope |= Q(project_product_id__isnull=True, database_id__isnull=False)
        return queryset.filter(product_scope)

    @staticmethod
    def factory_records(execution_id):
        return SqlExecutionRecord.objects.filter(source_type='data_factory',
                                                 source_detail__execution_id=execution_id).order_by('create_time', 'id')
