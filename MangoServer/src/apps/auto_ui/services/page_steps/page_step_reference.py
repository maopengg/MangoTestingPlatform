from django.db.models import Count

from src.apps.auto_ui.models import UiCase, UiCaseStepsDetailed
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class PageStepReferenceService:
    """查询页面步骤被 UI 用例引用的情况。"""

    @staticmethod
    def _filter_case_scope(request, queryset):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if (
                user is None or
                PermissionMenuService.is_effective_super_admin(user) or
                ProjectProductScopeService.can_view_all_project_data(user)
        ):
            return queryset
        allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        return queryset.filter(project_product_id__in=allowed_ids) if allowed_ids else queryset.none()

    @classmethod
    def list_cases(cls, request, page_step_id: int) -> list[dict]:
        reference_counts = {
            item['case_id']: item['reference_count']
            for item in UiCaseStepsDetailed.objects.filter(page_step_id=page_step_id)
            .values('case_id')
            .annotate(reference_count=Count('id'))
        }
        if not reference_counts:
            return []

        queryset = UiCase.objects.filter(id__in=reference_counts).select_related(
            'project_product',
            'project_product__project',
            'module',
            'case_people',
        ).order_by('-update_time', '-id')
        queryset = cls._filter_case_scope(request, queryset)

        result = []
        for case in queryset:
            project_product = case.project_product
            module = case.module
            result.append({
                'id': case.id,
                'name': case.name,
                'status': case.status,
                'update_time': case.update_time.strftime('%Y-%m-%d %H:%M:%S'),
                'case_people': {
                    'id': case.case_people_id,
                    'name': case.case_people.name,
                    'username': case.case_people.username,
                },
                'project_product': {
                    'id': project_product.id,
                    'name': project_product.name,
                    'project': {
                        'id': project_product.project_id,
                        'name': project_product.project.name,
                    },
                },
                'module': {
                    'id': module.id,
                    'name': module.name,
                    'superior_module_1': module.superior_module_1,
                    'superior_module_2': module.superior_module_2,
                },
            })
        return result
