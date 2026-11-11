"""隔离SIGTERM回归夹具：不调用MCP业务工具、不访问数据库。"""
import asyncio
import json
import os
import sys
import time
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
import django
django.setup()

import uvicorn
from src.apps.system.services.runtime_center.mcp_execution import McpExecutionLifecycle as Lifecycle
from src.apps.system.exceptions import SystemError
from src.processes.mcp.runner import DrainingMcpServer


def execute():
    with Lifecycle.admit():
        time.sleep(0.8)  # 模拟完整同步执行及后置清理。


async def application(scope, receive, send):
    if scope['type'] != 'http':
        return
    status, body = 200, b'done'
    if scope['path'] == '/state':
        body = json.dumps({'active': Lifecycle.snapshot()['active_tools']}).encode()
    else:
        try:
            await asyncio.to_thread(execute)
        except SystemError:
            status, body = 503, b'not-started'
    await send({'type': 'http.response.start', 'status': status, 'headers': []})
    await send({'type': 'http.response.body', 'body': body})


def heartbeat(*args, **kwargs):
    if kwargs.get('status') == 0:
        print('DRAINED_AFTER_EXECUTION', flush=True)


if __name__ == '__main__':
    with patch('src.apps.system.services.runtime_center.heartbeat.ServiceHeartbeatService.beat', side_effect=heartbeat):
        DrainingMcpServer(uvicorn.Config(application, host='127.0.0.1', port=int(sys.argv[1]),
            lifespan='off', access_log=False, log_level='error')).run()
