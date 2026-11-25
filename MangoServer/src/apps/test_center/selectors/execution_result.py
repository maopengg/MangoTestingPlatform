from django.db.models import Q

from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class ExecutionResultAccessSelector:
    @staticmethod
    def search_targets(product_ids=None):
        from src.apps.auto_api.selectors.querysets import ApiQuerySelector
        from src.apps.auto_ui.selectors.querysets import UiQuerySelector
        from src.apps.auto_pytest.selectors.querysets import PytestQuerySelector

        targets = {
            'api_case': ApiQuerySelector.api_case(),
            'api_info': ApiQuerySelector.api_info(),
            'ui_case': UiQuerySelector.ui_case(),
            'ui_page_step': UiQuerySelector.page_steps(),
            'pytest_case': PytestQuerySelector.pytest_case(),
        }
        if product_ids is not None:
            targets = {kind: rows.filter(**{
                'project_product__project_product_id__in' if kind == 'pytest_case' else 'project_product_id__in': product_ids,
            }) for kind, rows in targets.items()}
        return targets

    @classmethod
    def search_batch(cls, query, start, end, cursor=None, limit=25, *, product_ids=None):
        from src.apps.test_center.models import ExecutionResult

        rows = ExecutionResult.objects.filter(create_time__gte=start, create_time__lt=end)
        scope = [query.project_product_id] if query.project_product_id is not None else product_ids
        if scope is not None:
            product = Q(test_suite_detail__project_product_id__in=scope)
            for kind, assets in cls.search_targets(scope).items():
                product |= Q(target_type=kind, target_id__in=assets.values('id'))
            rows = rows.filter(product)
        if query.test_env is not None:
            rows = rows.filter(test_env=query.test_env)
        rows = rows.select_related('trigger_user', 'test_suite_detail')
        if cursor:
            rows = rows.filter(Q(create_time__lt=cursor[0]) | Q(create_time=cursor[0], id__lt=cursor[1]))
        return list(rows.only('id', 'create_time', 'target_type', 'target_id', 'source_type', 'test_suite_id',
            'test_suite_detail_id', 'test_suite_detail__case_name', 'trigger_user_id', 'trigger_user__name',
            'result_size', 'result_object_key', 'result_cleaned').order_by('-create_time', '-id')[:limit])

    @staticmethod
    def inline_search_payload(record_id, max_length):
        from django.db.models import TextField
        from django.db.models.functions import Cast, Substr
        from src.apps.test_center.models import ExecutionResult
        return ExecutionResult.objects.filter(id=record_id).annotate(
            search_payload=Substr(Cast('result_data', TextField()), 1, max_length + 1),
        ).values_list('search_payload', flat=True).first()

    @classmethod
    def search_names(cls, product_id, hits, *, product_ids=None):
        names = {}
        for kind, assets in cls.search_targets([product_id] if product_id is not None else product_ids).items():
            ids = {hit.target_id for hit in hits if hit.target_type == kind and hit.target_id}
            if ids:
                names.update({(kind, row['id']): row['name'] for row in assets.filter(id__in=ids).values('id', 'name')})
        return names

    @staticmethod
    def api_trace_results():
        from src.apps.test_center.models import ExecutionResult
        return ExecutionResult.objects.filter(target_type='api_case')

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
