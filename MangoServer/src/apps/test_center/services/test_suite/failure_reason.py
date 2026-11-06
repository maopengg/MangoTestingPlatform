import re
from collections import Counter
from typing import Any, Iterable

from mangotools.enums import TaskEnum

from src.apps.test_center.models import TestSuiteDetails
from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService


class TestSuiteFailureReasonService:
    DEFAULT_REASON = '未返回失败原因'
    DEFAULT_LIMIT = 5
    FAILURE_STATUSES = {TaskEnum.FAIL.value, 'failed', 'broken'}

    @classmethod
    def top_failure_reasons(cls, test_suite_id, limit: int = DEFAULT_LIMIT) -> dict:
        counter = Counter()
        details = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id).only(
            'id',
            'status',
            'error_message',
            'summary_data',
        )
        for detail in details.iterator(chunk_size=200):
            reasons = list(cls.detail_failure_reasons(detail))
            if reasons:
                counter.update(reasons)

        max_count = max(counter.values(), default=1)
        items = [
            {
                'message': message,
                'count': count,
                'percent': round(count / max_count * 100),
            }
            for message, count in counter.most_common(max(limit, 1))
        ]
        return {
            'items': items,
            'category_count': len(counter),
            'failure_count': sum(counter.values()),
        }

    @classmethod
    def detail_failure_reasons(cls, detail: TestSuiteDetails) -> Iterable[str]:
        from src.apps.test_center.services.test_suite.infrastructure import TestSuiteInfrastructureService
        if TestSuiteInfrastructureService.is_blocked(detail.summary_data):
            return
        children, _ = TestSuiteExecutionResultService.unpack_summary_data(detail.summary_data)
        child_reasons = [
            cls.failure_message(item)
            for item in cls.result_items(children)
            if cls.is_failure_status(item.get('status'))
        ]
        if child_reasons:
            yield from child_reasons
            return
        if cls.is_failure_status(detail.status):
            yield cls.normalize_message(detail.error_message)

    @classmethod
    def result_items(cls, value: Any) -> Iterable[dict]:
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield item
        elif isinstance(value, dict) and 'status' in value:
            yield value

    @classmethod
    def failure_message(cls, item: dict) -> str:
        status_details = item.get('statusDetails')
        status_message = status_details.get('message') if isinstance(status_details, dict) else None
        response = item.get('response')
        response_message = response.get('error') if isinstance(response, dict) else None
        return cls.normalize_message(
            item.get('error_message')
            or status_message
            or response_message
            or item.get('message')
        )

    @classmethod
    def normalize_message(cls, value: Any) -> str:
        message = re.sub(r'\s+', ' ', str(value or '')).strip()
        return message or cls.DEFAULT_REASON

    @classmethod
    def is_failure_status(cls, value: Any) -> bool:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            normalized = str(value or '').lower()
        return normalized in cls.FAILURE_STATUSES
