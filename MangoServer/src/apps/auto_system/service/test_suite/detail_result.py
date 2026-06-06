import json
from datetime import timedelta
from typing import Any

from django.utils import timezone

from src.apps.auto_system.models import TestSuiteDetailResult, TestSuiteDetails


class TestSuiteDetailResultService:
    DEFAULT_RETENTION_DAYS = 30

    @classmethod
    def save_result(cls, detail: TestSuiteDetails, result_data: Any):
        result_size = cls.calc_result_size(result_data)
        TestSuiteDetailResult.objects.update_or_create(
            test_suite_detail=detail,
            defaults={
                'result_data': result_data,
                'result_size': result_size,
            },
        )

    @classmethod
    def get_result_data(cls, detail: TestSuiteDetails):
        try:
            payload = detail.result_payload
            if payload and payload.result_data is not None:
                return payload.result_data
        except TestSuiteDetailResult.DoesNotExist:
            pass
        return None

    @classmethod
    def result_map(cls, detail_ids: list[int]) -> dict[int, TestSuiteDetailResult]:
        if not detail_ids:
            return {}
        return {
            item.test_suite_detail_id: item
            for item in TestSuiteDetailResult.objects.filter(test_suite_detail_id__in=detail_ids)
        }

    @classmethod
    def attach_children(cls, data_list: list[dict]):
        detail_ids = [item['id'] for item in data_list if item.get('id')]
        payload_map = cls.result_map(detail_ids)
        for item in data_list:
            payload = payload_map.get(item.get('id'))
            result_data = payload.result_data if payload else None
            item.pop('result_data', None)
            item['result_size'] = payload.result_size if payload else cls.calc_result_size(result_data)
            item['has_result_data'] = bool(result_data)
            item['children'] = result_data
            if item.get('children'):
                for child in item.get('children'):
                    child['case_type'] = item['type']
        return data_list

    @classmethod
    def clear_result(cls, detail_ids: list[int]):
        if not detail_ids:
            return 0
        return TestSuiteDetailResult.objects.filter(test_suite_detail_id__in=detail_ids).delete()[0]

    @classmethod
    def clean_expired_results(cls, retention_days: int = DEFAULT_RETENTION_DAYS) -> int:
        cutoff_time = timezone.now() - timedelta(days=retention_days)
        return TestSuiteDetailResult.objects.filter(create_time__lt=cutoff_time).delete()[0]

    @staticmethod
    def calc_result_size(result_data: Any) -> int:
        if result_data is None:
            return 0
        return len(
            json.dumps(
                result_data,
                ensure_ascii=False,
                default=str,
                separators=(',', ':'),
            ).encode('utf-8')
        )
