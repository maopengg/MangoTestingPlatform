"""Pydantic schema bases without business fields."""

from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    """Schema used for app-owned input and configuration validation."""

    model_config = ConfigDict(extra="forbid")


class FrozenSchema(BaseModel):
    """Immutable value schema used for stable snapshots and value objects."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class OrmSchema(BaseModel):
    """Read schema that can be built from Django ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class OpenSchema(BaseModel):
    """Schema for explicitly extensible third-party or runtime payloads."""

    model_config = ConfigDict(extra="allow")


class TrimmedStrictSchema(BaseModel):
    """Strict schema that also normalizes surrounding whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


__all__ = ["FrozenSchema", "OpenSchema", "OrmSchema", "StrictSchema", "TrimmedStrictSchema"]
