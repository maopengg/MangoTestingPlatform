from datetime import datetime

from django.conf import settings
from django.utils import timezone


def normalize_perf_datetime(value: datetime) -> datetime:
    """将执行器上报时间转换为当前 Django 数据库配置可接受的形式。"""
    if settings.USE_TZ:
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value
    if timezone.is_aware(value):
        return timezone.make_naive(value, timezone.get_current_timezone())
    return value
