import uvicorn

from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventSource
from src.common.decorators.system_error import system_error_guard
from src.processes.server_logging import access_log_enabled

REALTIME_ASGI_APPLICATION = "src.processes.realtime.asgi:application"


@system_error_guard(
    source=SystemErrorEventSource.REALTIME,
    request_path='run_realtime_service',
    service_name=RuntimeServiceName.REALTIME,
)
def run_realtime_service(host: str, port: int, workers: int = 1) -> None:
    if workers != 1:
        raise ValueError("realtime-service 当前必须使用单 ASGI Worker")
    uvicorn.run(
        REALTIME_ASGI_APPLICATION,
        host=host,
        port=port,
        workers=1,
        lifespan="on",
        access_log=access_log_enabled(),
    )
