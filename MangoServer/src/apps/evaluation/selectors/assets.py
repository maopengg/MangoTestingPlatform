"""Scoped evaluation asset access shared with protocol adapters."""

from src.apps.evaluation.exceptions import EVALUATION_OBJECT_NOT_FOUND, EvaluationError
from src.apps.evaluation.selectors.querysets import EvaluationQuerySelector
from src.apps.evaluation.selectors.scope import scope_dataset_queryset
from django.db.models import Q


def filter_dataset_task_types(queryset, task_types):
    if not task_types:
        return queryset
    condition = Q()
    for task_type in task_types:
        condition |= Q(task_type__contains=[task_type])
    return queryset.filter(condition)


def datasets(user, name=None):
    queryset = scope_dataset_queryset(EvaluationQuerySelector.datasets(), user)
    if name:
        queryset = queryset.filter(name__icontains=name)
    return queryset.order_by("-id")


def get_dataset(dataset_id, user):
    record = datasets(user).filter(pk=dataset_id).first()
    if record is None:
        raise EvaluationError(EVALUATION_OBJECT_NOT_FOUND)
    return record


def versions(dataset_id, user):
    get_dataset(dataset_id, user)
    return EvaluationQuerySelector.dataset_versions().filter(dataset_id=dataset_id).order_by("-version_no")


def version_items(version):
    return EvaluationQuerySelector.items().filter(dataset_version_id=version.id).order_by("id")


def execution_items(execution):
    return EvaluationQuerySelector.item_results().filter(execution_id=execution.id).order_by("id")


def page(queryset, presenter, page=1, page_size=20):
    page, page_size = max(1, page), min(100, max(1, page_size))
    return {"items": [presenter(item) for item in queryset[(page-1)*page_size:page*page_size]],
            "count": queryset.count(), "page": page, "page_size": page_size}
