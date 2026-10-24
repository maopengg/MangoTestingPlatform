from django.db.models import BooleanField, Case, Q, Value, When

from src.apps.test_center.selectors.querysets import TestCenterQuerySelector


class PytestCasePublicationSelector:
    @staticmethod
    def status(case):
        return case.publication_status

    @staticmethod
    def filter_status(queryset, statuses):
        if not statuses:
            return queryset
        return queryset.filter(publication_status__in=statuses)

    @staticmethod
    def with_owner(queryset, user_id):
        owned = TestCenterQuerySelector.owned_project_product_ids(user_id)
        return queryset.annotate(is_product_owner=Case(
            When(project_product__project_product_id__in=owned, then=Value(True)),
            default=Value(False), output_field=BooleanField(),
        ))

    @classmethod
    def filter_search(cls, queryset, params):
        for field in ('id', 'module', 'level', 'scenario_layer', 'scenario_type', 'status',
                      'file_status', 'source_status', 'asset_status', 'case_people', 'update_user',
                      'project_product', 'project_product__project_product_id'):
            raw = params.get(f'{field}__in') or params.get(field)
            if raw in (None, ''):
                continue
            try:
                values = [int(value.strip()) for value in str(raw).split(',') if value.strip()]
            except (ValueError, TypeError):
                return queryset.none()
            queryset = queryset.filter(**{f'{field}__in': values})
        for field, lookup in (('name', 'name__icontains'), ('file_path', 'file_path__icontains'),
                              ('file_path__startswith', 'file_path__startswith'), ('file_path__exact', 'file_path')):
            value = params.get(field)
            if value:
                queryset = queryset.filter(**{lookup: value})
        raw_status = params.get('publication_status__in') or params.get('publication_status')
        queryset = cls.filter_status(queryset, str(raw_status).split(',') if raw_status else [])
        tags = params.getlist('scenario_tags[]') + params.getlist('scenario_tags')
        if tags:
            condition = Q()
            for tag in tags:
                condition |= Q(scenario_tags__contains=[tag])
            queryset = queryset.filter(condition)
        return queryset
