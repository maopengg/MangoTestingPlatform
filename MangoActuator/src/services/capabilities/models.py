from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CapabilityDefinition:
    code: str
    display_name: str
    supported_os: tuple[str, ...]
    task_types: tuple[str, ...]
    protocol_version: int = 1
    default_capacity: int = 1


@dataclass
class CapabilityStatus:
    code: str
    display_name: str
    state: str
    enabled: bool
    protocol_version: int
    capacity: int
    running: int = 0
    engine_versions: dict[str, str] = field(default_factory=dict)
    dependencies: dict[str, Any] = field(default_factory=dict)
    reason_code: str | None = None
    reason: str | None = None
    checked_at: str | None = None

    @property
    def ready(self) -> bool:
        return self.enabled and self.state == "ready" and self.capacity > 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
