from enum import IntEnum, Enum

from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum


class ApiCaseTraceSourceType(IntEnum):
    TEST_SUITE = 1
    TIMING_TASK = 2
    MCP = 3
    SINGLE_CASE = 4
    DEBUG_CASE = 5
    OTHER = 6


class ApiCaseTraceStatus(IntEnum):
    FAIL = StatusEnum.FAIL.value
    SUCCESS = StatusEnum.SUCCESS.value
    STAY_BEGIN = TaskEnum.STAY_BEGIN.value
    PROCEED = TaskEnum.PROCEED.value
    CLEANUP_FAIL = 4
    SKIP = 5


class ApiCaseTraceStepType(str, Enum):
    CASE_START = "case_start"
    GLOBAL_VARIABLES = "global_variables"
    CASE_FRONT = "case_front"
    GRAY_CONFIG = "gray_config"
    PARAMETERIZE = "parameterize"
    SCENARIO = "scenario"
    RETRY_ROUND = "retry_round"
    RETRY_WAIT = "retry_wait"
    DATA_FACTORY_FRONT = "data_factory_front"
    FRONT_PROCESS = "front_process"
    REQUEST = "request"
    MCP_CONNECT = "mcp_connect"
    MCP_TOOL_CALL = "mcp_tool_call"
    MCP_CLOSE = "mcp_close"
    GRPC_CHANNEL_INIT = "grpc_channel_init"
    GRPC_CALL = "grpc_call"
    GRPC_CHANNEL_CLOSE = "grpc_channel_close"
    WEBSOCKET_CONNECT = "websocket_connect"
    WEBSOCKET_MESSAGE = "websocket_message"
    WEBSOCKET_CLOSE = "websocket_close"
    POSTERIOR = "posterior"
    ASSERTION = "assertion"
    DATA_FACTORY_CLEANUP = "data_factory_cleanup"
    CASE_POSTERIOR = "case_posterior"
    REPORT_WRITE = "report_write"
    CASE_FINISH = "case_finish"
    SKIPPED = "skipped"
