import os
import sys


LIVE_STREAM_UNSUPPORTED_MESSAGE = "当前执行器显示环境不可用，请检查Xvfb启动日志及DISPLAY配置"


def is_live_stream_supported() -> bool:
    if not sys.platform.startswith("linux"):
        return True
    if os.environ.get("ACTUATOR_LIVE_STREAM_SUPPORTED") == "0":
        return False
    return bool(os.environ.get("DISPLAY"))


def is_web_live_stream_supported() -> bool:
    return is_live_stream_supported()


def ensure_live_stream_supported() -> None:
    if not is_live_stream_supported():
        raise RuntimeError(LIVE_STREAM_UNSUPPORTED_MESSAGE)
