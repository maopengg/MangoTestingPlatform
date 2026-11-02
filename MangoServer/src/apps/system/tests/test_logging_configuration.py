import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from src.common.logging.config import build_logging_config, normalize_log_level
from src.common.logging.facade import DomainLogger


class CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class LoggingConfigurationTests(SimpleTestCase):

    def test_service_logging_keeps_three_file_layout_and_module_logger(self):
        with TemporaryDirectory() as directory:
            config = build_logging_config(
                service_name="api-worker",
                service_instance="api-worker-1",
                service_log_dir=Path(directory),
                business_level="DEBUG",
                access_log_level="INFO",
                max_bytes=4096,
                backup_count=3,
                django_backup_count=2,
            )

        self.assertEqual("DEBUG", config["handlers"]["service_file"]["level"])
        self.assertEqual("ERROR", config["handlers"]["error_file"]["level"])
        self.assertEqual("WARNING", config["handlers"]["django"]["level"])
        self.assertEqual(
            "concurrent_log_handler.ConcurrentRotatingFileHandler",
            config["handlers"]["service_file"]["class"],
        )
        self.assertEqual(["service_file", "error_file", "console"], config["loggers"]["src"]["handlers"])
        self.assertEqual("DEBUG", config["loggers"]["src"]["level"])

    def test_default_log_level_tracks_debug_mode_and_rejects_invalid_value(self):
        self.assertEqual("DEBUG", normalize_log_level(None, debug_default=True))
        self.assertEqual("INFO", normalize_log_level(None, debug_default=False))
        self.assertEqual("WARNING", normalize_log_level("warning"))
        with self.assertRaises(ValueError):
            normalize_log_level("verbose")

    def test_domain_facade_preserves_business_call_site_and_format_arguments(self):
        logger = logging.getLogger("logging-callsite-test")
        old_handlers = list(logger.handlers)
        old_level = logger.level
        old_propagate = logger.propagate
        capture = CaptureHandler()
        logger.handlers = [capture]
        logger.setLevel(logging.INFO)
        logger.propagate = False
        self.addCleanup(setattr, logger, "handlers", old_handlers)
        self.addCleanup(logger.setLevel, old_level)
        self.addCleanup(setattr, logger, "propagate", old_propagate)

        domain_logger = DomainLogger("logging-callsite-test")
        domain_logger.info("执行任务 %s", 12)

        self.assertEqual(1, len(capture.records))
        record = capture.records[0]
        self.assertEqual(__file__, record.pathname)
        self.assertEqual("执行任务 12", record.getMessage())

    def test_domain_facade_supports_exception_logging(self):
        logger = logging.getLogger("logging-exception-test")
        old_handlers = list(logger.handlers)
        old_level = logger.level
        old_propagate = logger.propagate
        capture = CaptureHandler()
        logger.handlers = [capture]
        logger.setLevel(logging.ERROR)
        logger.propagate = False
        self.addCleanup(setattr, logger, "handlers", old_handlers)
        self.addCleanup(logger.setLevel, old_level)
        self.addCleanup(setattr, logger, "propagate", old_propagate)

        domain_logger = DomainLogger("logging-exception-test")
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            domain_logger.exception("处理失败")

        self.assertIsNotNone(capture.records[0].exc_info)
