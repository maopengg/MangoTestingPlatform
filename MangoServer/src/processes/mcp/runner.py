from threading import Event, Thread

import uvicorn

from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventSource
from src.common.decorators.system_error import system_error_guard
from src.processes.server_logging import access_log_enabled

MCP_ASGI_APPLICATION = 'src.processes.mcp.asgi:application'


@system_error_guard(
    source=SystemErrorEventSource.MCP,
    request_path='run_mcp_service',
    service_name=RuntimeServiceName.MCP,
)
def run_mcp_service(host: str, port: int, workers: int = 1):
    stop_event = Event()
    thread = Thread(target=_heartbeat_loop, args=(host, port, workers, stop_event), daemon=True)
    thread.start()
    try:
        uvicorn.run(
            MCP_ASGI_APPLICATION,
            host=host,
            port=port,
            workers=max(workers, 1),
            access_log=access_log_enabled(),
        )
    finally:
        stop_event.set()


def _heartbeat_loop(host: str, port: int, workers: int, stop_event: Event):
    from src.apps.data_factory.services.pool_maintenance import DatasourcePoolMaintenance
    while not stop_event.is_set():
        ServiceHeartbeatService.beat(
            RuntimeServiceName.MCP,
            metadata={
                'host': host,
                'port': port,
                'workers': workers,
                # 多 worker 父进程不能证明子进程连接池健康，明确返回未核实。
                'datasource_maintenance_healthy': DatasourcePoolMaintenance.healthy() if workers == 1 else None,
            },
        )
        stop_event.wait(15)
