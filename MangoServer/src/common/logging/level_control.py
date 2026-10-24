from __future__ import annotations

import logging
from pathlib import Path

from src.common.logging.config import BUSINESS_LOGGER_NAMES, normalize_log_level


def _is_app_file_handler(handler: logging.Handler) -> bool:
    filename = getattr(handler, "baseFilename", None)
    return bool(filename and Path(filename).name == "app.log")


def set_logging_level(level: str) -> str:
    normalized = normalize_log_level(level)
    numeric_level = getattr(logging, normalized)
    visited_handlers: set[int] = set()
    for name in (*BUSINESS_LOGGER_NAMES, "console"):
        logger = logging.getLogger(name)
        logger.setLevel(numeric_level)
        for handler in logger.handlers:
            identity = id(handler)
            if identity in visited_handlers:
                continue
            visited_handlers.add(identity)
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(numeric_level)
            elif _is_app_file_handler(handler):
                handler.setLevel(numeric_level)
    return normalized


def set_debug_logging(enabled: bool) -> str:
    from django.conf import settings

    settings.IS_DEBUG_LOG = bool(enabled)
    return set_logging_level("DEBUG" if enabled else "INFO")


__all__ = ["set_debug_logging", "set_logging_level"]
