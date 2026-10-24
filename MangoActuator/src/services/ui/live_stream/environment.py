import os
import sys


LIVE_STREAM_UNSUPPORTED_MESSAGE = "当前容器不支持直播画面，请安装Xvfb"


def is_live_stream_supported() -> bool:
    if not sys.platform.startswith("linux"):
        return True
    if os.environ.get("ACTUATOR_LIVE_STREAM_SUPPORTED") == "1":
        return True
    if os.environ.get("DISPLAY"):
        return True
    return False


def is_web_live_stream_supported() -> bool:
    return is_live_stream_supported()


def ensure_live_stream_supported() -> None:
    if not is_live_stream_supported():
        raise RuntimeError(LIVE_STREAM_UNSUPPORTED_MESSAGE)
