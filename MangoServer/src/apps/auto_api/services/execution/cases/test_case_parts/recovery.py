from mangotools.enums import StatusEnum, TaskEnum

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStepType
from src.apps.auto_api.schemas.recovery import is_recovery_step
from src.common.logging import log


class ApiTestCaseRecoveryMixin:
    def run_recovery_steps(self, steps):
        recovery_steps = [step for step in steps if is_recovery_step(step)]
        if not recovery_steps:
            return []
        failures = []
        self._running_recovery = True
        try:
            for step in recovery_steps:
                trace = self.trace_recorder.start_step(
                    ApiCaseTraceStepType.CASE_POSTERIOR, '最终恢复：' + self.get_case_detailed_name(step),
                    {'case_detailed_id': step.id, 'is_recovery': True},
                )
                result_start = len(self.api_case_result.steps)
                success = False
                try:
                    if not getattr(self, 'is_step_debug', False):
                        self.current_step_execution_context = self.build_step_execution_context(step, None)
                    step.status = TaskEnum.PROCEED.value
                    self.save_case_detailed_runtime_state(step)
                    result = self.detailed_parameter(step)
                    success = not result
                    step.status = StatusEnum.SUCCESS.value if success else StatusEnum.FAIL.value
                    step.error_message = result[1] if result else None
                    self.save_case_detailed_runtime_state(step)
                    if result:
                        failures.append(f'恢复步骤 {step.id}：{result[1]}')
                        self.trace_recorder.fail_step(trace, result[1])
                    else:
                        self.trace_recorder.finish_step(trace)
                except Exception as error:
                    message = getattr(error, 'msg', '恢复步骤发生内部异常，请查看执行链路')
                    failures.append(f'恢复步骤 {step.id}：{message}')
                    self.trace_recorder.fail_step(trace, message)
                    log.api.exception(f'API最终恢复失败：case={self.case_id}, step={step.id}')
                    step.status = StatusEnum.FAIL.value
                    step.error_message = message
                    try:
                        self.save_case_detailed_runtime_state(step)
                    except Exception:
                        log.api.exception(f'保存API恢复失败状态失败：case={self.case_id}, step={step.id}')
                finally:
                    for result in self.api_case_result.steps[result_start:]:
                        result.is_recovery = True
                        if not success:
                            result.status = StatusEnum.FAIL.value
                            if not getattr(result, 'error_message', None):
                                result.error_message = step.error_message
            self.api_case_result.recovery_errors.extend(failures)
            self.api_case_result.recovery_status = (
                StatusEnum.FAIL.value if self.api_case_result.recovery_errors else StatusEnum.SUCCESS.value
            )
            return failures
        finally:
            self._running_recovery = False

    def annotate_recovery_results(self):
        for step in self.api_case_result.steps:
            step.main_status = self.api_case_result.main_status
            step.recovery_status = self.api_case_result.recovery_status
            step.recovery_errors = list(self.api_case_result.recovery_errors)
