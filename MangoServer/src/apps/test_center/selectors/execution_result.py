from django.db.models import Q

from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class ExecutionResultAccessSelector:
    @staticmethod
    def api_resource_evidence_result(trace):
        from src.apps.test_center.models import ExecutionResult
        return ExecutionResult.objects.filter(trace_id=trace.trace_id, target_type='api_case',
            target_id=trace.case_id, test_env=trace.test_env, trigger_user_id=trace.user_id,
        ).order_by('-id').first()

    @staticmethod
    def exact_api_trace_result(trace):
        from src.apps.test_center.models import ExecutionResult
        return ExecutionResult.objects.filter(trace_id=trace.trace_id, target_type='api_case',
            target_id=trace.case_id, test_env=trace.test_env, trigger_user_id=trace.user_id,
            source_type='mcp').order_by('-id').first()

    @staticmethod
    def visible_queryset(queryset, user, target_access):
        if user is None:
            return queryset.none()
        if PermissionMenuService.is_effective_super_admin(user):
            return queryset
        permissions = PermissionMenuService.permission_keys_for_user(user)
        # 执行结果管理列表本就覆盖全部记录，详情保持相同范围，包括已删除资产的历史结果。
        if 'system.execution_result:read' in permissions:
            return queryset
        all_products = ProjectProductScopeService.can_view_all_project_data(user)
        product_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        access = Q(pk__in=[])
        if 'report:read' in permissions:
            report_access = Q(test_suite_detail__isnull=False)
            if not all_products:
                report_access &= Q(test_suite_detail__project_product_id__in=product_ids)
            access |= report_access
        for target_type, (required_keys, assets, product_field) in target_access.items():
            if not permissions.intersection(required_keys):
                continue
            if not all_products:
                assets = assets.filter(**{f'{product_field}__in': product_ids})
            access |= Q(target_type=target_type, target_id__in=assets.values('id'))
        return queryset.filter(access)
