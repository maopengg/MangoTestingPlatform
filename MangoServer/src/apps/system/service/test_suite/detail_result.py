import json
from datetime import timedelta
from typing import Any

from django.utils import timezone

from src.apps.auto_api.models import ApiCaseDetailedParameter
from src.apps.system.models import TestSuiteDetailResult, TestSuiteDetails
from src.common.enums.api_enum import MethodEnum
from src.common.enums.tools_enum import TaskEnum, TestCaseTypeEnum
from src.common.models.api_model import ApiCaseStepsResultModel, RequestModel


class TestSuiteDetailResultService:
    DEFAULT_RETENTION_DAYS = 30
    SKIP_MESSAGE = '该用例前置步骤失败，未被执行'

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
            for item in TestSuiteDetailResult.objects.filter(test_suite_detail_id__in=detail_ids).order_by()
        }

    @classmethod
    def attach_children(cls, data_list: list[dict]):
        detail_ids = [item['id'] for item in data_list if item.get('id')]
        payload_map = cls.result_map(detail_ids)
        for item in data_list:
            payload = payload_map.get(item.get('id'))
            result_data = payload.result_data if payload else None
            result_data = cls.ensure_api_warning_results(item, result_data, payload)
            item.pop('result_data', None)
            item['result_size'] = payload.result_size if payload else cls.calc_result_size(result_data)
            item['has_result_data'] = bool(result_data)
            item['children'] = result_data
            if item.get('children'):
                for child in item.get('children'):
                    child['case_type'] = item['type']
        return data_list

    @classmethod
    def ensure_api_warning_results(
            cls,
            detail: dict,
            result_data: Any,
            payload: TestSuiteDetailResult | None,
    ):
        if detail.get('type') != TestCaseTypeEnum.API.value:
            return result_data
        if (detail.get('warning') or 0) <= 0:
            return result_data
        if not isinstance(result_data, list):
            result_data = []
        case_sum = detail.get('case_sum') or 0
        if len(result_data) >= case_sum:
            return result_data
        fixed_result_data = cls.build_missing_api_warning_results(detail, result_data)
        if len(fixed_result_data) == len(result_data):
            return result_data
        test_suite_detail_id = detail.get('id')
        if not test_suite_detail_id:
            return fixed_result_data
        result_size = cls.calc_result_size(fixed_result_data)
        if payload:
            payload.result_data = fixed_result_data
            payload.result_size = result_size
            payload.save(update_fields=['result_data', 'result_size', 'update_time'])
        else:
            TestSuiteDetailResult.objects.create(
                test_suite_detail_id=test_suite_detail_id,
                result_data=fixed_result_data,
                result_size=result_size,
            )
        return fixed_result_data

    @classmethod
    def build_missing_api_warning_results(cls, detail: dict, result_data: list[dict]):
        case_id = detail.get('case_id')
        if not case_id:
            return result_data
        parameters = ApiCaseDetailedParameter.objects.filter(
            case_detailed__case_id=case_id,
        ).select_related(
            'case_detailed',
            'case_detailed__api_info',
        ).order_by(
            'case_detailed__case_sort',
            'case_detailed_id',
            'id',
        )
        executed_count_map = cls.api_result_count_by_case_detailed(result_data)
        fixed_result_data = list(result_data)
        for parameter in parameters:
            case_detailed = parameter.case_detailed
            executed_count = executed_count_map.get(case_detailed.id, 0)
            if executed_count > 0:
                executed_count_map[case_detailed.id] = executed_count - 1
                continue
            fixed_result_data.append(cls.build_api_warning_result(parameter))
        return fixed_result_data

    @staticmethod
    def api_result_count_by_case_detailed(result_data: list[dict]) -> dict[int, int]:
        count_map = {}
        for item in result_data:
            try:
                case_detailed_id = int(item.get('id'))
            except (TypeError, ValueError):
                continue
            count_map[case_detailed_id] = count_map.get(case_detailed_id, 0) + 1
        return count_map

    @classmethod
    def build_api_warning_result(cls, parameter: ApiCaseDetailedParameter) -> dict:
        case_detailed = parameter.case_detailed
        api_info = case_detailed.api_info
        request_model = RequestModel(
            method=MethodEnum(api_info.method).name,
            url=api_info.url,
            headers={},
            params=parameter.params,
            protocol_type=api_info.protocol_type,
            body_type=api_info.body_type,
            body_config=parameter.body_config,
            sse_config=parameter.sse_config,
            posterior_file=api_info.posterior_file,
        )
        result_model = ApiCaseStepsResultModel(
            id=case_detailed.id,
            api_info_id=api_info.id,
            api_info_name=api_info.name,
            name=parameter.name or api_info.name or f'场景ID:{case_detailed.id}',
            status=TaskEnum.WARNING.value,
            request=request_model,
            cache_data={},
            test_time=timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            error_message=cls.SKIP_MESSAGE,
        )
        return result_model.model_dump()

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
