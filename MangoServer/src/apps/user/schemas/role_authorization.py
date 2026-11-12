from typing import Annotated, Literal

from pydantic import Field, StrictInt, StrictStr

from src.common.schemas import StrictSchema
from src.apps.user.enums.permission import EndpointPermissionEffectEnum


class RoleAuthorization(StrictSchema):
    version: Annotated[StrictInt, Field(ge=1, le=1)] = 1
    menu_keys: list[Annotated[StrictStr, Field(pattern=r'^[a-zA-Z0-9_.-]+$')]] = Field(default_factory=list)
    endpoint_permissions: dict[
        Annotated[StrictStr, Field(pattern=r'^(http|mcp)\.[a-f0-9]{64}$')], EndpointPermissionEffectEnum
    ] = Field(default_factory=dict)


class RoleAuthorizationBackupItem(StrictSchema):
    id: Annotated[StrictInt, Field(gt=0)]
    name: StrictStr
    authorization: RoleAuthorization


class RoleAuthorizationBackup(StrictSchema):
    format: Literal['mango-role-authorization-v1'] = 'mango-role-authorization-v1'
    roles: list[RoleAuthorizationBackupItem]
