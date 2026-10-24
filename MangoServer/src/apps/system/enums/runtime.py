from enum import Enum


class RuntimeServiceName(str, Enum):
    CORE_API = "core-api"
    SCHEDULER = "scheduler-service"
    API_WORKER = "api-worker"
    MCP = "mcp-service"
    REALTIME = "realtime-service"
    MONITORING = "monitoring-service"
    ACTUATOR = "actuator"
