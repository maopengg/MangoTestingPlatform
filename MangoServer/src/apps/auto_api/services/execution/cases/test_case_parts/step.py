# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
from datetime import datetime

from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum
from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.enums import MethodEnum
from src.apps.auto_api.exceptions import (
    AutoApiError,
    API_CASE_EMPTY,
)
from src.apps.auto_api.exceptions import TestSuiteStopped
from src.apps.auto_api.models import ApiCaseDetailed, ApiCaseDetailedParameter
from src.apps.auto_api.schemas.recovery import is_recovery_step
from src.apps.auto_api.schemas.case_schema import (
    unpack_scenario_body_config,
)
from src.apps.auto_api.schemas.execution import (
    ApiExecutionRequest,
    ApiCaseStepResult,
)
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.common.exceptions import MangoServerError


class ApiTestCaseStepMixin:
    @staticmethod
    def normalize_parametrize(parametrize: dict | list) -> dict:
        if isinstance(parametrize, dict):
            return parametrize
        return {'parametrize': parametrize}

    def get_case_detailed_queryset(self, case_id: int, case_sort: int | None):
        if self.revision_aggregate is not None:
            steps = self.revision_aggregate.steps
            if case_sort is not None and str(case_sort) != '':
                steps = tuple(step for step in steps if step.case_sort <= int(case_sort))
            return steps
        if case_sort is not None and str(case_sort) != '':
            return ApiCaseDetailed \
                .objects \
                .filter(case=case_id, case_sort__lte=case_sort) \
                .order_by('case_sort')
        return ApiCaseDetailed \
            .objects \
            .filter(case=case_id) \
            .order_by('case_sort')

    def get_parameters_for_step(self, case_detailed: ApiCaseDetailed):
        if self.revision_aggregate is not None:
            return self.revision_aggregate.parameters_for_step(case_detailed)
        return ApiCaseDetailedParameter.objects.filter(case_detailed_id=case_detailed.id).order_by('id')

    def update_test_case_detailed_proceed(self, case_id: int, case_sort: int | None):
        if self.revision_aggregate is None:
            self.get_case_detailed_queryset(case_id, case_sort).update(
                status=TaskEnum.PROCEED.value,
                error_message=None,
            )
            return
        step_ids = [step.id for step in self.get_case_detailed_queryset(case_id, case_sort)]
        ApiCaseDetailed.objects.filter(case_id=case_id, id__in=step_ids).update(
            status=TaskEnum.PROCEED.value,
            error_message=None,
        )

    def update_test_case_detailed_unfinished(self, case_id: int, case_sort: int | None, error_message: str):
        if self.revision_aggregate is None:
            self.get_case_detailed_queryset(case_id, case_sort) \
                .filter(status=TaskEnum.PROCEED.value) \
                .update(
                status=StatusEnum.FAIL.value,
                error_message=error_message,
            )
            return
        step_ids = [step.id for step in self.get_case_detailed_queryset(case_id, case_sort)]
        ApiCaseDetailed.objects.filter(
            case_id=case_id,
            id__in=step_ids,
            status=TaskEnum.PROCEED.value,
        ).update(
            status=StatusEnum.FAIL.value,
            error_message=error_message,
        )

    def save_case_detailed_runtime_state(self, case_detailed: ApiCaseDetailed):
        ApiCaseDetailed.objects.filter(
            case_id=self.case_id,
            id=case_detailed.id,
        ).update(
            status=case_detailed.status,
            error_message=case_detailed.error_message,
        )

    def case_detailed(self,
                      case_id: int,
                      case_sort: int | None,
                      parametrize: dict | None = None
                      ) -> tuple[int, str] | None:
        case_detailed_list = list(self.get_case_detailed_queryset(case_id, case_sort))
        if not case_detailed_list:
            raise AutoApiError(API_CASE_EMPTY)
        recovery_scope = (
            list(self.get_case_detailed_queryset(case_id, None))
            if case_sort is not None else case_detailed_list
        )
        main_result = None
        recovery_failures = []
        main_status = StatusEnum.FAIL.value
        self._recovery_attempted = True
        try:
            main_result = self.run_normal_steps(
                [step for step in case_detailed_list if not is_recovery_step(step)],
                parametrize,
            )
            main_status = main_result[0] if main_result else StatusEnum.SUCCESS.value
        except TestSuiteStopped:
            main_status = TaskEnum.STOPPED.value
            raise
        except Exception:
            main_status = StatusEnum.FAIL.value
            raise
        finally:
            current = self.api_case_result.main_status
            self.api_case_result.main_status = (
                StatusEnum.FAIL.value if StatusEnum.FAIL.value in (current, main_status)
                else TaskEnum.WARNING.value if TaskEnum.WARNING.value in (current, main_status)
                else main_status
            )
            recovery_failures = self.run_recovery_steps(recovery_scope)
            self.annotate_recovery_results()
        if recovery_failures:
            original = main_result[1] + '；' if main_result else ''
            return StatusEnum.FAIL.value, original + '；'.join(recovery_failures)
        return main_result

    def run_normal_steps(self, case_detailed_list, parametrize=None):
        self.case_base.case_parametrize(parametrize)
        failed_case_detailed_list = []
        warning_case_detailed_list = []
        parent_snapshot_id = None
        for index, case_detailed in enumerate(case_detailed_list):
            self.raise_if_report_stopped()
            self.current_step_execution_context = self.build_step_execution_context(
                case_detailed,
                parent_snapshot_id,
            )
            case_detailed.status = TaskEnum.PROCEED.value
            self.save_case_detailed_runtime_state(case_detailed)
            res: tuple[int, str] | None = self.detailed_parameter(case_detailed)
            from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
            if DatasourceInfrastructureService.current():
                case_detailed.status = TaskEnum.PROCEED.value
                case_detailed.error_message = DatasourceInfrastructureService.summary()
                self.save_case_detailed_runtime_state(case_detailed)
                return TaskEnum.PROCEED.value, case_detailed.error_message
            if res:
                case_detailed.status = res[0]
                case_detailed.error_message = res[1] if len(res) > 1 else None
                self.save_case_detailed_runtime_state(case_detailed)
                result_item = {
                    'id': case_detailed.id,
                    'case_sort': case_detailed.case_sort,
                    'name': self.get_case_detailed_name(case_detailed),
                    'error_message': case_detailed.error_message,
                }
                if res[0] == TaskEnum.WARNING.value:
                    warning_case_detailed_list.append(result_item)
                    parent_snapshot_id = self.current_step_execution_context.get('snapshot_id')
                    continue
                failed_case_detailed_list.append(result_item)
                for skipped_case_detailed in case_detailed_list[index + 1:]:
                    self.trace_recorder.skip_step(
                        self.get_case_detailed_name(skipped_case_detailed),
                        {'reason': '该用例前置步骤失败，未被执行'},
                        detail_ref_type='api_case_detailed',
                        detail_ref_id=skipped_case_detailed.id,
                    )
                self.api_case_result.steps.extend(
                    self.write_following_case_detailed_warning_results(
                        case_detailed_list[index + 1:]
                    )
                )
                break
            else:
                case_detailed.status = StatusEnum.SUCCESS.value
                case_detailed.error_message = None
                self.save_case_detailed_runtime_state(case_detailed)
                parent_snapshot_id = self.current_step_execution_context.get('snapshot_id')
        if failed_case_detailed_list:
            return StatusEnum.FAIL.value, self.format_case_detailed_failure_message(failed_case_detailed_list)
        if warning_case_detailed_list:
            return TaskEnum.WARNING.value, self.format_case_detailed_warning_message(warning_case_detailed_list)

    def raise_if_report_stopped(self) -> None:
        if getattr(self, '_running_recovery', False):
            return
        if not self.test_suite:
            return
        from src.apps.test_center.models import TestSuite

        if TestSuite.objects.filter(
                id=self.test_suite,
                status=TaskEnum.STOPPED.value,
        ).exists():
            raise TestSuiteStopped

    def write_following_case_detailed_warning_results(
            self, case_detailed_list: list[ApiCaseDetailed]
    ):
        if not case_detailed_list:
            return []
        skip_message = '该用例前置步骤失败，未被执行'
        warning_results = []
        for case_detailed in case_detailed_list:
            if self.revision_aggregate is None:
                api_info = ApiCaseStepService.resolve_step_api_runtime(case_detailed, allow_draft=True)
            else:
                api_info = case_detailed.api_info
            case_detailed.status = TaskEnum.WARNING.value
            case_detailed.error_message = skip_message
            self.save_case_detailed_runtime_state(case_detailed)
            for parameter in self.get_parameters_for_step(case_detailed):
                step_name = self.resolve_scenario_result_name(parameter, case_detailed)
                request_body_config, mcp_config, grpc_config = unpack_scenario_body_config(
                    api_info.protocol_type,
                    parameter.body_config,
                )
                request_model = ApiExecutionRequest(
                    method=MethodEnum(api_info.method).name,
                    url=api_info.url,
                    headers={},
                    params=parameter.params,
                    protocol_type=api_info.protocol_type,
                    body_type=api_info.body_type,
                    body_config=request_body_config,
                    sse_config=parameter.sse_config,
                    mcp_config=mcp_config,
                    grpc_config=grpc_config,
                    posterior_file=None,
                )
                res_model = ApiCaseStepResult(
                    id=case_detailed.id,
                    parameter_id=parameter.id,
                    api_info_id=api_info.id,
                    api_info_name=api_info.name,
                    name=step_name,
                    status=TaskEnum.WARNING.value,
                    request=request_model,
                    cache_data={},
                    test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    error_message=skip_message,
                )
                self.update_test_case_detailed_parameter(parameter.id, res_model)
                warning_results.append(res_model)
        return warning_results

    @staticmethod
    def get_case_detailed_name(case_detailed: ApiCaseDetailed) -> str:
        api_info_name = getattr(getattr(case_detailed, 'api_info', None), 'name', None)
        if api_info_name:
            return str(api_info_name)
        return f'场景ID:{case_detailed.id}'

    def resolve_scenario_result_name(
            self,
            parameter: ApiCaseDetailedParameter,
            case_detailed: ApiCaseDetailed,
    ) -> str:
        raw_name = parameter.name or self.get_case_detailed_name(case_detailed)
        try:
            resolved_name = self.test_setup.test_data.replace(raw_name)
        except (MangoServerError, MangoToolsError):
            return raw_name
        if resolved_name in (None, ''):
            return raw_name
        return str(resolved_name)

    @staticmethod
    def format_case_detailed_failure_message(failures: list[dict]) -> str:
        lines = [f'共 {len(failures)} 个场景失败：']
        for index, failure in enumerate(failures, start=1):
            name = failure.get('name') or f"场景ID:{failure.get('id')}"
            error_message = failure.get('error_message') or '未返回失败原因'
            lines.append(f'{index}. {name}：{error_message}')
        return '\n'.join(lines)

    @staticmethod
    def format_case_detailed_warning_message(warnings: list[dict]) -> str:
        lines = [f'共 {len(warnings)} 个步骤存在允许失败的场景：']
        for index, warning in enumerate(warnings, start=1):
            name = warning.get('name') or f"场景ID:{warning.get('id')}"
            error_message = warning.get('error_message') or '未返回失败原因'
            lines.append(f'{index}. {name}：{error_message}')
        return '\n'.join(lines)

    @staticmethod
    def format_parametrize_failure_message(error_messages: list[str]) -> str:
        lines = [f'共 {len(error_messages)} 组参数化执行失败：']
        for index, error_message in enumerate(error_messages, start=1):
            lines.append(f'{index}. {error_message or "未返回失败原因"}')
        return '\n'.join(lines)

    @staticmethod
    def format_parametrize_warning_message(error_messages: list[str]) -> str:
        lines = [f'共 {len(error_messages)} 组参数化执行存在警告：']
        for index, error_message in enumerate(error_messages, start=1):
            lines.append(f'{index}. {error_message or "未返回警告原因"}')
        return '\n'.join(lines)
