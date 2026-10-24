from typing import Any

from mangotools.contracts import ApiRecordingContract

from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum
from src.common.schemas import StrictSchema


class ApiRecordingSchema(StrictSchema):
    project_product: int
    username: str
    type: int = 0
    module: int | None = None
    name: str
    client: int = 0
    url: str
    method: int
    header: dict[str, Any] | None = None
    params: str | None = None
    protocol_type: str = ApiProtocolTypeEnum.HTTP.value
    body_type: str = ApiBodyTypeEnum.NONE.value
    body_config: dict[str, Any] | None = None
    sse_config: dict[str, Any] | None = None
    status: int | None = None

    @classmethod
    def from_contract(cls, contract: ApiRecordingContract) -> "ApiRecordingSchema":
        payload = contract.model_dump(by_alias=True)
        if not payload.get("body_config"):
            if payload.get("file") not in (None, "", [], {}):
                payload["body_type"] = ApiBodyTypeEnum.MULTIPART.value
                payload["body_config"] = {
                    "fields": payload.get("data") or [],
                    "files": payload.get("file") if isinstance(payload.get("file"), list) else [payload["file"]],
                }
            elif payload.get("json") is not None:
                payload["body_type"] = ApiBodyTypeEnum.JSON.value
                json_value = payload["json"]
                payload["body_config"] = (
                    {"source_type": "template", "body_text": json_value}
                    if isinstance(json_value, str)
                    else {"source_type": "value", "body": json_value}
                )
            elif payload.get("data") is not None:
                payload["body_type"] = ApiBodyTypeEnum.RAW.value
                payload["body_config"] = {"body_text": payload["data"], "content_type": "application/json"}
        for legacy_field in ("data", "json", "file"):
            payload.pop(legacy_field, None)
        if not payload.get("body_type"):
            payload["body_type"] = ApiBodyTypeEnum.NONE.value
        return cls.model_validate(payload)


__all__ = ["ApiRecordingSchema"]
