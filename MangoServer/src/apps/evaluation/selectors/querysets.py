"""Scoped facts and eager loading for data, Cases and nested execution results."""

from django.db.models import Count, OuterRef, Subquery, JSONField
from src.apps.evaluation.models import EvaluationDataset, EvaluationDatasetVersion, EvaluationDatasetItem, EvaluationCase, EvaluationCaseExecution, EvaluationItemResult
from src.apps.evaluation.selectors.scope import scope_queryset
from src.apps.evaluation.selectors.version import with_current_version, with_item_count
from src.apps.test_center.services.project.product_module import ProductModuleService


class EvaluationQuerySelector:
    @staticmethod
    def datasets():
        return with_current_version(EvaluationDataset.objects.all())

    @staticmethod
    def dataset_versions():
        return with_item_count(EvaluationDatasetVersion.objects.select_related("dataset"))

    @staticmethod
    def items():
        return EvaluationDatasetItem.objects.select_related("dataset_version__dataset")

    @staticmethod
    def cases(user, test_env=None):
        latest = EvaluationCaseExecution.objects.filter(case_id=OuterRef("pk"))
        if test_env:
            latest = latest.filter(test_env=test_env)
        latest = latest.order_by("-id")
        queryset = ProductModuleService.with_full_paths(EvaluationCase.objects.all(), "module").select_related(
            "project_product", "module", "owner", "dataset_version__dataset",
        ).annotate(latest_execution_id=Subquery(latest.values("id")[:1]),
                   latest_status=Subquery(latest.values("status")[:1]),
                   latest_finished_at=Subquery(latest.values("finished_at")[:1]),
                   latest_summary=Subquery(latest.values("summary")[:1], output_field=JSONField()))
        return scope_queryset(queryset, user)

    @staticmethod
    def executions(user, case_id):
        queryset = EvaluationCaseExecution.objects.filter(case_id=case_id).select_related(
            "case", "dataset_version__dataset", "created_by",
        ).annotate(item_total=Count("item_results"))
        return scope_queryset(queryset, user, "case__project_product_id")

    @staticmethod
    def item_results():
        return EvaluationItemResult.objects.select_related("execution__case").prefetch_related("grade_results")
