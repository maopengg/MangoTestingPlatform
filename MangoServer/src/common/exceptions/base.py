"""Protocol-neutral exception base classes."""

from __future__ import annotations

from typing import Any

from .definitions import ErrorDefinition


class MangoServerError(Exception):
    """Base class for expected business failures.

    Every expected failure is backed by a named :class:`ErrorDefinition`.
    """

    def __init__(
            self,
            definition: ErrorDefinition,
            *,
            value: tuple[Any, ...] | None = None,
            error: str | None = None,
            error_code: str | None = None,
            details: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(definition, ErrorDefinition):
            raise TypeError("definition must be an ErrorDefinition")
        self.code = definition.code
        template = definition.message
        self.msg = template.format(*value) if value else template
        self.error_code = error_code or str(definition.code)
        self.details = details or {}
        self.cause = error
        super().__init__(self.msg)

    def __str__(self) -> str:
        return f"[{self.code}] {self.msg}"


class CommonError(MangoServerError):
    """Expected failure owned by a genuinely cross-app common capability."""
