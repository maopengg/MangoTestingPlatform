from __future__ import annotations

import logging
from pathlib import Path

BUSINESS_LOGGER_NAMES = (
    "api",
    "ui",
    "system",
    "data_producer",
    "perf",
    "pytest",
    "monitoring",
    "user",
    "src",
)
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class ServiceContextFilter(logging.Filter):
    def __init__(self, service: str, instance: str):
        super().__init__()
        self.service = service
        self.instance = instance

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self.service
        record.instance = self.instance
        return True


def normalize_log_level(value: str | None, *, debug_default: bool = False) -> str:
    level = str(value or "").strip().upper()
    if not level:
        return "DEBUG" if debug_default else "INFO"
    if level not in VALID_LOG_LEVELS:
        allowed = ", ".join(sorted(VALID_LOG_LEVELS))
        raise ValueError(f"MANGO_LOG_LEVEL 仅支持: {allowed}")
    return level


def build_logging_config(
        *,
        service_name: str,
        service_instance: str,
        service_log_dir: Path,
        business_level: str,
        access_log_level: str,
        max_bytes: int,
        backup_count: int,
        django_backup_count: int,
) -> dict:
    service_log_dir.mkdir(parents=True, exist_ok=True)
    business_logger = {
        "handlers": ["service_file", "error_file", "console"],
        "level": business_level,
        "propagate": False,
    }
    loggers = {name: dict(business_logger) for name in BUSINESS_LOGGER_NAMES}
    loggers.update({
        "console": {
            "handlers": ["console"],
            "level": business_level,
            "propagate": False,
        },
        "django": {
            "handlers": ["django"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["django"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": access_log_level,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": access_log_level,
            "propagate": False,
        },
        "apscheduler": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apscheduler.executors.default": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    })
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "service_context": {
                "()": "src.common.logging.config.ServiceContextFilter",
                "service": service_name,
                "instance": service_instance,
            },
        },
        "formatters": {
            "colored": {
                "()": "colorlog.ColoredFormatter",
                "format": (
                    "%(log_color)s[%(asctime)s] [%(levelname)s] [%(service)s] "
                    "[%(instance)s] [%(name)s] %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "purple",
                },
            },
            "verbose": {
                "format": (
                    "[%(asctime)s] [%(levelname)s] [%(service)s] [%(instance)s] "
                    "[%(name)s] %(filename)s:%(lineno)d %(process)d %(thread)d %(message)s"
                ),
            },
            "standard": {
                "format": (
                    "[%(asctime)s] [%(levelname)s] [%(service)s] [%(instance)s] "
                    "[%(name)s] %(filename)s:%(lineno)d %(message)s"
                ),
            },
        },
        "handlers": {
            "console": {
                "level": business_level,
                "class": "logging.StreamHandler",
                "formatter": "colored",
                "filters": ["service_context"],
            },
            "service_file": {
                "level": business_level,
                "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
                "filename": str(service_log_dir / "app.log"),
                "formatter": "verbose",
                "filters": ["service_context"],
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            },
            "error_file": {
                "level": "ERROR",
                "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
                "filename": str(service_log_dir / "error.log"),
                "formatter": "verbose",
                "filters": ["service_context"],
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            },
            "django": {
                "level": "WARNING",
                "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
                "filename": str(service_log_dir / "django.log"),
                "formatter": "standard",
                "filters": ["service_context"],
                "maxBytes": max_bytes,
                "backupCount": django_backup_count,
                "encoding": "utf-8",
            },
        },
        "loggers": loggers,
    }


__all__ = [
    "BUSINESS_LOGGER_NAMES",
    "ServiceContextFilter",
    "build_logging_config",
    "normalize_log_level",
]
