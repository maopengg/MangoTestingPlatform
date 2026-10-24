# -*- coding: utf-8 -*-
import re
import time

from src.tools.log_collector import log


class TaskPullFailureReporter:
    """Rate-limit expected HTTP pull failures while WebSocket fallback remains available."""

    LOG_INTERVAL_SECONDS = 60
    _failures: dict[str, dict] = {}

    @classmethod
    def report(cls, task_type: str, error: Exception):
        now = time.time()
        summary = cls._summary(error)
        previous = cls._failures.get(task_type)
        cls._failures[task_type] = {
            'summary': summary,
            'last_seen': now,
            'last_logged': previous.get('last_logged', 0) if previous else 0,
        }
        if previous and previous.get('summary') == summary:
            if now - previous.get('last_logged', 0) < cls.LOG_INTERVAL_SECONDS:
                return
        cls._failures[task_type]['last_logged'] = now
        log.warning(f'HTTP拉取{task_type}任务失败（{summary}），已回退WebSocket，稍后自动重试')

    @classmethod
    def recovered(cls, task_type: str):
        if cls._failures.pop(task_type, None):
            log.info(f'HTTP拉取{task_type}任务已恢复')

    @staticmethod
    def _summary(error: Exception) -> str:
        status_code = getattr(error, 'status_code', None)
        if status_code:
            return f'HTTP {status_code}'
        value = re.sub(r'<[^>]+>', ' ', str(error or ''))
        value = ' '.join(value.split())
        return value[:120] or type(error).__name__
