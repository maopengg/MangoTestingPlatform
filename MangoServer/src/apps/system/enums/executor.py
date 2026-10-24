from src.common.enums.base import BaseEnum


class ExecutorTaskStatusEnum(BaseEnum):
    WAITING_EXECUTOR = "waiting_executor"
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

    @classmethod
    def terminal_values(cls) -> set[str]:
        return {
            cls.SUCCESS.value,
            cls.FAILED.value,
            cls.INTERRUPTED.value,
            cls.CANCELLED.value,
            cls.TIMEOUT.value,
        }


class ExecutorModeEnum(BaseEnum):
    SELF = "self"
    PUBLIC = "public"
    SPECIFIED = "specified"
    WORKSPACE = "workspace"


class ExecutorTaskTypeEnum(BaseEnum):
    EXECUTOR_COMMAND = "executor_command"
    LIVE_CONTROL = "live_control"
    CONFIG_COMMAND = "config_command"
    TEST_CONTROL = "test_control"
    API_EXECUTION = "api_execution"
    PYTEST_EXECUTION = "pytest_execution"
    ELEMENT_CHECK = "element_check"
    ELEMENT_DEEP_CHECK = "element_deep_check"
    ELEMENT_COLLECT = "element_collect"
    PAGE_SCAN = "page_scan"
    PAGE_OPEN = "page_open"
    PAGE_STEP_DEBUG = "page_step_debug"
    PAGE_STEP_NODE_DEBUG = "page_step_node_debug"
    UI_CASE = "ui_case"
    UI_CASE_STEP = "ui_case_step"
    AUTH_START = "auth_start"
    AUTH_CAPTURE = "auth_capture"
    RECORDING = "recording"
    PERF_EXECUTION = "perf_execution"
