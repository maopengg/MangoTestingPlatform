# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
import asyncio

from src.models.system_model import CmdTestModel
from src.network import ActuatorToolsEventEnum, socket_conn
from mangotools.enums import ClientTypeEnum
from mangotools.enums import TestCaseTypeEnum
from src.settings import settings
from src.tools.set_config import SetConfig
from src.services.ui.live_stream.environment import is_web_live_stream_supported
from src.tools.command.command import run_command
from src.tools.decorator.convert_args import convert_args
from src.tools.decorator.error_handle import async_error_handle
from src.tools.log_collector import log


class Tools:
    SERVER_CONFIG_FIELDS = {
        'host': (SetConfig.get_host, SetConfig.set_host),
        'ws': (SetConfig.get_ws, SetConfig.set_ws),
        'proxy_url': (SetConfig.get_proxy_url, SetConfig.set_proxy_url),
        'username': (SetConfig.get_username, SetConfig.set_username),
    }
    UI_CONFIG_FIELDS = {
        'web_type': (SetConfig.get_web_type, SetConfig.set_web_type),
        'web_path': (SetConfig.get_web_path, SetConfig.set_web_path),
        'web_parallel': (SetConfig.get_web_parallel, SetConfig.set_web_parallel),
        'ui_queue_size': (SetConfig.get_ui_queue_size, SetConfig.set_ui_queue_size),
        'web_h5': (SetConfig.get_web_h5, SetConfig.set_web_h5),
        'web_max': (SetConfig.get_web_max, SetConfig.set_web_max),
        'web_recording': (SetConfig.get_web_recording, SetConfig.set_web_recording),
        'web_headers': (SetConfig.get_web_headers, SetConfig.set_web_headers),
        'web_step_screenshot': (SetConfig.get_web_step_screenshot, SetConfig.set_web_step_screenshot),
        'web_static_cache_enabled': (
            SetConfig.get_web_static_cache_enabled,
            SetConfig.set_web_static_cache_enabled,
        ),
        'web_static_cache_path': (SetConfig.get_web_static_cache_path, SetConfig.set_web_static_cache_path),
    }
    PYTEST_CONFIG_FIELDS = {
        'pytest_parallel': (SetConfig.get_pytest_parallel, SetConfig.set_pytest_parallel),
        'pytest_queue_size': (SetConfig.get_pytest_queue_size, SetConfig.set_pytest_queue_size),
    }

    @classmethod
    @async_error_handle()
    @convert_args(CmdTestModel)
    async def t_mango_pytest(cls, data: CmdTestModel):
        for cmd in data.cmd:
            output, error = run_command(cmd)
            if output:
                log.info(f'命令执行输出：{output}')
            if error:
                log.error(f'命令执行错误：{error}')

    @classmethod
    @async_error_handle()
    @convert_args(dict)
    async def t_set_open_status(cls, data):
        log.debug(f'设置open状态：{data.get("is_open")}')
        SetConfig.set_open_status(data.get('is_open'))

    @classmethod
    @async_error_handle()
    @convert_args(dict)
    async def t_set_debug(cls, data):
        log.debug(f'设置debug状态：{data.get("debug")}')
        settings.IS_DEBUG = data.get('debug')
        log.set_debug(settings.IS_DEBUG)

    @classmethod
    @async_error_handle()
    @convert_args(dict)
    async def t_refresh_method_options(cls, data):
        from src.customization import func_info

        await socket_conn.async_send(
            '刷新执行器方法缓存成功',
            func_name=ActuatorToolsEventEnum.SET_OPERATION_OPTIONS.value,
            is_notice=ClientTypeEnum.WEB,
            func_args={'version': settings.SETTINGS.get('version'), 'data': func_info}
        )

    @classmethod
    @async_error_handle()
    @convert_args(dict)
    async def t_task_available(cls, data):
        from src.services.executor_task_worker import ExecutorTaskWorker
        ExecutorTaskWorker.wake()
        task_type = data.get('task_type') or data.get('type')
        if task_type in ('ui', TestCaseTypeEnum.UI.value):
            from src.services.ui.case_flow import CaseFlow
            CaseFlow.wake_pull()
            log.debug('收到UI任务可拉取通知')
        elif task_type in ('pytest', TestCaseTypeEnum.PYTEST.value):
            from src.services.pytest.case_flow import PytestCaseFlow
            PytestCaseFlow.wake_pull()
            log.debug('收到Pytest任务可拉取通知')

    @classmethod
    @async_error_handle()
    @convert_args(dict)
    async def t_stop_test_suite(cls, data):
        test_suite_id = int(data.get('test_suite_id'))
        from src.services.pytest.case_flow import PytestCaseFlow
        from src.services.ui.case_flow import CaseFlow

        ui_result, pytest_result = await asyncio.gather(
            CaseFlow.cancel_test_suite(test_suite_id),
            PytestCaseFlow.cancel_test_suite(test_suite_id),
        )
        log.info(
            f'已停止测试报告本地任务：test_suite={test_suite_id}, '
            f'ui={ui_result}, pytest={pytest_result}'
        )

    @classmethod
    @async_error_handle()
    @convert_args(dict)
    async def t_get_actuator_config(cls, data):
        request_id = data.get('request_id')
        result = {
            'request_id': request_id,
            'username': SetConfig.get_username(),
            'status': True,
            'config': cls._collect_actuator_config(),
        }
        await socket_conn.async_send(
            '执行器配置读取完成',
            func_name=ActuatorToolsEventEnum.SET_ACTUATOR_CONFIG_SNAPSHOT.value,
            is_notice=ClientTypeEnum.WEB,
            func_args=result,
        )
        return result

    @classmethod
    @async_error_handle()
    @convert_args(dict)
    async def t_update_actuator_config(cls, data):
        request_id = data.get('request_id')
        try:
            cls._apply_actuator_config(data.get('config') or {})
            config = cls._collect_actuator_config()
            status = True
            message = '执行器配置保存成功'
        except Exception as error:
            config = cls._collect_actuator_config()
            status = False
            message = f'执行器配置保存失败：{error}'
            log.error(message)
        result = {
            'request_id': request_id,
            'username': SetConfig.get_username(),
            'status': status,
            'message': message,
            'config': config,
        }
        await socket_conn.async_send(
            message,
            func_name=ActuatorToolsEventEnum.SET_ACTUATOR_CONFIG_SAVE_RESULT.value,
            is_notice=ClientTypeEnum.WEB,
            func_args=result,
        )
        return result

    @classmethod
    def _collect_actuator_config(cls):
        return {
            'server': cls._collect_config_group(cls.SERVER_CONFIG_FIELDS),
            'ui': cls._collect_config_group(cls.UI_CONFIG_FIELDS),
            'pytest': cls._collect_config_group(cls.PYTEST_CONFIG_FIELDS),
            'runtime': {
                'is_open': settings.IS_OPEN,
                'debug': settings.IS_DEBUG,
                'web_live_stream_supported': is_web_live_stream_supported(),
            },
        }

    @staticmethod
    def _collect_config_group(fields):
        config = {}
        for key, (getter, _) in fields.items():
            config[key] = getter()
        return config

    @classmethod
    def _apply_actuator_config(cls, config: dict):
        cls._apply_config_group(config.get('server') or {}, cls.SERVER_CONFIG_FIELDS)
        cls._apply_config_group(config.get('ui') or {}, cls.UI_CONFIG_FIELDS)
        cls._apply_config_group(config.get('pytest') or {}, cls.PYTEST_CONFIG_FIELDS)
        runtime_config = config.get('runtime') or {}
        if 'is_open' in runtime_config:
            SetConfig.set_open_status(runtime_config.get('is_open'))
        if 'debug' in runtime_config:
            settings.IS_DEBUG = bool(runtime_config.get('debug'))
            log.set_debug(settings.IS_DEBUG)

    @staticmethod
    def _apply_config_group(config: dict, fields):
        for key, value in config.items():
            field = fields.get(key)
            if not field:
                continue
            _, setter = field
            setter(value)
