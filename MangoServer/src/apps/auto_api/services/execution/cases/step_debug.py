import copy
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from mangotools.enums import StatusEnum

from src.apps.auto_api.exceptions import (
    API_CASE_STEP_NOT_FOUND,
    API_CACHE_STEP_NOT_FOUND,
    API_TEST_ENVIRONMENT_USER_INVALID,
    AutoApiError,
    API_PARAMETERIZED_STEP_DEBUG_UNSUPPORTED,
)
from src.apps.auto_api.models import ApiCaseDetailed, ApiCaseDetailedParameter
from src.apps.auto_api.schemas.execution import ApiStepExecutionContext
from src.apps.test_center.services.results.execution_result import ExecutionResultService


@dataclass
class ApiCaseStepSnapshot:
    context_id: str
    snapshot_id: str
    parent_snapshot_id: str | None
    cache_data: dict
    data_factory_cache_data: dict
    executed_at: str
    product_cache_keys: list[str] | None = None


@dataclass
class ApiCaseStepDebugState:
    step: ApiCaseDetailed
    context_id: str
    snapshot_id: str
    parent_snapshot_id: str | None
    cache_data: dict
    data_factory_cache_data: dict
    restored_from_step_id: int | None
    restored_from_step_name: str | None
    context_source: str
    run_case_front: bool

    def execution_context(self, *, test_env: int, user_id: int | None, trace_id: str | None) -> dict:
        return ApiStepExecutionContext(
            context_id=self.context_id,
            snapshot_id=self.snapshot_id,
            parent_snapshot_id=self.parent_snapshot_id,
            case_id=self.step.case_id,
            case_detailed_id=self.step.id,
            case_sort=self.step.case_sort,
            test_env=test_env,
            user_id=user_id,
            trace_id=trace_id,
            executed_at=datetime.now().astimezone().isoformat(),
        ).model_dump()


class ApiCaseStepDebugContextService:
    CONTEXT_MAX_AGE = timedelta(hours=2)
    CONTEXT_ID_PATTERN = re.compile(r'^[A-Za-z0-9:_-]{1,96}$')

    @classmethod
    def prepare(
            cls,
            *,
            case_id: int,
            case_detailed_id: int,
            test_env: int,
            user_id: int | None,
            context_id: str | None = None,
    ) -> ApiCaseStepDebugState:
        steps = list(
            ApiCaseDetailed.objects
            .select_related('case', 'api_info')
            .filter(case_id=case_id)
            .order_by('case_sort', 'id')
        )
        step_index = next((index for index, step in enumerate(steps) if step.id == case_detailed_id), None)
        if step_index is None:
            raise AutoApiError(API_CASE_STEP_NOT_FOUND)
        step = steps[step_index]
        if step.case.parametrize and isinstance(step.case.parametrize, list):
            raise AutoApiError(API_PARAMETERIZED_STEP_DEBUG_UNSUPPORTED)

        normalized_context_id = cls.normalize_context_id(context_id)
        if step_index == 0:
            return ApiCaseStepDebugState(
                step=step,
                context_id=normalized_context_id or uuid4().hex,
                snapshot_id=uuid4().hex,
                parent_snapshot_id=None,
                cache_data={},
                data_factory_cache_data={},
                restored_from_step_id=None,
                restored_from_step_name=None,
                context_source='new',
                run_case_front=True,
            )

        previous_steps = steps[:step_index]
        if normalized_context_id is None:
            normalized_context_id = cls.latest_context_id(
                previous_steps[-1],
                test_env=test_env,
                user_id=user_id,
            )
        if normalized_context_id is None:
            raise AutoApiError(API_CACHE_STEP_NOT_FOUND)

        snapshots = cls.validate_snapshot_chain(
            previous_steps,
            context_id=normalized_context_id,
            test_env=test_env,
            user_id=user_id,
        )
        previous_step = previous_steps[-1]
        previous_snapshot = snapshots[-1]
        cache_data = copy.deepcopy(previous_snapshot.cache_data)
        crosses_products = any(item.api_info.project_product_id != step.case.project_product_id
                               for item in [*previous_steps, step])
        if crosses_products and previous_snapshot.product_cache_keys is not None:
            for key in previous_snapshot.product_cache_keys:
                cache_data.pop(key, None)
        elif crosses_products:
            # 旧快照没有产品配置的键归属，不能把旧凭据带入另一产品。
            raise AutoApiError(API_TEST_ENVIRONMENT_USER_INVALID)
        return ApiCaseStepDebugState(
            step=step,
            context_id=normalized_context_id,
            snapshot_id=uuid4().hex,
            parent_snapshot_id=previous_snapshot.snapshot_id,
            cache_data=cache_data,
            data_factory_cache_data=copy.deepcopy(previous_snapshot.data_factory_cache_data),
            restored_from_step_id=previous_step.id,
            restored_from_step_name=previous_step.api_info.name,
            context_source='previous_step',
            run_case_front=False,
        )

    @classmethod
    def validate_snapshot_chain(
            cls,
            steps: list[ApiCaseDetailed],
            *,
            context_id: str,
            test_env: int,
            user_id: int | None,
    ) -> list[ApiCaseStepSnapshot]:
        snapshots = []
        expected_parent_snapshot_id = None
        for step in steps:
            snapshot = cls.step_snapshot(
                step,
                context_id=context_id,
                test_env=test_env,
                user_id=user_id,
            )
            if snapshot.parent_snapshot_id != expected_parent_snapshot_id:
                raise AutoApiError(API_TEST_ENVIRONMENT_USER_INVALID)
            snapshots.append(snapshot)
            expected_parent_snapshot_id = snapshot.snapshot_id
        return snapshots

    @classmethod
    def step_snapshot(
            cls,
            step: ApiCaseDetailed,
            *,
            context_id: str,
            test_env: int,
            user_id: int | None,
    ) -> ApiCaseStepSnapshot:
        parameters = list(
            ApiCaseDetailedParameter.objects
            .filter(case_detailed_id=step.id)
            .order_by('update_time', 'id')
        )
        if not parameters or step.status != StatusEnum.SUCCESS.value:
            raise AutoApiError(API_CACHE_STEP_NOT_FOUND)

        expected_snapshot_id = None
        expected_parent_snapshot_id = None
        latest_result = None
        latest_context = None
        for parameter in parameters:
            result_data = ExecutionResultService.latest_api_case_parameter_result(
                case_id=step.case_id,
                parameter_id=parameter.id,
                test_env=test_env,
            )
            execution_context = result_data.get('execution_context')
            if (
                    parameter.status != StatusEnum.SUCCESS.value
                    or result_data.get('status') != StatusEnum.SUCCESS.value
                    or not isinstance(execution_context, dict)
            ):
                raise AutoApiError(API_CACHE_STEP_NOT_FOUND)
            if (
                    execution_context.get('context_id') != context_id
                    or str(execution_context.get('test_env')) != str(test_env)
                    or str(execution_context.get('user_id')) != str(user_id)
                    or execution_context.get('case_detailed_id') != step.id
            ):
                raise AutoApiError(API_TEST_ENVIRONMENT_USER_INVALID)
            snapshot_id = execution_context.get('snapshot_id')
            parent_snapshot_id = execution_context.get('parent_snapshot_id')
            if not snapshot_id:
                raise AutoApiError(API_TEST_ENVIRONMENT_USER_INVALID)
            if expected_snapshot_id is None:
                expected_snapshot_id = snapshot_id
                expected_parent_snapshot_id = parent_snapshot_id
            elif snapshot_id != expected_snapshot_id or parent_snapshot_id != expected_parent_snapshot_id:
                raise AutoApiError(API_TEST_ENVIRONMENT_USER_INVALID)
            latest_result = result_data
            latest_context = execution_context

        if latest_result is None or latest_context is None or cls.is_expired(latest_context.get('executed_at')):
            raise AutoApiError(API_TEST_ENVIRONMENT_USER_INVALID)
        cache_data = latest_result.get('cache_data')
        data_factory_cache_data = latest_result.get('data_factory_cache_data')
        if not isinstance(cache_data, dict) or not isinstance(data_factory_cache_data, dict):
            raise AutoApiError(API_TEST_ENVIRONMENT_USER_INVALID)
        return ApiCaseStepSnapshot(
            context_id=context_id,
            snapshot_id=expected_snapshot_id,
            parent_snapshot_id=expected_parent_snapshot_id,
            cache_data=cache_data,
            data_factory_cache_data=data_factory_cache_data,
            executed_at=latest_context.get('executed_at'),
            product_cache_keys=latest_context.get('product_cache_keys'),
        )

    @classmethod
    def latest_context_id(
            cls,
            step: ApiCaseDetailed,
            *,
            test_env: int,
            user_id: int | None,
    ) -> str | None:
        parameters = (
            ApiCaseDetailedParameter.objects
            .filter(case_detailed_id=step.id, status=StatusEnum.SUCCESS.value)
            .order_by('-update_time', '-id')
        )
        for parameter in parameters:
            result_data = ExecutionResultService.latest_api_case_parameter_result(
                case_id=step.case_id,
                parameter_id=parameter.id,
                test_env=test_env,
            )
            execution_context = result_data.get('execution_context')
            if not isinstance(execution_context, dict):
                continue
            if (
                    str(execution_context.get('test_env')) == str(test_env)
                    and str(execution_context.get('user_id')) == str(user_id)
                    and not cls.is_expired(execution_context.get('executed_at'))
            ):
                return cls.normalize_context_id(execution_context.get('context_id'))
        return None

    @classmethod
    def normalize_context_id(cls, context_id: str | None) -> str | None:
        if context_id is None or str(context_id).strip() == '':
            return None
        value = str(context_id).strip()
        if not cls.CONTEXT_ID_PATTERN.fullmatch(value):
            raise AutoApiError(API_TEST_ENVIRONMENT_USER_INVALID)
        return value

    @classmethod
    def is_expired(cls, executed_at: str | None) -> bool:
        if not executed_at:
            return True
        value = parse_datetime(str(executed_at))
        if value is None:
            return True
        current_timezone = timezone.get_current_timezone()
        if timezone.is_naive(value):
            value = timezone.make_aware(value, current_timezone)
        now = datetime.now().astimezone()
        return now - value > cls.CONTEXT_MAX_AGE

    @staticmethod
    def restore_cache(test_data, state: ApiCaseStepDebugState):
        for key, value in state.cache_data.items():
            test_data.set_cache(key, value)
        for key, value in state.data_factory_cache_data.items():
            test_data.set_data_factory_cache(key, value)
