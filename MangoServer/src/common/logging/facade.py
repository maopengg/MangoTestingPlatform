from __future__ import annotations

import logging
from typing import Any


class DomainLogger:
    """Compatibility facade that preserves the real business call site."""

    def __init__(self, name: str):
        self.log = logging.getLogger(name)

    @staticmethod
    def _stacklevel(kwargs: dict[str, Any]) -> dict[str, Any]:
        kwargs.setdefault("stacklevel", 2)
        return kwargs

    def debug(self, msg: object, *args, **kwargs) -> None:
        self.log.debug(msg, *args, **self._stacklevel(kwargs))

    def info(self, msg: object, *args, **kwargs) -> None:
        self.log.info(msg, *args, **self._stacklevel(kwargs))

    def warning(self, msg: object, *args, **kwargs) -> None:
        self.log.warning(msg, *args, **self._stacklevel(kwargs))

    def error(self, msg: object, *args, **kwargs) -> None:
        self.log.error(msg, *args, **self._stacklevel(kwargs))

    def exception(self, msg: object, *args, **kwargs) -> None:
        kwargs.setdefault("exc_info", True)
        self.log.error(msg, *args, **self._stacklevel(kwargs))

    def critical(self, msg: object, *args, **kwargs) -> None:
        self.log.critical(msg, *args, **self._stacklevel(kwargs))


class Log:
    system = DomainLogger("system")
    ui = DomainLogger("ui")
    api = DomainLogger("api")
    user = DomainLogger("user")
    perf = DomainLogger("perf")
    pytest = DomainLogger("pytest")
    monitoring = DomainLogger("monitoring")


log = Log()

__all__ = ["DomainLogger", "Log", "log"]
