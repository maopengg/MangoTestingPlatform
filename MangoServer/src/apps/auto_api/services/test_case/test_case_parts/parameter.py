# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
import traceback
from datetime import datetime

import time
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum
from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.enums import MethodEnum
from src.apps.auto_api.schemas.recovery import is_recovery_step
from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStepType
from src.apps.auto_api.models import ApiCaseDetailed, ApiCase, ApiCaseDetailedParameter
from src.apps.auto_api.schemas.case_schema import (
    unpack_scenario_body_config,
)
from src.apps.auto_api.schemas.execution import (
    ApiExecutionRequest,
    ApiCaseStepResult,
    ApiExecutionResponse,
)
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.apps.auto_api.services.protocols.outcome import ProtocolCallOutcomeService
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
from src.apps.gray_config.services.execution_runner import GrayCaseExecutionRunner
from src.common.exceptions import MangoServerError
from src.common.logging import log
from ...base.case_data_factory import ParameterDataFactory
from ...base.case_parameter import CaseParameter


class ApiTestCaseParameterMixin:
    def detailed_parameter(
            self,
            case_detailed: ApiCaseDetailed,
            inherited_gray_configs: list | None = None,
    ) -> tuple[int, str] | None:
        api_info = case_detailed.api_info
        if self.revision_aggregate is None:
            api_info = ApiCaseStepService.resolve_step_api_runtime(case_detailed, allow_draft=True)
            case_detailed.api_info = api_info
        failed_parameter_list = []
        warning_parameter_list = []
        for parameter in self.get_parameters_for_step(case_detailed):
            if self.is_step_debug and self.revision_aggregate is None:
                parameter.status = TaskEnum.PROCEED.value
                parameter.save(update_fields=['status'])
            scenario_step = self.trace_recorder.start_step(
                ApiCaseTraceStepType.SCENARIO,
                parameter.name or self.get_case_detailed_name(case_detailed),
                {
                    'case_detailed_id': case_detailed.id,
                    'parameter_id': parameter.id,
                    'api_info_id': case_detailed.api_info_id,
                },
                detail_ref_type='api_case_detailed_parameter',
                detail_ref_id=parameter.id,
            )
            self.test_setup.init_test_object(api_info.project_product_id, self.test_env)
            self.test_setup.init_public(
                api_info.project_product_id,
                self.test_env,
                self.api_case.front_public,
                self.api_case.front_auth_config,
            )
            error_retry = 0
            retry = parameter.error_retry if parameter.error_retry else 1
            status = StatusEnum.FAIL.value
            error_message = None
            log.api.debug(f'开始执行用例的场景：{parameter.name}，这个场景失败重试：{retry} 次')
            while error_retry < retry and status != StatusEnum.SUCCESS.value:
                applied_parameter_gray_configs = []
                error_retry += 1
                retry_step = self.trace_recorder.start_step(
                    ApiCaseTraceStepType.RETRY_ROUND,
                    f'第 {error_retry}/{retry} 轮',
                    {
                        'retry_current': error_retry,
                        'retry_max': retry,
                        'retry_interval': parameter.retry_interval or 0,
                    },
                    detail_ref_type='api_case_detailed_parameter',
                    detail_ref_id=parameter.id,
                    parent_step_id=scenario_step.id if scenario_step else None,
                )
                retry_parent_id = retry_step.id if retry_step else None
                retry_aborted = False
                case_parameter = CaseParameter(
                    self.test_setup,
                    parameter,
                    api_info,
                    test_env=self.test_env,
                )
                parameter_data_factory_configs = None
                if self.revision_aggregate is not None:
                    parameter_data_factory_configs = self.revision_aggregate.data_factory_configs_for(
                        DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
                        parameter.id,
                    )
                parameter_data_factory = ParameterDataFactory(
                    self.test_setup,
                    parameter,
                    user_id=self.user_id,
                    configs=parameter_data_factory_configs,
                )
                data_factory_step = None
                front_step = None
                request_step = None
                posterior_step = None
                assertion_step = None
                cleanup_step = None
                gray_step = None
                request_body_config, mcp_config, grpc_config = unpack_scenario_body_config(
                    api_info.protocol_type,
                    parameter.body_config,
                )
                request_model = ApiExecutionRequest(
                    method=MethodEnum(api_info.method).name,
                    url=api_info.url,
                    headers=case_parameter.headers(parameter, self.case_base.case_headers),
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
                    is_recovery=is_recovery_step(case_detailed),
                    parameter_id=parameter.id,
                    retry_index=error_retry,
                    api_info_id=api_info.id,
                    api_info_name=api_info.name,
                    name=parameter.name,
                    status=StatusEnum.FAIL.value,
                    request=request_model,
                    cache_data={},
                    test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    execution_context=self.current_step_execution_context,
                )
                try:
                    gray_step = self.trace_recorder.start_step(
                        ApiCaseTraceStepType.GRAY_CONFIG,
                        '应用接口灰度',
                        {
                            'scope': 'api_step/api_parameter',
                            'case_detailed_id': case_detailed.id,
                            'parameter_id': parameter.id,
                            'inherited_config_count': len(inherited_gray_configs or []),
                        },
                        detail_ref_type='api_case_detailed_parameter',
                        detail_ref_id=parameter.id,
                        parent_step_id=retry_parent_id,
                    )
                    applied_parameter_gray_configs = GrayCaseExecutionRunner.apply_api_parameter(
                        self.api_case,
                        case_detailed,
                        parameter,
                        self.test_suite,
                        self.test_suite_details,
                        inherited_gray_configs,
                        self.test_env,
                    )
                    self.trace_recorder.finish_step(
                        gray_step,
                        self.gray_trace_summary(applied_parameter_gray_configs),
                    )
                    data_factory_step = self.trace_recorder.start_step(
                        ApiCaseTraceStepType.DATA_FACTORY_FRONT,
                        '执行场景数据工厂前置',
                        {'parameter_id': parameter.id, 'retry': error_retry},
                        detail_ref_type='api_case_detailed_parameter',
                        detail_ref_id=parameter.id,
                        parent_step_id=retry_parent_id,
                    )
                    parameter_data_factory.run_front()
                    self.trace_recorder.finish_step(data_factory_step)
                    front_step = self.trace_recorder.start_step(
                        ApiCaseTraceStepType.FRONT_PROCESS,
                        '执行场景前置处理',
                        {
                            'front_sql_count': len(parameter.front_sql or []),
                            'has_front_func': bool(parameter.front_func),
                        },
                        detail_ref_type='api_case_detailed_parameter',
                        detail_ref_id=parameter.id,
                        parent_step_id=retry_parent_id,
                    )
                    request_model = case_parameter.front_main(request_model)
                    self.trace_recorder.finish_step(front_step, {
                        'method': request_model.method,
                        'url': request_model.url,
                        'protocol_type': request_model.protocol_type,
                        'body_type': request_model.body_type,
                    })
                    request_step = self.trace_recorder.start_step(
                        ApiCaseTraceStepType.REQUEST,
                        '发送接口请求',
                        {
                            'api_info_id': case_detailed.api_info_id,
                            'method': request_model.method,
                            'url': request_model.url,
                            'protocol_type': request_model.protocol_type,
                            'body_type': request_model.body_type,
                        },
                        detail_ref_type='api_info',
                        detail_ref_id=case_detailed.api_info_id,
                        parent_step_id=retry_parent_id,
                    )
                    request_model.trace_parent_step_id = request_step.id if request_step else retry_parent_id
                    has_user_assertions = self.has_user_configured_assertions(parameter)
                    res_model.response = self.test_setup.api_request(
                        case_detailed.api_info_id,
                        self.test_env,
                        request_model,
                        api_info=(case_detailed.api_info if self.revision_aggregate is not None else None),
                        apply_api_info_posterior=not has_user_assertions,
                        initialize_public_context=False,
                    )
                    expected_codes, accept_any_status = self.resolve_protocol_expectation(
                        parameter,
                        res_model.response,
                    )
                    call_outcome = ProtocolCallOutcomeService.evaluate(
                        res_model.response,
                        expected_http_status_codes=expected_codes,
                        accept_any_http_status=accept_any_status,
                        display_name=api_info.name,
                    )
                    request_summary = {
                        'code': res_model.response.code,
                        'time': res_model.response.time,
                        'response_mode': res_model.response.response_mode,
                        'error_msg': res_model.response.error_msg,
                        'api_info_posterior_skipped_reason': (
                            res_model.response.api_info_posterior_skipped_reason
                        ),
                        'protocol_status': call_outcome.protocol_status,
                    }
                    if not call_outcome.success:
                        skip_message = '接口调用未达到场景预期，已跳过响应后置处理和业务断言。'
                        error_message = f'{call_outcome.error_message} {skip_message}'
                        status = StatusEnum.FAIL.value
                        self.trace_recorder.fail_step(request_step, error_message, request_summary)
                        res_model.status = status
                        res_model.error_message = error_message
                        res_model.failure_category = 'protocol_call_failed'
                        res_model.protocol_status = call_outcome.protocol_status
                        res_model.posterior_skipped_reason = skip_message
                        res_model.assertion_skipped_reason = skip_message
                        res_model.name = self.resolve_scenario_result_name(parameter, case_detailed)
                        res_model.cache_data = self.test_setup.test_data.get_all()
                        res_model.data_factory_cache_data = self.test_setup.test_data.get_data_factory_all()
                        self.api_case_result.steps.append(res_model)
                        self.update_api_info(case_detailed.api_info.id, res_model.response, res_model.status)
                        self.update_test_case_detailed_parameter(parameter.id, res_model)
                        continue
                    self.trace_recorder.finish_step(request_step, request_summary)
                    posterior_step = self.trace_recorder.start_step(
                        ApiCaseTraceStepType.POSTERIOR,
                        '执行响应后置处理',
                        {
                            'posterior_response_count': len(parameter.posterior_response or []),
                            'posterior_response_text_count': len(parameter.posterior_response_text or []),
                            'posterior_sql_count': len(parameter.posterior_sql or []),
                            'has_posterior_func': bool(parameter.posterior_func),
                            'has_posterior_file': bool(parameter.posterior_file),
                        },
                        detail_ref_type='api_case_detailed_parameter',
                        detail_ref_id=parameter.id,
                        parent_step_id=retry_parent_id,
                    )
                    res_model.response = case_parameter.posterior_main(res_model.response)
                    self.trace_recorder.finish_step(posterior_step)
                    assertion_step = self.trace_recorder.start_step(
                        ApiCaseTraceStepType.ASSERTION,
                        '执行接口断言',
                        {
                            'ass_jsonpath_count': len(parameter.ass_jsonpath or []),
                            'ass_general_count': len(parameter.ass_general or []),
                            'has_ass_json_all': bool(parameter.ass_json_all),
                            'has_ass_text_all': bool(parameter.ass_text_all),
                            'has_ass_schema': bool(parameter.ass_schema),
                        },
                        detail_ref_type='api_case_detailed_parameter',
                        detail_ref_id=parameter.id,
                        parent_step_id=retry_parent_id,
                    )
                    res_model.ass, status, error_message = case_parameter.ass_main(res_model.response)
                    if status == StatusEnum.SUCCESS.value:
                        self.trace_recorder.finish_step(assertion_step, {'assertion_count': len(res_model.ass or [])})
                    else:
                        self.trace_recorder.fail_step(assertion_step, error_message,
                                                      {'assertion_count': len(res_model.ass or [])})
                    res_model.status = status
                    res_model.error_message = error_message
                    res_model.name = self.resolve_scenario_result_name(parameter, case_detailed)
                    res_model.cache_data = self.test_setup.test_data.get_all()
                    res_model.data_factory_cache_data = self.test_setup.test_data.get_data_factory_all()
                    self.api_case_result.steps.append(res_model)
                    self.update_api_info(case_detailed.api_info.id, res_model.response, res_model.status)
                    self.update_test_case_detailed_parameter(parameter.id, res_model)
                except (MangoServerError, MangoToolsError) as error:
                    retry_aborted = True
                    for step in [assertion_step, posterior_step, request_step, front_step, data_factory_step,
                                 gray_step]:
                        if step and step.status == TaskEnum.PROCEED.value:
                            self.trace_recorder.fail_step(step, error.msg)
                            break
                    res_model.name = self.resolve_scenario_result_name(parameter, case_detailed)
                    res_model.cache_data = self.test_setup.test_data.get_all()
                    res_model.data_factory_cache_data = self.test_setup.test_data.get_data_factory_all()
                    res_model.status = StatusEnum.FAIL.value
                    res_model.error_message = error.msg
                    self.api_case_result.steps.append(res_model)
                    if res_model.response:
                        self.update_api_info(case_detailed.api_info.id, res_model.response,
                                             res_model.status)
                    self.update_test_case_detailed_parameter(parameter.id, res_model)
                    status = StatusEnum.FAIL.value
                    error_message = error.msg
                    break
                except Exception as error:
                    retry_aborted = True
                    for step in [assertion_step, posterior_step, request_step, front_step, data_factory_step,
                                 gray_step]:
                        if step and step.status == TaskEnum.PROCEED.value:
                            self.trace_recorder.fail_step(step, str(error))
                            break
                    res_model.name = self.resolve_scenario_result_name(parameter, case_detailed)
                    res_model.cache_data = self.test_setup.test_data.get_all()
                    res_model.data_factory_cache_data = self.test_setup.test_data.get_data_factory_all()
                    res_model.status = StatusEnum.FAIL.value
                    msg = f'发生未知错误，请联系管理员来处理异常，异常内容：{error}'
                    res_model.error_message = msg
                    self.api_case_result.steps.append(res_model)
                    if res_model.response:
                        self.update_api_info(case_detailed.api_info.id, res_model.response,
                                             res_model.status)
                    self.update_test_case_detailed_parameter(parameter.id, res_model)
                    log.api.error(f'API请求发生未知错误：{traceback.print_exc()}')
                    status = StatusEnum.FAIL.value
                    error_message = msg
                    break
                finally:
                    cleanup_error = None
                    cleanup_step = self.trace_recorder.start_step(
                        ApiCaseTraceStepType.DATA_FACTORY_CLEANUP,
                        '清理场景数据工厂',
                        {'parameter_id': parameter.id},
                        detail_ref_type='api_case_detailed_parameter',
                        detail_ref_id=parameter.id,
                        parent_step_id=retry_parent_id,
                    )
                    try:
                        parameter_data_factory.cleanup()
                        self.trace_recorder.finish_step(cleanup_step)
                    except Exception as error:
                        cleanup_error = error
                        self.trace_recorder.fail_step(cleanup_step, str(error))
                    self.restore_gray_with_trace(
                        '恢复接口灰度',
                        applied_parameter_gray_configs,
                        GrayCaseExecutionRunner.api_case_snapshot(
                            self.api_case,
                            self.test_suite,
                            self.test_suite_details,
                            case_detailed,
                            parameter,
                            self.test_env,
                        ),
                        parent_step_id=retry_parent_id,
                    )
                    if cleanup_error:
                        status = StatusEnum.FAIL.value
                        error_message = f'场景数据工厂清理失败：{cleanup_error}'
                        retry_aborted = True
                    should_wait = (
                            not retry_aborted
                            and status == StatusEnum.FAIL.value
                            and error_retry < retry
                            and bool(parameter.retry_interval)
                    )
                    if should_wait:
                        wait_step = self.trace_recorder.start_step(
                            ApiCaseTraceStepType.RETRY_WAIT,
                            '等待下次重试',
                            {
                                'seconds': parameter.retry_interval,
                                'next_retry': error_retry + 1,
                                'retry_max': retry,
                            },
                            detail_ref_type='api_case_detailed_parameter',
                            detail_ref_id=parameter.id,
                            parent_step_id=retry_parent_id,
                        )
                        time.sleep(parameter.retry_interval)
                        self.trace_recorder.finish_step(wait_step, {
                            'waited_seconds': parameter.retry_interval,
                        })
                    retry_summary = {
                        'retry_current': error_retry,
                        'retry_max': retry,
                        'status': status,
                    }
                    if status == StatusEnum.SUCCESS.value:
                        self.trace_recorder.finish_step(retry_step, retry_summary)
                    else:
                        self.trace_recorder.fail_step(retry_step, error_message, retry_summary)
                    if cleanup_error:
                        raise cleanup_error
            if status == StatusEnum.FAIL.value:
                self.trace_recorder.fail_step(scenario_step, error_message)
                result_item = {
                    'id': parameter.id,
                    'name': self.resolve_scenario_result_name(parameter, case_detailed),
                    'error_message': error_message,
                }
                if parameter.allow_failure and not getattr(self, '_running_recovery', False):
                    status = TaskEnum.WARNING.value
                    res_model.status = TaskEnum.WARNING.value
                    self.update_test_case_detailed_parameter(parameter.id, res_model)
                    warning_parameter_list.append(result_item)
                else:
                    failed_parameter_list.append(result_item)
            else:
                self.trace_recorder.finish_step(scenario_step, {'status': status})
        if failed_parameter_list:
            return StatusEnum.FAIL.value, self.format_parameter_failure_message(failed_parameter_list)
        if warning_parameter_list:
            return TaskEnum.WARNING.value, self.format_parameter_warning_message(warning_parameter_list)

    def update_api_info(self, _id: int, result_data: ApiExecutionResponse, status: int):
        return

    @classmethod
    def update_test_case(cls, case_id: int, status: int):
        ApiCase.objects.filter(id=case_id).update(status=status)

    def update_test_case_detailed_parameter(self, parameter_id, result_data: ApiCaseStepResult):
        ApiCaseDetailedParameter.objects.filter(
            id=parameter_id,
            case_detailed__case_id=self.case_id,
        ).update(status=result_data.status)

    @staticmethod
    def format_parameter_failure_message(failures: list[dict]) -> str:
        lines = [f'共 {len(failures)} 个参数场景失败：']
        for index, failure in enumerate(failures, start=1):
            name = failure.get('name') or f"参数ID:{failure.get('id')}"
            error_message = failure.get('error_message') or '未返回失败原因'
            lines.append(f'{index}. {name}：{error_message}')
        return '\n'.join(lines)

    @staticmethod
    def format_parameter_warning_message(warnings: list[dict]) -> str:
        lines = [f'共 {len(warnings)} 个参数场景允许失败且执行未通过：']
        for index, warning in enumerate(warnings, start=1):
            name = warning.get('name') or f"参数ID:{warning.get('id')}"
            error_message = warning.get('error_message') or '未返回失败原因'
            lines.append(f'{index}. {name}：{error_message}')
        return '\n'.join(lines)
