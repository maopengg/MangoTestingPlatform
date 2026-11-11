from src.apps.auto_ui.enums import UiPublicTypeEnum
from src.common.utils.variable_tags import filter_variable_tags, summarize_variable_tags
from src.common.utils.variable_tag_cache import VariableTagSummaryCache


class UiPublicTagSelector:
    @staticmethod
    def filter(queryset, tag=None, untagged=False):
        return filter_variable_tags(queryset.filter(type__in=UiPublicTypeEnum.get_key_list()), tag, untagged)

    @staticmethod
    def summarize(queryset):
        scoped = queryset.filter(type__in=UiPublicTypeEnum.get_key_list())
        return VariableTagSummaryCache.get(scoped, lambda: summarize_variable_tags(scoped))
