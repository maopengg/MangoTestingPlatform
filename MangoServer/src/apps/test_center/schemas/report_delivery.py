import re
from urllib.parse import urlsplit

from pydantic import ConfigDict, Field, field_validator
from src.common.schemas.base import StrictSchema


class ReportDeliveryConfig(StrictSchema):
    model_config = ConfigDict(extra='forbid', validate_default=True)
    version: int = Field(default=1, ge=1, le=1)
    enabled: bool = False
    include_details: bool = True
    failed_cases_only: bool = True
    include_screenshots: bool = False
    link_ttl_seconds: int = Field(default=604800, ge=300, le=604800)
    html_public_base_url: str = Field(default='', max_length=2048)

    @field_validator('html_public_base_url')
    @classmethod
    def validate_html_public_base_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return ''
        try:
            url = urlsplit(value)
            valid = (url.scheme in ('http', 'https') and url.hostname and not url.username
                     and not url.password and not url.query and not url.fragment
                     and url.path in ('', '/') and not re.search(r'\s', value))
            port = url.port
            valid = valid and (port is None or 1 <= port <= 65535)
        except ValueError:
            valid = False
        if not valid:
            raise ValueError('HTML 报告访问地址必须是 HTTP/HTTPS 域名，不含路径、账号或查询参数')
        return value.rstrip('/')
