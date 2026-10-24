from django.db.models import Count, Max, Q
from src.apps.evaluation.enums import EvaluationVersionStatusEnum


def with_current_version(queryset):
    return queryset.annotate(published_version_no=Max(
        "versions__version_no",
        filter=Q(versions__status=EvaluationVersionStatusEnum.PUBLISHED.value),
        default=0,
    ))


def current_version(asset):
    if hasattr(asset, "published_version_no"):
        return asset.published_version_no
    return asset.versions.filter(status=EvaluationVersionStatusEnum.PUBLISHED.value).aggregate(
        value=Max("version_no", default=0),
    )["value"]


def with_item_count(queryset):
    return queryset.annotate(enabled_item_count=Count("items", filter=Q(items__enabled=True)))


def item_count(version):
    if hasattr(version, "enabled_item_count"):
        return version.enabled_item_count
    return version.items.filter(enabled=True).count()
