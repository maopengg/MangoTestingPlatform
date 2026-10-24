from typing import Literal
from pydantic import Field, SecretStr, field_validator
from urllib.parse import urlsplit
from src.common.schemas.base import TrimmedStrictSchema


class EvaluationAiProfile(TrimmedStrictSchema):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=100)
    provider_type: Literal["openai", "openai_compatible", "azure_openai"] = "openai_compatible"
    base_url: str = Field(min_length=1, max_length=1000)
    model: str = Field(min_length=1, max_length=200)
    api_key: SecretStr
    timeout: int = Field(default=120, ge=1, le=3600, strict=True)
    enabled: bool = True

    @field_validator("base_url")
    @classmethod
    def valid_endpoint(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("服务地址必须是无账号密码的 HTTP/HTTPS 地址")
        return value
