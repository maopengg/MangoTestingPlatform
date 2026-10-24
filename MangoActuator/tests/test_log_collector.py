import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from mangotools.log_collector._log_control import LogHandler
from src.tools.log_collector import log


class CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_log_facade_preserves_business_call_site_and_arguments():
    logger = log.INFO.logger
    old_handlers = list(logger.handlers)
    capture = CaptureHandler()
    logger.handlers = [capture]
    try:
        log.info("执行任务 %s", 12)
    finally:
        logger.handlers = old_handlers

    assert capture.records[0].pathname == __file__
    assert capture.records[0].getMessage() == "执行任务 12"


def test_log_facade_supports_exception_logging():
    logger = log.ERROR.logger
    old_handlers = list(logger.handlers)
    capture = CaptureHandler()
    logger.handlers = [capture]
    try:
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            log.exception("执行失败")
    finally:
        logger.handlers = old_handlers

    assert capture.records[0].exc_info is not None


def test_log_handler_initialization_is_idempotent():
    with TemporaryDirectory() as directory:
        filename = str(Path(directory) / "info-log.log")
        first = LogHandler(filename, "info")
        handler_count = len(first.logger.handlers)
        second = LogHandler(filename, "info")
        try:
            assert len(second.logger.handlers) == handler_count
        finally:
            for handler in list(first.logger.handlers):
                handler.close()
                first.logger.removeHandler(handler)


def test_log_handler_uses_configurable_rotation(monkeypatch):
    monkeypatch.setenv("MANGO_ACTUATOR_LOG_MAX_BYTES", "2048")
    monkeypatch.setenv("MANGO_ACTUATOR_LOG_BACKUP_COUNT", "2")
    with TemporaryDirectory() as directory:
        handler = LogHandler(str(Path(directory) / "warning-log.log"), "warning")
        try:
            file_handler = next(item for item in handler.logger.handlers if hasattr(item, "maxBytes"))
            assert file_handler.maxBytes == 2048
            assert file_handler.backupCount == 2
        finally:
            for item in list(handler.logger.handlers):
                item.close()
                handler.logger.removeHandler(item)
