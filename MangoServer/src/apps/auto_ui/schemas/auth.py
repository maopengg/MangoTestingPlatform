from mangotools.contracts import UiAuthStorageItemContract
from pydantic import Field

from src.common.schemas import OpenSchema, StrictSchema


class UiAuthCookie(StrictSchema):
    name: str
    value: str
    domain: str | None = None
    path: str = "/"
    expires: int | float | None = None
    httpOnly: bool = False
    secure: bool = False
    sameSite: str | None = None


class UiAuthStorageStateOrigin(OpenSchema):
    origin: str
    localStorage: list[dict] = Field(default_factory=list)


class UiAuthStorageState(OpenSchema):
    cookies: list[UiAuthCookie] = Field(default_factory=list)
    origins: list[UiAuthStorageStateOrigin] = Field(default_factory=list)


class UiAuthCache(StrictSchema):
    cookies: list[UiAuthCookie] = Field(default_factory=list)
    local_storage: list[UiAuthStorageItemContract] = Field(default_factory=list)
    session_storage: list[UiAuthStorageItemContract] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    storage_state: UiAuthStorageState | None = None


__all__ = ["UiAuthCache", "UiAuthCookie", "UiAuthStorageState", "UiAuthStorageStateOrigin"]
