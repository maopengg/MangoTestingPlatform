from enum import Enum


class SystemErrorEventSource(str, Enum):
    HTTP = "http"
    DRF = "drf"
    SCHEDULER = "scheduler"
    API_WORKER = "api-worker"
    MCP = "mcp"
    REALTIME = "realtime"
    MONITORING = "monitoring"
    PERFORMANCE = "performance"
    ACTUATOR = "actuator"
    FRONTEND = "frontend"
