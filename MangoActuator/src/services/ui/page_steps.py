# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/5/4 14:34
# @Author : 毛鹏
from src.services.system_error_reporter import ActuatorSystemErrorReporter
import asyncio
import copy
import inspect
import json
import os
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Any
from urllib import parse
from urllib.parse import urljoin

from mangoautomation.enums import ElementOperationEnum
from mangoautomation.exceptions import MangoAutomationError
from mangoautomation.models import ElementModel
from mangoautomation.models import ElementResultModel
from mangoautomation.uidrives import AsyncElement
from mangoautomation.uidrives import AsyncWebRuntime, BaseData
from mangotools.exceptions import MangoToolsError
from mangotools.test_target import resolve_test_target
from mangotools.models import MethodModel
from playwright._impl._errors import TargetClosedError
from playwright.async_api import Request, Route, Error

from mangotools.enums import ApiTypeEnum, DriveTypeEnum, MethodEnum, StatusEnum, TaskEnum, UiPublicTypeEnum
from src.enums.api_enum import ClientEnum
from mangotools.enums import ClientTypeEnum
from src.exceptions import ERROR_MSG_0001, ERROR_MSG_0005, ERROR_MSG_0010, ERROR_MSG_0025, UiError
from mangotools.contracts import ApiRecordingContract
from mangoautomation.models import PageStepsResultModel, PageStepsModel
from src.network import ActuatorApiEventEnum, ActuatorUiEventEnum, socket_conn, HTTP
from src.services.runtime.session import AutomationSessionManager
from src.services.data_source_execution import (
    UiDataSourceExecutionCallback,
    UiDataSourceExecutionService,
)
from src.services.ui.element_snapshot import UiElementSnapshotReporter
from src.services.ui.live_stream.runtime_registry import UiRuntimeRegistry
from src.services.ui.step_healing import PageStepHealingOrchestrator
from src.tools import project_dir
from src.tools.decorator.error_handle import async_error_handle
from src.tools.json_tools import json_dumps
from src.tools.log_collector import log
from src.tools.executor_task_context import format_executor_task_log
from src.tools.send_global_msg import send_global_msg
from src.tools.execution_activity import ExecutionActivity, execution_identity
from src.tools.set_config import SetConfig


@dataclass
class UiPublicCodeContext:
    test_data: Any
    environment_config: Any
    execute_data_source: Any = None
    web_runtime: Any = None
    base_data: Any = None


class PageSteps:
    PROGRESS_MODE_CASE = 'case'
    PROGRESS_MODE_PAGE_STEP_DEBUG = 'page_step_debug'
    PROGRESS_PUSH_ELEMENT_COUNT = 10
    PROGRESS_PUSH_INTERVAL = 60

    def __init__(self,
                 base_data: BaseData,
                 web_runtime: AsyncWebRuntime,
                 page_steps_model: PageStepsModel | None,
                 is_step=False,
                 progress_mode: str | None = None,
                 progress_user: str | None = None,
                 case_id: int | None = None):
        self.web_runtime = web_runtime
        self.test_object: str = ''
        self.base_data = base_data
        self.page_steps_model = page_steps_model
        self.is_step = is_step
        self.progress_mode = progress_mode
        self.progress_user = progress_user
        self.case_id = case_id
        self._last_progress_push_time = datetime.now()
        self._last_progress_push_count = 0
        self._progress_sequence = 0
        self._device_opened = False
        self._activity_step_index = 0
        self._activity_step_total = len(page_steps_model.element_list) if (
            page_steps_model and isinstance(page_steps_model.element_list, list) and not page_steps_model.flow_data
        ) else 0
        self._step_healing = None
        self._runtime_flow_root = None
        self.host_list: list[dict] = []
        self._data_source_callback = None
        if page_steps_model:
            source_type = 'ui_case' if case_id else 'ui_page_step'
            source_id = case_id or page_steps_model.id
            self._data_source_callback = UiDataSourceExecutionCallback(
                project_product_id=page_steps_model.project_product,
                test_env=page_steps_model.test_env,
                test_data=base_data.test_data,
                source_context={
                    'source_type': source_type,
                    'source_stage': 'page_step',
                    'source_id': source_id,
                    'case_id': case_id,
                    'page_step_id': page_steps_model.id,
                    'case_step_detail_id': getattr(page_steps_model, 'case_steps_id', None),
                    'execution_id': getattr(page_steps_model, 'execution_id', None),
                },
            )
            self.page_step_result_model = PageStepsResultModel(
                execution_id=getattr(self.page_steps_model, 'execution_id', None),
                workspace_id=getattr(self.page_steps_model, 'workspace_id', None),
                id=self.page_steps_model.id,
                name=self.page_steps_model.name,
                type=self.page_steps_model.type,
                project_product_id=self.page_steps_model.project_product,
                project_product_name=self.page_steps_model.project_product_name,
                test_env=getattr(self.page_steps_model, 'test_env', None),
                case_step_details_id=getattr(self.page_steps_model, 'case_steps_id', None),
                test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                cache_data={},
                test_object='',
                status=StatusEnum.FAIL.value,
                element_result_list=[],
                is_auth_step=self.page_steps_model.is_auth_step,
            )

    async def page_init(self, is_page_init: bool = True):
        self.base_data.set_database_execute_callback(self._data_source_callback)
        log.debug(f'设置UI自定义值-1：{not is_page_init},数据：{self.page_steps_model.public_data_list}')
        if not is_page_init:
            return
        for cache_data in self.page_steps_model.public_data_list:
            if cache_data.type == UiPublicTypeEnum.CUSTOM.value:
                send_global_msg(f'UI-设置全局变量-自定义成功')
                log.debug(f'设置UI自定义值key-2：{cache_data.key}，value：{cache_data.value}')
                self.base_data.test_data.set_cache(cache_data.key, cache_data.value)
            elif cache_data.type == UiPublicTypeEnum.SQL.value:
                send_global_msg('UI-开始设置全局数据库变量')
                await UiDataSourceExecutionService.execute(
                    item={
                        'datasource_alias': cache_data.datasource_alias,
                        'key': cache_data.key,
                        'value': cache_data.value,
                    },
                    project_product_id=self.page_steps_model.project_product,
                    test_env=self.page_steps_model.test_env,
                    test_data=self.base_data.test_data,
                    require_cache_result=True,
                    confirm_write=False,
                    source_context={
                        'source_type': 'ui_global_variable',
                        'source_stage': 'global_variable',
                        'source_id': getattr(cache_data, 'id', None),
                        'global_variable_id': getattr(cache_data, 'id', None),
                        'case_id': self.case_id,
                        'page_step_id': self.page_steps_model.id,
                    },
                )
            elif cache_data.type == UiPublicTypeEnum.CODE.value:
                send_global_msg(f'UI-设置全局变量-代码变量成功')
                namespace = {}
                exec(cache_data.value, namespace)
                variable_func = namespace.get('variable')
                if not callable(variable_func):
                    raise UiError(300, f'代码变量【{cache_data.key}】必须定义 variable(context) 函数')
                result = variable_func(UiPublicCodeContext(
                    test_data=self.base_data.test_data,
                    environment_config=self.page_steps_model.environment_config,
                    execute_data_source=self._execute_custom_data_source,
                    web_runtime=self.web_runtime,
                    base_data=self.base_data,
                ))
                if inspect.isawaitable(result):
                    result = await result
                if not isinstance(result, dict):
                    raise UiError(300, f'代码变量【{cache_data.key}】的 variable(context) 必须返回 dict')
                cache_values = {key: value for key, value in result.items() if value is not None}
                if not cache_values:
                    raise UiError(300, f'代码变量【{cache_data.key}】返回数据为空')
                for key, value in cache_values.items():
                    self.base_data.test_data.set_cache(key, value)
                log.debug(f'设置UI代码变量key-4：{list(cache_values.keys())}')

    async def _execute_custom_data_source(self, datasource_alias_id, operation_config) -> dict:
        return await UiDataSourceExecutionService.execute(
            item={
                'datasource_alias': datasource_alias_id,
                'value': operation_config,
            },
            project_product_id=self.page_steps_model.project_product,
            test_env=self.page_steps_model.test_env,
            test_data=self.base_data.test_data,
            require_cache_result=False,
            confirm_write=True,
            source_context={
                'source_type': 'ui_custom_code',
                'source_stage': 'custom_code',
                'source_id': self.case_id or self.page_steps_model.id,
                'case_id': self.case_id,
                'page_step_id': self.page_steps_model.id,
            },
        )

    async def steps_main(self) -> PageStepsResultModel:
        before_wait_seconds = self.page_steps_model.step_control.before_wait_seconds
        if before_wait_seconds:
            send_global_msg(f'UI-步骤执行前等待：{before_wait_seconds} 秒', log_level='debug')
            await asyncio.sleep(before_wait_seconds)
        error_retry = 0
        self.page_steps_model.error_retry = self.page_steps_model.error_retry if self.page_steps_model.error_retry else 1
        send_global_msg(
            f'UI-开始执行步骤，当前步骤重试：{self.page_steps_model.error_retry} 次',
            log_level='debug',
        )
        while error_retry < self.page_steps_model.error_retry and self.page_step_result_model.status == StatusEnum.FAIL.value:
            if error_retry != 0 and not self.is_step:
                log.debug(f'开始第：{error_retry} 次重试步骤：{self.page_steps_model.name}')
                send_global_msg(
                    f'UI-正在执行步骤，当前步骤重试到第：{error_retry} 次', log_level='debug',
                )
                await self._steps_retry()
            error_retry += 1
            try:
                if not self.page_steps_model.flow_data:
                    element_models = self.page_steps_model.element_list
                    for index, element_list in enumerate(element_models):
                        element_result = await self._ope_steps(element_list, [])
                        if (
                            element_result.status == StatusEnum.SUCCESS.value
                            and index + 1 < len(element_models)
                        ):
                            element_result.next_node_id = element_models[index + 1].id
                        await self._record_element_result(element_result)
                        if element_result.status == StatusEnum.FAIL.value:
                            break
                else:
                    self._runtime_flow_root = self.page_steps_model.flow_data
                    await self._prepare_entry_device()
                    flow_entry, element_result = await self._prepare_flow_entry(
                        self.page_steps_model.flow_data,
                    )
                    if flow_entry is not None:
                        element_result = await self.test_flow_data(flow_entry)
                    elif element_result is not None:
                        await self._record_element_result(element_result)
                    if element_result and element_result.status == StatusEnum.FAIL.value:
                        continue
                    if (
                        element_result
                        and not await self._success_criteria_met()
                        and not await self._wait_for_success_criteria()
                    ):
                        recovered = await self._recover_step(
                            element_result,
                            self._element_model(element_result.id),
                            trigger='success_criteria_mismatch',
                        )
                        if not recovered or not await self._wait_for_success_criteria():
                            self.page_step_result_model.status = StatusEnum.FAIL.value
                            self.page_step_result_model.error_message = '页面步骤执行完成，但未达到配置的成功条件'
                            continue
            except (MangoToolsError, MangoAutomationError) as error:
                log.debug(f'步骤发生未知失败-1，类型：{error}，详情：{traceback.format_exc()}')
                self.page_step_result_model.status = StatusEnum.FAIL.value
                self.page_step_result_model.error_message = error.msg
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, 'services/ui/page_steps:steps_main')
                log.error(f'步骤发生未知失败-2，类型：{error}，详情：{traceback.format_exc()}')
                self.page_step_result_model.status = StatusEnum.FAIL.value
                self.page_step_result_model.error_message = str(error)
        self.page_step_result_model.cache_data = self.base_data.test_data.get_all()
        self.page_step_result_model.data_factory_cache_data = self.base_data.test_data.get_data_factory_all()
        self.page_step_result_model.test_object = self.test_object
        after_wait_seconds = self.page_steps_model.step_control.after_wait_seconds
        if after_wait_seconds:
            send_global_msg(f'UI-步骤执行后等待：{after_wait_seconds} 秒', log_level='debug')
            await asyncio.sleep(after_wait_seconds)
        self.page_step_result_model.stop_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.page_step_result_model.is_final = True
        if self.progress_mode == self.PROGRESS_MODE_CASE:
            await self._send_progress(force=True)
        return self.page_step_result_model

    async def _prepare_entry_device(self) -> None:
        """Open a configured Web step URL before evaluating its entry criteria."""
        if (
            self.page_steps_model.type == DriveTypeEnum.WEB.value
            and not self._device_opened
            and self._should_force_step_url()
        ):
            await self._open_web_device(AsyncElement(self.base_data, self.page_steps_model.type))
            self._device_opened = True

    async def test_flow_data(self, flow_data: dict) -> ElementResultModel:
        if hasattr(flow_data, 'model_dump'):
            flow_data = flow_data.model_dump(mode='json')

        async def search_element_model(_id) -> ElementModel:
            element_model = next((i for i in self.page_steps_model.element_list if i.id == _id), None)
            if not element_model:
                raise UiError(*ERROR_MSG_0001)
            element_model = await self._update_element_data(_id, element_model)
            return element_model

        element_model = await search_element_model(flow_data.get('id'))
        element_list_model = []
        if element_model.type == ElementOperationEnum.CONDITION:
            for i in flow_data.get('children', []):
                element_list_model.append(await search_element_model(i.get('id')))

        element_result = None
        if (
            self._has_condition_rules(element_model.precondition)
            and self.base_data.page
            and not await self._condition_met(element_model.precondition)
        ):
            element_result = ElementResultModel(
                id=element_model.id,
                name=element_model.name,
                type=getattr(element_model.type, 'value', element_model.type),
                ope_key=element_model.ope_key,
                status=StatusEnum.FAIL.value,
                error_message='当前页面不满足节点前置条件',
            )
            if not await self._recover_step(
                element_result, element_model, trigger='precondition_mismatch',
            ):
                await self._record_element_result(element_result)
                return element_result
        if element_result is None:
            element_result = await self._ope_steps(element_model, element_list_model)
        if element_result.status == StatusEnum.FAIL.value:
            if await self._recover_step(element_result, element_model, trigger='node_failed'):
                if element_result.next_node_id:
                    await self._record_element_result(element_result)
                    target = self._find_flow_node(self._runtime_flow_root, element_result.next_node_id)
                    return await self.test_flow_data(target) if target else element_result
                if element_result.status == StatusEnum.SUCCESS.value:
                    # A guarded direct action or checkpoint-based skip completed this node.
                    pass
                else:
                    await self._record_element_result(element_result)
                    return element_result
            else:
                await self._record_element_result(element_result)
                return element_result
        if (
            element_result.status == StatusEnum.SUCCESS.value
            and self._has_condition_rules(element_model.postcondition)
        ):
            if (
                not await self._condition_met(element_model.postcondition)
                and not await self._wait_for_condition(element_model.postcondition)
            ):
                element_result.status = StatusEnum.FAIL.value
                element_result.error_message = '节点操作已执行，但页面未达到配置的后置条件'
                recovered = await self._recover_step(
                    element_result, element_model, trigger='postcondition_mismatch',
                )
                if not recovered or not await self._condition_met(element_model.postcondition):
                    element_result.status = StatusEnum.FAIL.value
                    element_result.error_message = '节点操作已执行，但页面未达到配置的后置条件'
                    await self._record_element_result(element_result)
                    return element_result
        if element_result.next_node_id:
            for f in flow_data.get('children', []):
                if f['id'] == element_result.next_node_id:
                    await self._record_element_result(element_result)
                    return await self.test_flow_data(f)
            await self._record_element_result(element_result)
            raise UiError(**ERROR_MSG_0005)
        elif len(flow_data.get('children')) == 1:
            element_result.next_node_id = flow_data['children'][0]['id']
            await self._record_element_result(element_result)
            return await self.test_flow_data(flow_data.get('children')[0])
        elif len(flow_data.get('children')) > 1:
            await self._record_element_result(element_result)
            log.error(f'这里不应该有多个：{json_dumps(self.page_steps_model)}--{json_dumps(flow_data)}')
            raise UiError(**ERROR_MSG_0005)
        else:
            await self._record_element_result(element_result)
            return element_result

    def _element_model(self, detail_id):
        return next(
            (item for item in self.page_steps_model.element_list if str(item.id) == str(detail_id)),
            None,
        )

    @staticmethod
    def _has_condition_rules(condition) -> bool:
        if hasattr(condition, 'model_dump'):
            condition = condition.model_dump(mode='json')
        return bool(isinstance(condition, dict) and condition.get('conditions'))

    def _healing_runtime(self):
        if self._step_healing is None and self.base_data.page:
            self._step_healing = PageStepHealingOrchestrator(
                self.base_data.page, self.page_steps_model, self.base_data.test_data,
            )
        return self._step_healing

    async def _condition_met(self, condition) -> bool:
        runtime = self._healing_runtime()
        if runtime is None:
            return False
        return await runtime.observer.matches(condition)

    async def _success_criteria_met(self) -> bool:
        criteria = getattr(self.page_steps_model, 'success_criteria', None) or {}
        if not criteria.get('conditions'):
            return True
        return await self._condition_met(criteria)

    async def _wait_for_success_criteria(self, timeout_seconds: float = 5.0) -> bool:
        criteria = getattr(self.page_steps_model, 'success_criteria', None) or {}
        if not criteria.get('conditions'):
            return True
        return await self._wait_for_condition(criteria, timeout_seconds=timeout_seconds)

    async def _wait_for_condition(self, condition, timeout_seconds: float = 2.0) -> bool:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while time.monotonic() < deadline:
            await asyncio.sleep(.25)
            if await self._condition_met(condition):
                return True
        return False

    async def _prepare_flow_entry(self, flow_data):
        """Resolve a safe starting node before the configured flow begins."""
        criteria = getattr(self.page_steps_model, 'entry_criteria', None) or {}
        if not criteria.get('conditions') or await self._condition_met(criteria):
            return flow_data, None
        # A SPA may finish navigation before its visible content is committed.
        # Give the configured entry condition a short settling window before
        # treating the page as a changed workflow and invoking AI recovery.
        if await self._wait_for_condition(criteria):
            return flow_data, None
        runtime = self._healing_runtime()
        root_element = self._element_model(
            flow_data.get('id') if isinstance(flow_data, dict) else getattr(flow_data, 'id', None),
        )
        if runtime is None or root_element is None:
            return None, self._entry_failure(root_element, '当前页面不满足页面步骤进入条件')

        first, _ = await runtime.observer.snapshot(runtime.checkpoints)
        await asyncio.sleep(.25)
        second, _ = await runtime.observer.snapshot(runtime.checkpoints)
        stable = set(first.matched_checkpoints).intersection(second.matched_checkpoints)
        if 'entry' in second.matched_checkpoints:
            return flow_data, None
        if 'success' in stable:
            result = self._entry_failure(root_element, '')
            result.status = StatusEnum.SUCCESS.value
            result.error_message = None
            return None, result

        ordered_nodes = self._flatten_flow_nodes(flow_data)
        resumable = [
            node for node in ordered_nodes
            if f'node:{node.get("id")}:pre' in stable
        ]
        if len(resumable) == 1:
            target = resumable[0]
            log.debug(
                f'页面步骤入口不匹配，稳定命中节点前置检查点，从节点续跑：'
                f'page_step_id={self.page_steps_model.id}，node_id={target.get("id")}',
            )
            return target, None

        outcome = await runtime.recover(
            None,
            trigger='entry_criteria_mismatch',
            error_message=(
                '当前页面不满足页面步骤进入条件，且命中了多个中间检查点，无法安全确定续跑节点'
                if len(resumable) > 1
                else '当前页面不满足页面步骤进入条件，且未命中可续跑的中间检查点'
            ),
            execution_history=self._execution_history(),
        )
        if outcome.status == 'recovered' and await self._condition_met(criteria):
            return flow_data, None
        message = outcome.user_message or '当前页面不满足页面步骤进入条件'
        return None, self._entry_failure(root_element, message)

    @staticmethod
    def _entry_failure(element_model, message):
        return ElementResultModel(
            id=getattr(element_model, 'id', 0),
            name=getattr(element_model, 'name', '页面步骤入口'),
            type=getattr(getattr(element_model, 'type', 0), 'value', getattr(element_model, 'type', 0)),
            ope_key=getattr(element_model, 'ope_key', None),
            status=StatusEnum.FAIL.value,
            error_message=message,
        )

    @classmethod
    def _flatten_flow_nodes(cls, flow_data):
        if hasattr(flow_data, 'model_dump'):
            flow_data = flow_data.model_dump(mode='json')
        if not isinstance(flow_data, dict):
            return []
        result = [flow_data]
        for child in flow_data.get('children') or []:
            result.extend(cls._flatten_flow_nodes(child))
        return result

    async def _recover_step(self, element_result, element_model, *, trigger: str) -> bool:
        runtime = self._healing_runtime()
        if runtime is None or element_model is None:
            return False
        outcome = await runtime.recover(
            element_model,
            trigger=trigger,
            error_message=element_result.error_message,
            execution_history=self._execution_history(),
        )
        if outcome.status != 'recovered':
            if outcome.user_message:
                element_result.error_message = f'{element_result.error_message or ""}；{outcome.user_message}'.strip('；')
            return False
        if outcome.retry_current_node:
            retry_result = await self._ope_steps(element_model, [])
            element_result = self._copy_result(element_result, retry_result)
        elif outcome.skip_current_node or outcome.next_node_id or outcome.executed_plan:
            element_result.status = StatusEnum.SUCCESS.value
            element_result.error_message = None
        if outcome.next_node_id:
            element_result.next_node_id = int(outcome.next_node_id) if str(outcome.next_node_id).isdigit() else outcome.next_node_id
        element_result.locator_engine = {
            **(element_result.locator_engine or {}),
            'step_healing': {
                'trace_id': outcome.trace_id,
                'status': outcome.status,
                'message': outcome.user_message,
                'temporary': True,
            },
        }
        return element_result.status == StatusEnum.SUCCESS.value

    def _execution_history(self):
        return [
            {
                'node_id': str(item.id),
                'status': 'success' if item.status == StatusEnum.SUCCESS.value else 'failed',
                'error': item.error_message,
            }
            for item in (self.page_step_result_model.element_result_list or [])
        ]

    @staticmethod
    def _copy_result(target, source):
        for field in source.model_fields:
            setattr(target, field, getattr(source, field))
        return target

    @classmethod
    def _find_flow_node(cls, flow_data, detail_id):
        if hasattr(flow_data, 'model_dump'):
            flow_data = flow_data.model_dump(mode='json')
        if not isinstance(flow_data, dict):
            return None
        if str(flow_data.get('id')) == str(detail_id):
            return flow_data
        for child in flow_data.get('children') or []:
            found = cls._find_flow_node(child, detail_id)
            if found:
                return found
        return None

    async def _update_element_data(self, _id, element_model) -> ElementModel:
        if self.is_step:
            return element_model

        element_data = next(
            (elem
             for elem in getattr(self.page_steps_model, 'case_data', [])
             if elem.page_step_details_id == _id),
            None
        )
        if element_data is None:
            raise UiError(*ERROR_MSG_0025)
        match element_model.type:
            case ElementOperationEnum.OPE | ElementOperationEnum.ASS | ElementOperationEnum.CONDITION | ElementOperationEnum.FORCE_WAIT:
                element_model.ope_value = [MethodModel(**i) for i in (element_data.page_step_details_data or [])]
            case ElementOperationEnum.SQL:
                element_model.sql_execute = element_data.page_step_details_data
            case ElementOperationEnum.CUSTOM:
                element_model.custom = element_data.page_step_details_data
            case _:
                element_model.func = element_data.page_step_details_data[0]['func']
        if element_data.condition_value:
            element_model.condition_value = element_data.condition_value
        return element_model

    async def _ope_steps(self, element_model, element_list_model) -> ElementResultModel:
        action_name = element_model.name or element_model.ope_key
        send_global_msg(f'UI-开始执行元素或操作：{action_name}', log_level='debug')
        self._activity_step_index += 1
        for prefix in ("ui-case", "ui-step"):
            ExecutionActivity.update(
                execution_identity(self.page_steps_model, prefix),
                f"正在执行：{action_name}",
                progress_current=max(0, self._activity_step_index - 1),
                progress_total=self._activity_step_total or None,
            )
        if element_model.type in (ElementOperationEnum.FORCE_WAIT, ElementOperationEnum.FORCE_WAIT.value):
            element_result = await self._execute_force_wait_element(element_model)
        elif element_model.type in (ElementOperationEnum.SQL, ElementOperationEnum.SQL.value):
            element_ope = AsyncElement(self.base_data, self.page_steps_model.type)
            element_result = await element_ope.element_main(element_model, element_list_model)
        else:
            element_ope = AsyncElement(self.base_data, self.page_steps_model.type)
            if not self._device_opened:
                await self._open_web_device(element_ope)
                self._device_opened = True
            async with UiRuntimeRegistry.operation_guard(
                self.base_data.page or self.base_data.ios
            ):
                element_result = await element_ope.element_main(element_model, element_list_model)
        send_global_msg(f'UI-结束执行元素或操作：{action_name}', log_level='debug')
        if element_result.status == StatusEnum.FAIL.value:
            log.warning(format_executor_task_log(
                'UI节点执行未通过',
                page_step_id=getattr(self.page_steps_model, 'id', None),
                element_id=getattr(element_model, 'id', None),
                element_name=action_name,
                operation=getattr(element_model, 'ope_key', None),
                error=element_result.error_message,
            ))
        for prefix in ("ui-case", "ui-step"):
            ExecutionActivity.update(
                execution_identity(self.page_steps_model, prefix),
                progress_current=self._activity_step_index,
            )
        self.page_step_result_model.status = element_result.status
        self.page_step_result_model.error_message = element_result.error_message
        if element_model.type in (
                ElementOperationEnum.FORCE_WAIT,
                ElementOperationEnum.FORCE_WAIT.value,
        ):
            return element_result
        await UiElementSnapshotReporter.report_ambiguous_success_heal_record(
            self.base_data.page,
            self.page_steps_model,
            element_model,
            element_result,
            self.base_data.locator_engine,
        )
        await self._capture_step_screenshot(element_model, element_result)
        await self._upload_element_picture(element_result)
        await UiElementSnapshotReporter.report_runtime_result(
            self.base_data.page,
            self.page_steps_model,
            element_model,
            element_result,
        )
        locator_engine_result = element_result.locator_engine or {}
        if element_model.collect_snapshot or locator_engine_result.get('temporary_heal_used'):
            UiElementSnapshotReporter.schedule_success_snapshot(
                self.base_data.page,
                self.page_steps_model,
                element_model,
                element_result,
            )
        await UiElementSnapshotReporter.report_failed_heal_record(
            self.base_data.page,
            self.page_steps_model,
            element_model,
            element_result,
            self.base_data.locator_engine,
        )
        return element_result

    async def _execute_force_wait_element(self, element_model) -> ElementResultModel:
        started_at = time.perf_counter()
        values = {item.f: item.v for item in element_model.ope_value or []}
        result = ElementResultModel(
            id=element_model.id,
            name=element_model.name or '强制等待',
            type=ElementOperationEnum.FORCE_WAIT.value,
            ope_key=None,
            ope_value=[
                item.model_dump(mode='json') if hasattr(item, 'model_dump') else item
                for item in element_model.ope_value or []
            ],
            test_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            status=StatusEnum.FAIL.value,
        )
        try:
            seconds = float(values.get('seconds', 1))
            if seconds < 0 or seconds > 3600:
                raise ValueError('强制等待时长必须在 0 到 3600 秒之间')
            result.name = element_model.name or f'强制等待 {seconds:g} 秒'
            send_global_msg(f'UI-强制等待：{seconds:g} 秒')
            await asyncio.sleep(seconds)
            result.status = StatusEnum.SUCCESS.value
        except (TypeError, ValueError) as error:
            result.error_message = str(error)
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/page_steps:_execute_force_wait_element')
            result.error_message = str(error)
        result.stop_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result.duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return result

    async def _record_element_result(self, element_result: ElementResultModel) -> None:
        self.page_step_result_model.status = element_result.status
        self.page_step_result_model.error_message = element_result.error_message
        self.page_step_result_model.element_result_list.append(element_result)
        await self._send_node_progress(element_result)
        await self._send_progress(element_result=element_result)

    async def _capture_step_screenshot(self, element_model, element_result: ElementResultModel):
        if element_result.picture_path:
            return
        if self.page_steps_model.type != DriveTypeEnum.WEB.value:
            return
        if element_model.type not in (
                ElementOperationEnum.OPE, ElementOperationEnum.OPE.value,
                ElementOperationEnum.ASS, ElementOperationEnum.ASS.value,
        ):
            return
        if not SetConfig.get_web_step_screenshot():  # type: ignore
            return
        if not self.base_data.page or self.base_data.page.is_closed():
            return
        try:
            file_name = f'步骤截图-{self._safe_file_name(element_model.name or element_model.ope_key)}-{datetime.now().strftime("%Y%m%d%H%M%S%f")}.jpg'
            file_path = os.path.join(project_dir.screenshot(), file_name)
            await self.base_data.page.screenshot(path=file_path, full_page=True, timeout=10000)
            element_result.picture_path = file_path
            element_result.picture_name = file_name
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/page_steps:_capture_step_screenshot')
            log.warning(
                f'WEB步骤截图失败，不影响执行，元素：{element_model.name or element_model.ope_key}，'
                f'类型：{type(error)}，详情：{error}'
            )

    async def _upload_element_picture(self, element_result: ElementResultModel):
        if not (element_result.picture_name and element_result.picture_path):
            return None
        if not os.path.exists(element_result.picture_path):
            failure_reason = f'执行器本地截图文件不存在：{element_result.picture_path}'
            log.warning(
                f'截图上传已跳过，本地文件不存在：{element_result.picture_path}，'
                f'截图名称：{element_result.picture_name}'
            )
            element_result.picture_path = None
            return failure_reason
        log.debug(f'上传截图文件名称：{element_result.picture_name}，绝对路径：{element_result.picture_path}')
        upload_result = await HTTP.system.upload_file(element_result.picture_path, element_result.picture_name)
        if not upload_result.success or not upload_result.path:
            failure_reason = upload_result.error_message or '未知上传错误'
            if self.page_step_result_model.status == StatusEnum.FAIL.value and self.page_step_result_model.error_message:
                self.page_step_result_model.error_message += f'--截图上传失败：{failure_reason}'
            log.warning(
                f'截图上传失败，已保留本地文件：{element_result.picture_path}，'
                f'截图名称：{element_result.picture_name}，原因：{failure_reason}'
            )
            element_result.picture_path = None
            return failure_reason
        try:
            os.remove(element_result.picture_path)
            log.debug(f'本地截图已删除：{element_result.picture_path}')
        except OSError as error:
            log.warning(f'删除本地截图失败，路径：{element_result.picture_path}，错误：{error}')
        element_result.picture_path = upload_result.path
        return None

    @staticmethod
    def _safe_file_name(file_name):
        return ''.join(i if i.isalnum() or i in ('-', '_') else '_' for i in str(file_name))

    def _refresh_progress_snapshot(self):
        self.page_step_result_model.cache_data = self.base_data.test_data.get_all()
        self.page_step_result_model.data_factory_cache_data = self.base_data.test_data.get_data_factory_all()
        self.page_step_result_model.test_object = self.test_object
        self.page_step_result_model.stop_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _should_send_progress(self, element_result: ElementResultModel | None = None, force: bool = False):
        if not self.progress_mode or not self.page_steps_model:
            return False
        current_count = len(self.page_step_result_model.element_result_list or [])
        if self.progress_mode == self.PROGRESS_MODE_PAGE_STEP_DEBUG:
            if force and current_count == self._last_progress_push_count:
                return False
            return True
        if self.progress_mode != self.PROGRESS_MODE_CASE:
            return False
        if not self.page_step_result_model.case_step_details_id:
            return False
        if force:
            return current_count != self._last_progress_push_count or current_count == 0
        if element_result and element_result.status == StatusEnum.FAIL.value:
            return True
        if current_count - self._last_progress_push_count >= self.PROGRESS_PUSH_ELEMENT_COUNT:
            return True
        elapsed = (datetime.now() - self._last_progress_push_time).total_seconds()
        return current_count > self._last_progress_push_count and elapsed >= self.PROGRESS_PUSH_INTERVAL

    async def _send_progress(self, element_result: ElementResultModel | None = None, force: bool = False):
        if not self._should_send_progress(element_result, force):
            return
        self._refresh_progress_snapshot()
        current_count = len(self.page_step_result_model.element_result_list or [])
        self._progress_sequence += 1
        self.page_step_result_model.progress_sequence = self._progress_sequence
        progress_model = copy.deepcopy(self.page_step_result_model)
        if force:
            progress_model.is_final = True
        else:
            progress_model.status = TaskEnum.PROCEED.value
            progress_model.is_final = False
        await self._persist_executor_task_progress(progress_model, element_result)
        try:
            await socket_conn.async_send(
                msg=f'UI-步骤【{self.page_steps_model.name}】实时结果已更新',
                code=200 if progress_model.status else 300,
                is_notice=ClientTypeEnum.WEB,
                func_name=ActuatorUiEventEnum.PAGE_STEPS.value,
                func_args=progress_model,
                user=self.progress_user,
                reliable=True,
            )
            self._last_progress_push_count = current_count
            self._last_progress_push_time = datetime.now()
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/page_steps:_send_progress')
            log.warning(
                f'UI步骤实时结果推送失败，不影响执行，步骤ID：{self.page_steps_model.id}，'
                f'元素数量：{current_count}，失败详情：{error}'
            )

    async def _persist_executor_task_progress(
            self,
            progress_model,
            element_result: ElementResultModel | None,
    ) -> None:
        from src.tools.executor_task_context import get_executor_task_context

        task_id, connection_id = get_executor_task_context()
        if task_id is None:
            return
        current = len(progress_model.element_result_list or [])
        total = len(self.page_steps_model.element_list or []) if self.page_steps_model else 0
        current_node_id = None
        if element_result is not None:
            current_node_id = (
                getattr(element_result, 'page_step_detail_id', None)
                or getattr(element_result, 'element_id', None)
                or getattr(element_result, 'id', None)
            )
        try:
            await HTTP.actuator_tasks.progress(
                task_id,
                {
                    'percent': min(100, int(current * 100 / total)) if total else None,
                    'current': current,
                    'total': total,
                    'message': f'已执行 {current}/{total} 个节点' if total else '步骤正在执行',
                    'current_node_id': current_node_id,
                },
                connection_id=connection_id,
            )
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/page_steps:_persist_executor_task_progress')
            # 进度写入失败不能中断浏览器操作；心跳工作器仍会发现租约异常并终止任务。
            log.warning(
                f'执行器任务进度保存失败，不影响当前节点执行：task_id={task_id}，error={error}'
            )

    async def _send_node_progress(self, element_result: ElementResultModel) -> None:
        if (
            self.progress_mode != self.PROGRESS_MODE_CASE
            or not self.page_step_result_model.case_step_details_id
        ):
            return
        try:
            await socket_conn.async_send(
                msg=f'UI-步骤【{self.page_steps_model.name}】节点进度已更新',
                code=200 if element_result.status else 300,
                is_notice=ClientTypeEnum.WEB,
                func_name=ActuatorUiEventEnum.PAGE_STEP_NODE_PROGRESS.value,
                func_args={
                    'execution_id': self.page_step_result_model.execution_id,
                    'id': self.page_step_result_model.id,
                    'case_step_details_id': self.page_step_result_model.case_step_details_id,
                    'slot_id': self.page_step_result_model.slot_id,
                    'executor_connection_id': self.page_step_result_model.executor_connection_id,
                    'element_result': element_result,
                    'completed_count': len(
                        self.page_step_result_model.element_result_list or []
                    ),
                },
                user=self.progress_user,
            )
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/page_steps:_send_node_progress')
            log.warning(
                f'UI步骤节点进度推送失败，不影响执行，步骤ID：{self.page_steps_model.id}，'
                f'失败详情：{error}'
            )

    async def _open_web_device(self, element_ope: AsyncElement):
        target_url = self._resolve_step_url()
        force_switch_url = self._should_force_step_url()
        if self.page_steps_model.type == DriveTypeEnum.WEB.value and force_switch_url:
            await self._ensure_web_page()
            send_global_msg(f'UI-准备切换到步骤URL：{target_url}')
            try:
                await element_ope.w_goto(target_url)
            except MangoAutomationError:
                if self.base_data.context is not None and self.base_data.page is not None:
                    raise
                send_global_msg('UI-浏览器Page已关闭，正在重建后重新打开步骤URL')
                self.base_data.url = target_url
                await self._ensure_web_page()
                await element_ope.w_goto(target_url)
            current_url = self.base_data.page.url if self.base_data.page else target_url
            send_global_msg(f'UI-已切换到步骤URL：{current_url}')
            return
        try:
            await element_ope.open_device(False)
        except MangoAutomationError:
            if self.page_steps_model.type != DriveTypeEnum.WEB.value:
                raise
            if self.base_data.context is not None and self.base_data.page is not None:
                raise
            send_global_msg('UI-浏览器Page已关闭，正在重建后重新打开URL')
            self.base_data.url = target_url
            await self._ensure_web_page()
            await element_ope.open_device(False)

    def _resolve_test_target(self) -> str:
        environment = self.page_steps_model.environment_config
        return resolve_test_target(environment.test_object_value, getattr(environment, 'target_config', None),
                                   self.base_data.test_data.get_cache)

    def _resolve_step_url(self) -> str:
        raw_url = urljoin(
            self._resolve_test_target(),
            self.page_steps_model.url,
        )
        try:
            target_url = self.base_data.test_data.replace(raw_url)
        except MangoToolsError as error:
            parsed_url = parse.urlsplit(raw_url)
            target_url = parse.urlunsplit((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                '',
                parsed_url.fragment,
            ))
            log.warning(
                f'步骤URL参数替换失败，改用无查询参数地址：'
                f'raw={raw_url}，target={target_url}，error={error.msg}'
            )
            send_global_msg(f'UI-步骤URL参数未完成替换，改用无参数地址：{target_url}')
        self.base_data.url = str(target_url)
        self.test_object = self.base_data.url
        return self.base_data.url

    def _should_force_step_url(self) -> bool:
        if self.progress_mode == self.PROGRESS_MODE_PAGE_STEP_DEBUG:
            return False
        return bool(self.page_steps_model.switch_step_open_url)

    async def _steps_retry(self):
        match self.page_steps_model.type:
            case DriveTypeEnum.WEB.value:
                send_global_msg(f'UI-开始重试，正在刷新浏览器')
                if self.base_data.page:
                    try:
                        await self.base_data.page.reload(wait_until="domcontentloaded", timeout=20000)
                    except TimeoutError:
                        await self.base_data.page.reload(wait_until="load", timeout=10000)
            case DriveTypeEnum.ANDROID.value:
                pass
            case DriveTypeEnum.IOS.value:
                if self.base_data.ios and self.base_data.bundle_id:
                    self.base_data.ios.terminate_app(self.base_data.bundle_id)
                    self.base_data.ios.activate_app(self.base_data.bundle_id)
            case DriveTypeEnum.DESKTOP.value:
                pass
            case _:
                log.error('自动化类型不存在，请联系管理员检查！')

    async def driver_init(self):
        match self.page_steps_model.type:
            case DriveTypeEnum.WEB.value:
                await self.web_init()
            case DriveTypeEnum.ANDROID.value:
                await self.android_init()
            case DriveTypeEnum.IOS.value:
                await self.ios_init()
            case DriveTypeEnum.DESKTOP.value:
                self.desktop_init()
            case _:
                log.error('自动化类型不存在，请联系管理员检查！')

    async def web_init(self, is_recording: bool = False, host_list: list | None = None):
        send_global_msg(f'UI-开始初始化WEB设备')
        if is_recording and host_list:
            self.web_runtime.is_header_intercept = True
            self.web_runtime.wen_intercept_request = partial(self.__intercept_request, self)
            self.web_runtime.wen_recording_api = self.__send_recording_api
            self.host_list = host_list
        else:
            self.base_data.url = urljoin(self._resolve_test_target(),
                                         self.page_steps_model.url)
            self.test_object = self.base_data.url
            if self._should_force_step_url():
                send_global_msg(f'UI-步骤切换URL：{self.base_data.url}')
        try:
            await self._ensure_web_page()
        except TargetClosedError as error:
            self.base_data.setup()
            self.page_step_result_model.status = StatusEnum.FAIL.value
            self.page_step_result_model.error_message = error.message
            log.error(f'浏览器异常关闭-1，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
            raise UiError(*ERROR_MSG_0010)

    async def _ensure_web_page(self):
        owner_type = self.progress_mode or "page_step"
        owner_id = getattr(self.base_data, "_runtime_session_id", None) or getattr(self.page_steps_model, "id", None)
        await AutomationSessionManager.ensure_web_page(
            self.base_data,
            self.web_runtime,
            owner_type=owner_type,
            owner_id=owner_id,
            purpose=f"{owner_type}:{getattr(self.page_steps_model, 'name', '') or '-'}",
        )

    async def android_init(self):
        package_name = self._resolve_test_target()
        self.base_data.package_name = package_name
        self.test_object = self.base_data.url
        send_global_msg(f'UI-开始初始化安卓设备：{self.base_data.package_name}')
        owner = getattr(self.base_data, "_runtime_session_id", None) or f"base:{id(self.base_data)}"
        await AutomationSessionManager.acquire_android(
            self.base_data,
            SetConfig.get_and_equipment(),  # type: ignore
            package_name,
            owner,
        )

    async def ios_init(self):
        bundle_id = self._resolve_test_target()
        self.base_data.bundle_id = bundle_id
        self.test_object = bundle_id
        owner = getattr(self.base_data, '_runtime_session_id', None) or f'base:{id(self.base_data)}'
        capabilities = {
            'platformName': 'iOS',
            'appium:automationName': 'XCUITest',
            'appium:deviceName': SetConfig.get_ios_device_name(),  # type: ignore
            'appium:bundleId': bundle_id,
            'appium:noReset': True,
            'appium:newCommandTimeout': 300,
        }
        optional = {
            'appium:udid': SetConfig.get_ios_udid(),  # type: ignore
            'appium:platformVersion': SetConfig.get_ios_platform_version(),  # type: ignore
            'appium:xcodeOrgId': SetConfig.get_ios_xcode_org_id(),  # type: ignore
            'appium:updatedWDABundleId': SetConfig.get_ios_wda_bundle_id(),  # type: ignore
        }
        capabilities.update({key: value for key, value in optional.items() if value})
        send_global_msg(f'UI-开始初始化iOS设备：{capabilities["appium:deviceName"]}')
        await AutomationSessionManager.acquire_ios(
            self.base_data,
            SetConfig.get_ios_appium_url(),  # type: ignore
            capabilities,
            owner,
        )

    def desktop_init(self, ):
        send_global_msg(f'UI-开始初始化PC设备')

    async def __intercept_request(self, obj, route: Route, request: Request):
        if self.host_list is None:
            await route.continue_()
            return
        if request.resource_type in ("document", "xhr", "fetch"):
            for host_dict in self.host_list:
                if host_dict.get('value') in request.url:
                    send_global_msg(f'UI-设置拦截API成功，接口会写入到的产品ID：{host_dict.get("project_product_id")}')
                    await self.__send_recording_api(request, host_dict.get('project_product_id'))
        await route.continue_()

    @classmethod
    @async_error_handle()
    async def __send_recording_api(cls, request: Request, project_product: int):
        parsed_url = parse.urlsplit(request.url)
        try:
            json_data = request.post_data_json
        except Error:
            json_data = None
        data = {key: value[0] for key, value in
                parse.parse_qs(request.post_data).items()} if json_data is None else None
        params = {key: value[0] for key, value in
                  parse.parse_qs(parsed_url.query).items()} if parsed_url.query else None
        api_info = ApiRecordingContract(
            project_product=project_product,
            username=SetConfig.get_username(),  # type: ignore
            type=ApiTypeEnum.batch.value,
            name=parsed_url.path,
            client=ClientEnum.WEB.value,
            url=parsed_url.path,
            method=MethodEnum.get_key(request.method),
            params=None if params == {} or params is None else json.dumps(params, ensure_ascii=False),
            data=None if data == {} or data is None else json.dumps(data, ensure_ascii=False),
            json=None if json_data == {} or json_data is None else json.dumps(json_data, ensure_ascii=False)
        )
        await socket_conn.async_send(
            msg="发送录制接口",
            func_name=ActuatorApiEventEnum.RECORDING_API.value,
            func_args=api_info
        )
        send_global_msg(f'UI-发送接口信息成功，URL：{parsed_url.path}')
