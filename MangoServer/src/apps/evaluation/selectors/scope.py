"""Project/product boundaries shared by evaluation queries and services."""

from src.apps.evaluation.exceptions import EVALUATION_PROJECT_PRODUCT_ACCESS_DENIED, EvaluationError
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


def ensure_dataset_access(user):
    from src.apps.evaluation.exceptions import EVALUATION_DATASET_ACCESS_DENIED
    if user is not None and (
        PermissionMenuService.is_effective_super_admin(user)
        or "evaluation.dataset:read" in PermissionMenuService.permission_keys_for_user(user)
    ):
        return
    raise EvaluationError(EVALUATION_DATASET_ACCESS_DENIED)


def scope_dataset_queryset(queryset, user):
    from src.apps.evaluation.exceptions import EVALUATION_DATASET_ACCESS_DENIED
    try:
        ensure_dataset_access(user)
    except EvaluationError as error:
        if error.code != EVALUATION_DATASET_ACCESS_DENIED.code:
            raise
        return queryset.none()
    return queryset


def scope_queryset(queryset, user, product_field="project_product_id"):
    if user is None:
        return queryset.none()
    if PermissionMenuService.is_effective_super_admin(user) or ProjectProductScopeService.can_view_all_project_data(user):
        return queryset
    return queryset.filter(**{
        f"{product_field}__in": ProjectProductScopeService.project_product_ids_for_user(user),
    })


def ensure_product_scope(user, project_product_id):
    if user is not None and (
        PermissionMenuService.is_effective_super_admin(user)
        or ProjectProductScopeService.can_view_all_project_data(user)
        or ProjectProductScopeService.has_project_product(user, project_product_id)
    ):
        return
    raise EvaluationError(EVALUATION_PROJECT_PRODUCT_ACCESS_DENIED)
