from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.common.utils.variable_tags import filter_variable_tags, summarize_variable_tags
from src.common.utils.variable_tag_cache import VariableTagSummaryCache


class ApiPublicTagSelector:
    @staticmethod
    def filter(queryset, tag=None, untagged=False):
        return filter_variable_tags(queryset.filter(type__in=ApiPublicTypeEnum.get_key_list()), tag, untagged)

    @staticmethod
    def summarize(queryset):
        scoped = queryset.filter(type__in=ApiPublicTypeEnum.get_key_list())
        return VariableTagSummaryCache.get(scoped, lambda: summarize_variable_tags(scoped))
