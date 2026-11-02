from django.db.models import Q

from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


class ExecutionResultAccessSelector:
    @staticmethod
    def visible_queryset(queryset, user, target_access):
        if user is None:
            return queryset.none()
        if PermissionMenuService.is_effective_super_admin(user):
            return queryset
        permissions = PermissionMenuService.permission_keys_for_user(user)
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
