"""变量分类标签的跨协议校验及已授权 QuerySet 查询辅助。"""
from collections import Counter

from src.common.exceptions import MangoServerError, SAVE_VALIDATION_FAILED


def normalize_variable_tags(value):
    if not isinstance(value, list) or any(not isinstance(tag, str) for tag in value):
        raise MangoServerError(SAVE_VALIDATION_FAILED, value=({'tags': ['分类标签必须是字符串列表']},))
    tags = list(dict.fromkeys(tag.strip() for tag in value if tag.strip()))
    if len(tags) > 20 or any(len(tag) > 32 for tag in tags):
        raise MangoServerError(SAVE_VALIDATION_FAILED, value=({'tags': ['最多20个标签，每个最多32个字符']},))
    return tags


def filter_variable_tags(queryset, tag=None, untagged=False):
    if tag and untagged:
        raise MangoServerError(SAVE_VALIDATION_FAILED, value=({'tags': ['分类和未分类不能同时筛选']},))
    if untagged:
        return queryset.filter(tags=[])
    if tag:
        tags = normalize_variable_tags([tag])
        if tags:
            return queryset.filter(tags__contains=tags)
    return queryset


def summarize_variable_tags(queryset):
    counts = Counter()
    total = untagged = 0
    # 只读标签列，不加载变量值；按行流式汇总，避免分页造成分类统计不完整。
    for values in queryset.values_list('tags', flat=True).iterator(chunk_size=1000):
        total += 1
        tags = set(values or [])
        if not tags:
            untagged += 1
        counts.update(tags)
    return {'total': total, 'untagged': untagged,
            'items': [{'name': name, 'count': count} for name, count in sorted(counts.items())]}
