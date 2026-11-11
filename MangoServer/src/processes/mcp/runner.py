from threading import Event, Thread
import os
import socket
import asyncio

import uvicorn

from src.apps.system.enums import RuntimeServiceName
from src.common.enums.system_error import SystemErrorEventSource
from src.common.decorators.system_error import system_error_guard
from src.processes.server_logging import access_log_enabled

MCP_ASGI_APPLICATION = 'src.processes.mcp.asgi:application'


class DrainingMcpServer(uvicorn.Server):
    def handle_exit(self, sig, frame):
        from src.apps.system.services.runtime_center.mcp_execution import McpExecutionLifecycle
        McpExecutionLifecycle.begin_drain()

    async def on_tick(self, counter):
        from src.apps.system.services.runtime_center.mcp_execution import McpExecutionLifecycle
        exiting = await super().on_tick(counter)
        draining = McpExecutionLifecycle.should_exit()
        if draining and McpExecutionLifecycle.snapshot()['active_tools'] == 0:
            from src.apps.data_factory.services.pool_maintenance import DatasourcePoolMaintenance
            await asyncio.to_thread(DatasourcePoolMaintenance.close_idle_pools)
            # Uvicorn退出后会重新抛出SIGTERM，不能只依赖run的finally保存证据。
            await asyncio.to_thread(McpExecutionLifecycle.record_drained)
        return exiting or draining

    def run(self, sockets=None):
        import django
        from django.apps import apps
        if not apps.ready:
            django.setup()
        from src.apps.system.services.runtime_center.mcp_execution import McpExecutionLifecycle
        stop_event = Event()
        thread = Thread(target=_heartbeat_loop,
                        args=(self.config.host, self.config.port, 1, stop_event), daemon=True)
        thread.start()
        try:
            return super().run(sockets=sockets)
        finally:
            stop_event.set()
            McpExecutionLifecycle.begin_drain()
            McpExecutionLifecycle.record_drained()


@system_error_guard(
    source=SystemErrorEventSource.MCP,
    request_path='run_mcp_service',
    service_name=RuntimeServiceName.MCP,
)
def run_mcp_service(host: str, port: int, workers: int = 1):
    config = uvicorn.Config(MCP_ASGI_APPLICATION, host=host, port=port, workers=max(workers, 1),
                            access_log=access_log_enabled(), timeout_graceful_shutdown=30)
    server = DrainingMcpServer(config)
    if config.workers > 1:
        from uvicorn.supervisors import Multiprocess
        sock = config.bind_socket()
        try:
            Multiprocess(config, target=server.run, sockets=[sock]).run()
        finally:
            sock.close()
    else:
        server.run()
        if not server.started:
            from uvicorn.main import STARTUP_FAILURE
            raise SystemExit(STARTUP_FAILURE)


def _heartbeat_loop(host: str, port: int, workers: int, stop_event: Event):
    from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
    from src.apps.data_factory.services.pool_maintenance import DatasourcePoolMaintenance
    from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
    from src.apps.system.services.runtime_center.mcp_execution import McpExecutionLifecycle
    while not stop_event.is_set():
        ServiceHeartbeatService.beat(
            RuntimeServiceName.MCP,
            instance_name=(os.getenv('HOSTNAME') or socket.gethostname()) + ':' + str(os.getpid()),
            metadata={
                **RuntimeProcessIdentity.current(), **McpExecutionLifecycle.snapshot(),
                'host': host,
                'port': port,
                'workers': workers,
                # 每个子进程仅报告自己的执行与连接池状态。
                'datasource_maintenance_healthy': DatasourcePoolMaintenance.healthy(),
            },
        )
        stop_event.wait(15)
