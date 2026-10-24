# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
import traceback

from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum
from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStepType
from src.apps.auto_api.exceptions import (
    AutoApiError,
    API_CASE_STEP_DEBUG_BUSY,
)
from src.apps.auto_api.exceptions import TestSuiteStopped
from src.apps.auto_api.schemas.execution import (
    ApiCaseExecutionResult,
)
from src.apps.gray_config.services.execution_runner import GrayCaseExecutionRunner
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.schemas.execution import TestSuiteDetailResultSchema
from src.apps.test_center.services.test_suite.update_test_suite import UpdateTestSuite
from src.common.database.mysql_lock import acquire_mysql_lock, release_mysql_lock
from src.common.exceptions import MangoServerError
from src.common.logging import log
from ..step_debug import ApiCaseStepDebugContextService


class ApiTestCaseExecutionMixin:
    def test_case(self, case_sort: int | None = None, parametrize: dict | list | None = None) -> ApiCaseExecutionResult:
        log.api.info(f'开始执行用例ID：{self.case_id}')
        res = None
        report_stopped = False
        applied_case_gray_configs = []
        self._recovery_attempted = False
        try:
            self.raise_if_report_stopped()
            self.update_test_case_detailed_proceed(self.case_id, case_sort)
            init_step = self.trace_recorder.start_step(
                ApiCaseTraceStepType.GLOBAL_VARIABLES,
                '初始化环境与全局变量',
                {
                    'project_product_id': self.api_case.project_product_id,
                    'test_env': self.test_env,
                    'front_public': self.api_case.front_public,
                    'front_auth_config': self.api_case.front_auth_config,
                },
            )
            self.test_setup.init_test_object(self.api_case.project_product_id, self.test_env)
            self.test_setup.init_public(
                self.api_case.project_product_id,
                self.test_env,
                self.api_case.front_public,
                self.api_case.front_auth_config,
            )
            self.trace_recorder.finish_step(init_step)
            front_step = self.trace_recorder.start_step(
                ApiCaseTraceStepType.CASE_FRONT,
                '执行用例前置',
                {
                    'front_custom_count': len(self.api_case.front_custom or []),
                    'front_sql_count': len(self.api_case.front_sql or []),
                    'front_headers_count': len(self.api_case.front_headers or []),
                },
            )
            self.case_base.case_front_main()
            self.trace_recorder.finish_step(front_step)
            applied_case_gray_configs = self.apply_gray_with_trace(
                '应用用例灰度',
                {
                    'scope': 'case',
                    'case_id': self.api_case.id,
                },
                lambda: GrayCaseExecutionRunner.apply_api_case(
                    self.api_case,
                    self.test_suite,
                    self.test_suite_details,
                    self.test_env,
                ),
            )
            if parametrize:
                param_step = self.trace_recorder.start_step(
                    ApiCaseTraceStepType.PARAMETERIZE,
                    '执行指定参数化',
                    parametrize,
                )
                res: tuple[int, str] | None = self.case_detailed(
                    self.case_id,
                    case_sort,
                    self.normalize_parametrize(parametrize),
                    applied_case_gray_configs,
                )
                self.trace_recorder.finish_step(param_step)
            elif self.api_case.parametrize and isinstance(self.api_case.parametrize, list):
                parametrize_failures = []
                parametrize_warnings = []
                for i in self.api_case.parametrize:
                    self.raise_if_report_stopped()
                    param_step = self.trace_recorder.start_step(
                        ApiCaseTraceStepType.PARAMETERIZE,
                        f'执行参数化：{i.get("name") or "-"}',
                        i,
                    )
                    parametrize_res: tuple[int, str] | None = self.case_detailed(
                        self.case_id,
                        case_sort,
                        i,
                        applied_case_gray_configs,
                    )
                    if parametrize_res and isinstance(parametrize_res, tuple):
                        self.trace_recorder.fail_step(param_step, parametrize_res[1])
                    else:
                        self.trace_recorder.finish_step(param_step)
                    if parametrize_res and parametrize_res[0] == StatusEnum.FAIL.value:
                        parametrize_failures.append(parametrize_res[1])
                    elif parametrize_res and parametrize_res[0] == TaskEnum.WARNING.value:
                        parametrize_warnings.append(parametrize_res[1])
                if parametrize_failures:
                    res = StatusEnum.FAIL.value, self.format_parametrize_failure_message(parametrize_failures)
                elif parametrize_warnings:
                    res = TaskEnum.WARNING.value, self.format_parametrize_warning_message(parametrize_warnings)
            else:
                res: tuple[int, str] | None = self.case_detailed(
                    self.case_id,
                    case_sort,
                    inherited_gray_configs=applied_case_gray_configs,
                )
            if res and isinstance(res, tuple):
                self.api_case_result.status, self.api_case_result.error_message = res[0], res[1]
            else:
                self.api_case_result.status, self.api_case_result.error_message = StatusEnum.SUCCESS.value, None
        except TestSuiteStopped:
            report_stopped = True
            self.api_case_result.status = TaskEnum.STOPPED.value
            self.api_case_result.main_status = TaskEnum.STOPPED.value
            self.trace_recorder.fail_trace('用户手动停止')
            log.api.info(
                f'API测试报告任务已停止：test_suite={self.test_suite}, '
                f'detail={self.test_suite_details}'
            )
        except (MangoToolsError, MangoServerError) as e:
            self.trace_recorder.fail_trace(e.msg)
            self.update_test_case(self.case_id, TaskEnum.FAIL.value)
            traceback.print_exc()
            self.api_case_result.error_message = e.msg
            self.api_case.status = StatusEnum.FAIL.value
            self.update_test_case_detailed_unfinished(self.case_id, case_sort, e.msg)
        except Exception as error:
            self.trace_recorder.fail_trace(str(error))
            self.update_test_case(self.case_id, TaskEnum.FAIL.value)
            traceback.print_exc()
            log.api.error(f'API用例执行过程中发生异常：{error}')
            self.api_case_result.error_message = f'API用例执行过程中发生异常：{error}'
            self.api_case.status = StatusEnum.FAIL.value
            self.update_test_case(self.case_id, StatusEnum.FAIL.value)
            self.update_test_case_detailed_unfinished(self.case_id, case_sort, self.api_case_result.error_message)
        try:
            if not self._recovery_attempted:
                self.api_case_result.main_status = self.api_case_result.status
                self.run_recovery_steps(
                    list(self.get_case_detailed_queryset(self.case_id, None)), applied_case_gray_configs,
                )
                self.annotate_recovery_results()
            if self.api_case_result.recovery_errors:
                recovery_message = '；'.join(self.api_case_result.recovery_errors)
                if recovery_message not in (self.api_case_result.error_message or ''):
                    self.api_case_result.error_message = '；'.join(filter(None, [
                        self.api_case_result.error_message, recovery_message,
                    ]))
                if not report_stopped:
                    self.api_case_result.status = StatusEnum.FAIL.value
            try:
                self.raise_if_report_stopped()
            except TestSuiteStopped:
                report_stopped = True
                self.api_case_result.status = TaskEnum.STOPPED.value
            if report_stopped:
                if self.test_suite_details:
                    from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService
                    TestSuiteExecutionResultService.save_stopped_api_recovery(
                        self.test_suite_details, self.api_case_result,
                    )
                return self.api_case_result
            self.run_case_posterior()
            report_step = self.trace_recorder.start_step(
                ApiCaseTraceStepType.REPORT_WRITE,
                '回写用例结果',
                {
                    'test_suite': self.test_suite,
                    'test_suite_details': self.test_suite_details,
                    'status': self.api_case_result.status,
                },
            )
            self.update_test_case(self.case_id, self.api_case_result.status)
            if self.test_suite and self.test_suite_details:
                UpdateTestSuite.update_test_suite_details(TestSuiteDetailResultSchema(
                    id=self.test_suite_details,
                    type=TestCaseTypeEnum.API,
                    test_suite=self.test_suite,
                    status=self.api_case_result.status,
                    error_message=self.api_case_result.error_message,
                    result_data=self.api_case_result
                ))
            self.trace_recorder.finish_step(report_step)
            self.test_setup.close_mcp_sessions()
            self.test_setup.close_grpc_channels()
            if self.api_case_result.status == StatusEnum.SUCCESS.value:
                self.trace_recorder.finish_trace({
                    'status': self.api_case_result.status,
                    'steps_count': len(self.api_case_result.steps),
                })
            else:
                self.trace_recorder.fail_trace(self.api_case_result.error_message, {
                    'status': self.api_case_result.status,
                    'steps_count': len(self.api_case_result.steps),
                })
            log.api.debug(f'用例测试完成：{self.api_case_result.model_dump_json()}')
            return self.api_case_result
        finally:
            if report_stopped:
                try:
                    self.case_base.case_data_factory.cleanup()
                except Exception as cleanup_error:
                    log.api.error(
                        f'API测试报告停止后的数据工厂清理失败：case={self.case_id}, '
                        f'test_suite={self.test_suite}, error={cleanup_error}'
                    )
            self.restore_gray_with_trace(
                '恢复用例灰度',
                applied_case_gray_configs,
                GrayCaseExecutionRunner.api_case_snapshot(
                    self.api_case,
                    self.test_suite,
                    self.test_suite_details,
                    test_env=self.test_env,
                ),
            )
            self.test_setup.close_mcp_sessions()
            self.test_setup.close_grpc_channels()
            self.test_setup.close_db_connections()

    def run_case_posterior(self):
        posterior_step = None
        try:
            posterior_step = self.trace_recorder.start_step(
                ApiCaseTraceStepType.CASE_POSTERIOR,
                '执行用例后置',
                {'posterior_sql_count': len(self.api_case.posterior_sql or [])},
            )
            self.case_base.case_posterior_main()
            self.trace_recorder.finish_step(posterior_step)
        except Exception as error:
            error_message = getattr(error, 'msg', str(error))
            if posterior_step:
                self.trace_recorder.fail_step(posterior_step, error_message)
            posterior_error = f'用例后置处理失败：{error_message}'
            if self.api_case_result.error_message:
                self.api_case_result.error_message = (
                    f'{self.api_case_result.error_message}；{posterior_error}'
                )
            else:
                self.api_case_result.error_message = posterior_error
            self.api_case_result.status = StatusEnum.FAIL.value
            self.api_case.status = StatusEnum.FAIL.value
            log.api.error(
                f'API用例后置处理失败：case={self.case_id}, '
                f'test_suite={self.test_suite}, detail={self.test_suite_details}, '
                f'error={error_message}'
            )

    def debug_step(
            self,
            case_detailed_id: int,
            context_id: str | None = None,
    ) -> ApiCaseExecutionResult:
        self.is_step_debug = True
        state = ApiCaseStepDebugContextService.prepare(
            case_id=self.api_case.id,
            case_detailed_id=case_detailed_id,
            test_env=self.test_env,
            user_id=self.user_id,
            context_id=context_id,
        )
        lock_name = f'mango:api-step-debug:{self.api_case.id}'
        if not acquire_mysql_lock(lock_name, timeout=0):
            raise AutoApiError(API_CASE_STEP_DEBUG_BUSY)
        try:
            return self._debug_step_with_state(state)
        finally:
            release_mysql_lock(lock_name)
