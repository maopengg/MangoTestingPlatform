from django.conf import settings

from src.common.logging import set_debug_logging


class LoggingLevelService:
    @staticmethod
    def set_debug(enabled) -> dict:
        if isinstance(enabled, str):
            enabled = enabled.strip().lower() in {"1", "true", "yes", "on"}
        level = set_debug_logging(bool(enabled))
        settings.BUSINESS_LOG_LEVEL = level
        return {
            "is_debug": settings.IS_DEBUG_LOG,
            "level": level,
            "service": settings.MANGO_SERVICE_NAME,
            "instance": settings.MANGO_SERVICE_INSTANCE,
            "scope": "current_process",
        }


__all__ = ["LoggingLevelService"]
