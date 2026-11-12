# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏

from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum
from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStepType
from src.apps.auto_api.models import ApiCaseDetailedParameter
from src.apps.auto_api.schemas.recovery import is_recovery_step
from src.apps.auto_api.schemas.execution import (
    ApiCaseExecutionResult,
)
from src.common.exceptions import MangoServerError
from src.common.logging import log
from src.apps.auto_api.services.execution.cases.step_debug import ApiCaseStepDebugContextService, ApiCaseStepDebugState


class ApiTestCaseDebuggingMixin:
    def _debug_step_with_state(self, state: ApiCaseStepDebugState) -> ApiCaseExecutionResult:
        self.debug_context_state = state
        self.execution_context_id = state.context_id
        self.api_case_result.execution_context_id = state.context_id
        self.current_step_execution_context = state.execution_context(
            test_env=self.test_env,
            user_id=self.user_id,
            trace_id=self.api_case_result.trace_id,
        )
        step = state.step
        parameter_queryset = ApiCaseDetailedParameter.objects.filter(case_detailed_id=step.id)
        step.status = TaskEnum.STAY_BEGIN.value
        step.error_message = None
        step.save(update_fields=['status', 'error_message'])
        parameter_queryset.update(status=TaskEnum.STAY_BEGIN.value)
        step.status = TaskEnum.PROCEED.value
        step.save(update_fields=['status'])

        context_step = self.trace_recorder.start_step(
            ApiCaseTraceStepType.GLOBAL_VARIABLES,
            '初始化单步调试上下文',
            {
                'case_detailed_id': step.id,
                'case_sort': step.case_sort,
                'context_id': state.context_id,
                'context_source': state.context_source,
                'restored_from_step_id': state.restored_from_step_id,
                'restored_cache_keys': list(state.cache_data.keys()),
                'restored_data_factory_cache_keys': list(state.data_factory_cache_data.keys()),
            },
        )
        try:
            self.test_setup.init_test_object(self.api_case.project_product_id, self.test_env)
            self.test_setup.init_public(
                self.api_case.project_product_id,
                self.test_env,
                self.api_case.front_public,
                self.api_case.front_auth_config,
            )
            if state.run_case_front:
                self.case_base.case_front_main()
            else:
                self.case_base.init_headers()
                ApiCaseStepDebugContextService.restore_cache(self.test_setup.test_data, state)
            self.trace_recorder.finish_step(context_step, {
                'context_id': state.context_id,
                'snapshot_id': state.snapshot_id,
                'restored_cache_count': len(state.cache_data),
                'restored_data_factory_cache_count': len(state.data_factory_cache_data),
            })
            if is_recovery_step(step):
                errors = self.run_recovery_steps([step])
                self.annotate_recovery_results()
                result = (StatusEnum.FAIL.value, '；'.join(errors)) if errors else None
            else:
                result = self.detailed_parameter(step)
            if result:
                self.api_case_result.status = result[0]
                self.api_case_result.error_message = result[1] if len(result) > 1 else None
                step.status = result[0]
                step.error_message = self.api_case_result.error_message
            else:
                self.api_case_result.status = StatusEnum.SUCCESS.value
                self.api_case_result.error_message = None
                step.status = StatusEnum.SUCCESS.value
                step.error_message = None
            step.save(update_fields=['status', 'error_message'])
        except (MangoToolsError, MangoServerError) as error:
            if context_step and context_step.status == TaskEnum.PROCEED.value:
                self.trace_recorder.fail_step(context_step, error.msg)
            self.api_case_result.status = StatusEnum.FAIL.value
            self.api_case_result.error_message = error.msg
            step.status = StatusEnum.FAIL.value
            step.error_message = error.msg
            step.save(update_fields=['status', 'error_message'])
        except Exception as error:
            if context_step and context_step.status == TaskEnum.PROCEED.value:
                self.trace_recorder.fail_step(context_step, str(error))
            message = f'API单步调试过程中发生异常：{error}'
            log.api.error(message)
            self.api_case_result.status = StatusEnum.FAIL.value
            self.api_case_result.error_message = message
            step.status = StatusEnum.FAIL.value
            step.error_message = message
            step.save(update_fields=['status', 'error_message'])
        finally:
            self.test_setup.close_mcp_sessions()
            self.test_setup.close_grpc_channels()
            self.test_setup.close_db_connections()

        trace_summary = {
            'status': self.api_case_result.status,
            'steps_count': len(self.api_case_result.steps),
            'context_id': state.context_id,
            'snapshot_id': state.snapshot_id,
            'case_detailed_id': step.id,
        }
        if self.api_case_result.status == StatusEnum.SUCCESS.value:
            self.trace_recorder.finish_trace(trace_summary)
        else:
            self.trace_recorder.fail_trace(self.api_case_result.error_message, trace_summary)
        return self.api_case_result

    def debug_context_payload(self) -> dict:
        state = self.debug_context_state
        if state is None:
            return {}
        return {
            'context_id': state.context_id,
            'snapshot_id': state.snapshot_id,
            'parent_snapshot_id': state.parent_snapshot_id,
            'context_source': state.context_source,
            'restored_from_step_id': state.restored_from_step_id,
            'restored_from_step_name': state.restored_from_step_name,
            'restored_cache_keys': list(state.cache_data.keys()),
            'restored_data_factory_cache_keys': list(state.data_factory_cache_data.keys()),
        }
