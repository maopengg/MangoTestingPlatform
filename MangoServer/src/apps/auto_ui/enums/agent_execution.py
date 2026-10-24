from enum import Enum


class AgentUiStepStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class AgentUiArtifactKind(str, Enum):
    SCREENSHOT = "screenshot"
    TRACE = "trace"
    LOG = "log"
    OTHER = "other"


__all__ = ["AgentUiArtifactKind", "AgentUiStepStatus"]
