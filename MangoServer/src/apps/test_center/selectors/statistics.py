from django.db.models import Case, F, JSONField, Value, When

from src.apps.test_center.enums import TestCaseTypeEnum


class ReportStatisticsSelector:
    @staticmethod
    def rows(queryset, fields, by_scenario):
        """仅旧 Case 口径且缺少场景计数快照的记录需要读取轻量 children；不读取执行结果文件。"""
        if not by_scenario:
            return queryset.values(*fields).iterator(chunk_size=2000)
        return queryset.annotate(
            statistics_api_mode=F('summary_data__meta__api_count_by_scenario'),
            statistics_scene_count=F('summary_data__meta__api_scene_count'),
            statistics_scene_counter=F('summary_data__meta__api_scene_counter'),
            statistics_legacy_children=Case(
                When(type=TestCaseTypeEnum.API.value, summary_data__meta__api_count_by_scenario=False,
                     summary_data__meta__api_scene_counter__isnull=True,
                     then=F('summary_data__children')),
                default=Value(None, output_field=JSONField()), output_field=JSONField(),
            ),
        ).values(*fields, 'statistics_api_mode', 'statistics_scene_count',
                 'statistics_scene_counter', 'statistics_legacy_children').iterator(chunk_size=2000)
