from django.core.cache import cache
# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
from django.db import transaction
from mangotools.enums import TaskEnum

from src.apps.auto_ui.models import PageSteps, UiCase, UiCaseStepsDetailed
from src.apps.auto_ui.schemas.execution import UiCaseExecutionResult, UiPageStepResult
from src.apps.data_factory.services.cleanup import DataFactoryCleanup
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.common.logging import log


class TestReportWriting:

    @classmethod
    def update_page_step_status(cls, data: UiPageStepResult) -> None:
        if data.case_step_details_id:
            cls.update_case_step_progress(data)
            return
        try:
            log.ui.debug(
                f'开始写入步骤调试结果，步骤ID：{data.id}，状态：{data.status}，'
                f'是否最终结果：{data.is_final}，元素数量：{len(data.element_result_list or [])}'
            )
            with transaction.atomic():
                res = PageSteps.objects.select_for_update().get(id=data.id)
                if cls._should_ignore_progress(res.status, data):
                    log.ui.warning(
                        f'忽略晚到的步骤调试增量结果，步骤ID：{data.id}，'
                        '当前已写入最终结果'
                    )
                    return
                write_status = data.status if data.is_final else TaskEnum.PROCEED.value
                result_data = data.model_dump()
                result_data['status'] = write_status
                res.status = write_status
                res.save(update_fields=['status'])
                if data.is_final:
                    ExecutionResultService.save_result(
                        source_type=ExecutionResultService.SOURCE_PAGE,
                        target_type=ExecutionResultService.TARGET_UI_PAGE_STEP,
                        target_id=res.id,
                        test_env=data.test_env,
                        status=write_status,
                        error_message=data.error_message,
                        result_data=result_data,
                        trace_id=data.execution_id or data.slot_id or data.workspace_id,
                    )
                    cls._mark_progress_final(data)
        except PageSteps.DoesNotExist:
            log.ui.error(
                '忽略这个报错，如果是在步骤详情中没有查到，可以忽略这个错误，步骤详情中的调试不会修改整个步骤状态')

    @classmethod
    def update_test_case(cls, data: UiCaseExecutionResult):
        log.ui.debug(f'开始写入用例测试结果，用例的测试状态是：{data.status}')
        case = UiCase.objects.get(id=data.id)
        case.status = data.status
        case.save(update_fields=['status'])
        ExecutionResultService.save_result(
            source_type=ExecutionResultService.SOURCE_PAGE,
            target_type=ExecutionResultService.TARGET_UI_CASE,
            target_id=case.id,
            test_env=data.test_env,
            status=data.status,
            error_message=data.error_message,
            result_data=data.model_dump(),
            trace_id=data.execution_id,
        )
        for i in data.steps:
            cls.update_step(i)
        cls.cleanup_data_factory(data)

    @classmethod
    def update_case_step_progress(cls, step_data: UiPageStepResult):
        log.ui.debug(
            f'开始写入用例步骤增量结果，步骤ID：{step_data.id}，'
            f'用例步骤明细ID：{step_data.case_step_details_id}，状态：{step_data.status}，'
            f'是否最终结果：{step_data.is_final}，元素数量：{len(step_data.element_result_list or [])}'
        )
        with transaction.atomic():
            case_step_detailed = UiCaseStepsDetailed.objects.select_for_update().filter(
                id=step_data.case_step_details_id
            ).first()
            if not case_step_detailed:
                return
            if cls._should_ignore_progress(case_step_detailed.status, step_data):
                log.ui.warning(
                    f'忽略晚到的用例步骤增量结果，步骤ID：{step_data.id}，'
                    f'用例步骤明细ID：{step_data.case_step_details_id}'
                )
                return
            write_status = step_data.status if step_data.is_final else TaskEnum.PROCEED.value
            result_data = step_data.model_dump()
            result_data['status'] = write_status
            case_step_detailed.status = write_status
            case_step_detailed.error_message = step_data.error_message
            case_step_detailed.save(update_fields=['status', 'error_message'])
            if step_data.is_final:
                cls._mark_progress_final(step_data)

    @classmethod
    def update_step(cls, step_data: UiPageStepResult):
        log.ui.debug(
            f'开始写入用例中步骤最终结果，步骤ID：{step_data.id}，'
            f'用例步骤明细ID：{step_data.case_step_details_id}，状态：{step_data.status}，'
            f'元素数量：{len(step_data.element_result_list or [])}'
        )

        with transaction.atomic():
            result_data = step_data.model_dump()
            result_data['is_final'] = True
            page_step = PageSteps.objects.select_for_update().filter(id=step_data.id).first()
            if page_step:
                page_step.status = step_data.status
                page_step.save(update_fields=['status'])
                ExecutionResultService.save_result(
                    source_type=ExecutionResultService.SOURCE_PAGE,
                    target_type=ExecutionResultService.TARGET_UI_PAGE_STEP,
                    target_id=page_step.id,
                    test_env=step_data.test_env,
                    status=step_data.status,
                    error_message=step_data.error_message,
                    result_data=result_data,
                    trace_id=step_data.execution_id or step_data.slot_id or step_data.workspace_id,
                )
            else:
                log.ui.warning(f'用例结果中的页面步骤不存在，步骤ID：{step_data.id}')

            if step_data.case_step_details_id:
                case_step_detailed = UiCaseStepsDetailed.objects.select_for_update().get(
                    id=step_data.case_step_details_id
                )
                case_step_detailed.status = step_data.status
                case_step_detailed.error_message = step_data.error_message
                case_step_detailed.save(update_fields=['status', 'error_message'])
            else:
                log.ui.debug(
                    f'用例结果中的步骤无用例步骤明细，仅同步页面步骤结果，'
                    f'步骤ID：{step_data.id}，步骤名称：{step_data.name}'
                )
            cls._mark_progress_final(step_data)

    @classmethod
    def _should_ignore_progress(cls, current_status, data: UiPageStepResult) -> bool:
        progress_key = cls._progress_final_key(data)
        if progress_key:
            if cache.get(progress_key):
                return True
            sequence_key = f'{progress_key}:sequence'
            last_sequence = int(cache.get(sequence_key) or 0)
            if data.progress_sequence and data.progress_sequence < last_sequence:
                return True
            if data.progress_sequence:
                cache.set(
                    sequence_key,
                    data.progress_sequence,
                    timeout=24 * 60 * 60,
                )
            return False
        if data.is_final:
            return False
        return current_status not in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value)

    @classmethod
    def _mark_progress_final(cls, data: UiPageStepResult) -> None:
        progress_key = cls._progress_final_key(data)
        if progress_key:
            cache.set(progress_key, True, timeout=24 * 60 * 60)

    @staticmethod
    def _progress_final_key(data: UiPageStepResult) -> str | None:
        execution_key = data.execution_id or data.slot_id or data.workspace_id
        if not execution_key:
            return None
        detail_key = data.case_step_details_id or data.id
        return f'ui-progress-final:{execution_key}:{detail_key}'

    @classmethod
    def cleanup_data_factory(cls, data: UiCaseExecutionResult):
        for execution_id in data.data_factory_auto_cleanup_execution_ids:
            try:
                result = DataFactoryCleanup.cleanup_execution(
                    execution_id,
                    force_cleanup=True,
                    allow_missing=True,
                )
                if result.get('fail'):
                    log.ui.error(f'UI用例数据工厂自动清理失败，execution_id:{execution_id}，结果:{result}')
                else:
                    log.ui.info(f'UI用例数据工厂自动清理完成，execution_id:{execution_id}，结果:{result}')
            except Exception as error:
                log.ui.error(f'UI用例数据工厂自动清理失败，execution_id:{execution_id}，错误:{error}')
