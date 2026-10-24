from enum import Enum


class LiveStreamRole(str, Enum):
    PUBLISHER = "publisher"
    READY = "ready"


class LiveStreamExecutionType(str, Enum):
    UI_CASE = "ui_case"
    PAGE_STEP_DEBUG = "page_step_debug"
    ELEMENT_CHECK = "element_check"
    ELEMENT_WORKSPACE = "element_workspace"
    PAGE_STEP_WORKSPACE = "page_step_workspace"


class LiveStreamCommand(str, Enum):
    START = "u_live_stream_start"
    STOP = "u_live_stream_stop"
    WORKSPACE_START = "u_live_workspace_start"
    WORKSPACE_STOP = "u_live_workspace_stop"


class LiveStreamEvent(str, Enum):
    SUBSCRIBER_READY = "subscriber_ready"
    PUBLISHER_READY = "publisher_ready"
    STREAM_STATUS = "stream_status"
    CONTROL_REQUEST = "control_request"
    CONTROL_GRANTED = "control_granted"
    CONTROL_DENIED = "control_denied"
    CONTROL_RENEW = "control_renew"
    CONTROL_RELEASE = "control_release"
    CONTROL_EVENT = "control_event"
    CONTROL_ACK = "control_ack"
    CONTROL_STARTED = "control_started"
    CONTROL_STOPPED = "control_stopped"
    STOP_CAPTURE = "stop_capture"
    ERROR = "error"
