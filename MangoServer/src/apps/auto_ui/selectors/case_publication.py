from django.db.models import BooleanField, Case, Value, When

from src.apps.test_center.selectors.querysets import TestCenterQuerySelector


class UiCasePublicationSelector:
    @staticmethod
    def status(case):
        return case.publication_status

    @staticmethod
    def filter_status(queryset, status):
        if not status:
            return queryset
        return queryset.filter(publication_status=status)

    @staticmethod
    def with_owner(queryset, user_id):
        owned = TestCenterQuerySelector.owned_project_product_ids(user_id)
        return queryset.annotate(is_product_owner=Case(
            When(project_product_id__in=owned, then=Value(True)),
            default=Value(False), output_field=BooleanField(),
        ))
