from django.db.models import Q, QuerySet


class TestSuiteDetailQueryService:
    @staticmethod
    def filter_by_case_keyword(queryset: QuerySet, keyword) -> QuerySet:
        normalized_keyword = str(keyword or '').strip()
        if not normalized_keyword:
            return queryset

        condition = Q(case_name__icontains=normalized_keyword)
        if normalized_keyword.isdigit():
            numeric_keyword = int(normalized_keyword)
            condition |= Q(case_id=numeric_keyword) | Q(id=numeric_keyword)
        return queryset.filter(condition)
