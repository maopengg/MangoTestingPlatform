from pydantic import Field
from src.common.schemas.base import TrimmedStrictSchema


class McpBindingDefinition(TrimmedStrictSchema):
    tool_name: str = Field(min_length=1, max_length=256)
    server_id: int | None = None
    server_name: str = ""
    server_url: str | None = None
    transport_type: int = Field(default=0, ge=0, le=2)
    tool_id: int | None = None
    tool_title: str | None = None
    tool_type: str = "tool"
    tool_enabled: bool = True
    risk_level: int = 0
    write_operation: bool = False
    require_confirm: bool = False
    mcp_config: dict | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    schema_hash: str | None = None
    snapshot_id: int | None = None
    snapshot_test_env: int | None = None
    snapshot_create_time: str | None = None
