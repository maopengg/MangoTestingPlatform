# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-20 20:30
# @Author : 毛鹏
import asyncio
import traceback

from src.services.ui.case_flow import CaseFlow
from src.tools.set_config import SetConfig
from .consumer import SocketConsumer
from .network.web_socket import WebSocketClient, socket_conn
from .services.pytest.case_flow import PytestCaseFlow
from .services.runtime import RuntimeSupervisor
from .services.executor_task_worker import ExecutorTaskWorker
from .services.system_error_reporter import ActuatorSystemErrorReporter
from .tools import project_dir
from .tools.log_collector import log


async def process(parent, is_login=False, retry=0):
    try:
        WebSocketClient.parent = parent
        SocketConsumer.parent = parent
        CaseFlow.parent = parent
        PytestCaseFlow.parent = parent
        from src.network import HTTP
        HTTP.refresh()
        if is_login:
            login_response = await HTTP.system.login(
                SetConfig.get_username(),
                SetConfig.get_login_password(),
                is_retry=True
            )
            if login_response.code != 200:
                raise RuntimeError(f'执行器登录失败：{login_response.msg}')
        try:
            await HTTP.system.refresh_runtime_config()
        except Exception as error:
            log.warning(f'启动时刷新执行器运行配置失败，将使用默认值并后台重试：{error}')
        RuntimeSupervisor.start_task('websocket_client', WebSocketClient.client_run)
        RuntimeSupervisor.start_task('socket_consumer', SocketConsumer.process_tasks)
        RuntimeSupervisor.start_task('executor_task_worker', ExecutorTaskWorker.run)
        RuntimeSupervisor.start_task('ui_case_flow', CaseFlow.process_tasks)
        RuntimeSupervisor.start_task('pytest_case_flow', PytestCaseFlow.process_tasks)
        retry = 0
    except Exception as error:
        await RuntimeSupervisor.stop()
        if socket_conn.websocket:
            socket_conn.websocket = None
        traceback.print_exc()
        log.error(f"启动永久循环协程任务时出现异常：{error}")
        await asyncio.sleep(5)
        if retry >= 20:
            await ActuatorSystemErrorReporter.report(
                error,
                'startup:process',
                traceback_text=traceback.format_exc(),
            )
            raise error
        else:
            await process(parent, is_login=is_login, retry=retry + 1)


async def test_process(parent):
    try:
        SocketConsumer.parent = parent
        CaseFlow.parent = parent
        PytestCaseFlow.parent = parent
        RuntimeSupervisor.start_task('socket_consumer', SocketConsumer.process_tasks)
        RuntimeSupervisor.start_task('executor_task_worker', ExecutorTaskWorker.run)
        RuntimeSupervisor.start_task('ui_case_flow', CaseFlow.process_tasks)
        RuntimeSupervisor.start_task('pytest_case_flow', PytestCaseFlow.process_tasks)
    except Exception as error:
        await RuntimeSupervisor.stop()
        if socket_conn.websocket:
            socket_conn.websocket = None
        traceback.print_exc()
        log.error(f"启动永久循环协程任务时出现异常：{error}")
        await asyncio.sleep(5)
        await test_process(parent)
