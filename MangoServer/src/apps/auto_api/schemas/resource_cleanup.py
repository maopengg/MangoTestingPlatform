import re
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator, model_validator

from src.common.schemas import StrictSchema


ResourceIdentifier = Annotated[str, StringConstraints(min_length=1, max_length=64,
                                                     pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')]
ResourcePath = Annotated[str, StringConstraints(min_length=1, max_length=256,
                                               pattern=r'^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$')]


class ApiResourceChildRule(StrictSchema):
    table: ResourceIdentifier
    foreign_key: ResourceIdentifier
    root_field: ResourceIdentifier
    tenant_field: ResourceIdentifier
    max_rows: int = Field(default=1000, ge=1, le=10000)


class ApiResourceCleanupRule(StrictSchema):
    key: ResourceIdentifier
    trigger_step_key: str = Field(pattern=r'^step-[1-9][0-9]*$')
    api_info_id: int = Field(gt=0)
    sql_datasource_alias_id: int = Field(gt=0)
    es_datasource_alias_id: int = Field(gt=0)
    table: ResourceIdentifier
    primary_key: ResourceIdentifier = '_id'
    business_id_field: ResourceIdentifier = 'id'
    document_id_field: ResourceIdentifier = 'group_id'
    version_field: ResourceIdentifier = 'version'
    tenant_field: ResourceIdentifier = 'tenant_id'
    creator_field: ResourceIdentifier = 'create_employee_id'
    unique_field: ResourceIdentifier = 'name'
    request_unique_path: ResourcePath
    tenant_cache_key: ResourceIdentifier
    creator_cache_key: ResourceIdentifier
    response_id_path: ResourcePath = 'data.projectId'
    response_document_id_path: ResourcePath = 'data.groupId'
    response_version_path: ResourcePath = 'data.projectVersion'
    index_template: str = Field(pattern=r'^[a-z0-9][a-z0-9_-]*\{tenant\}$', max_length=200)
    es_tenant_path: ResourcePath = 'tenantId'
    es_business_id_path: ResourcePath = 'projectId'
    es_document_id_path: ResourcePath = 'groupId'
    es_version_path: ResourcePath = 'sourceVersion'
    children: list[ApiResourceChildRule] = Field(default_factory=list, max_length=10)
    observation_seconds: int = Field(default=15, ge=15, le=120)
    poll_seconds: int = Field(default=1, ge=1, le=5)

    @model_validator(mode='after')
    def distinct_identity(self):
        fields = [self.primary_key, self.business_id_field, self.document_id_field,
                  self.version_field, self.tenant_field, self.creator_field, self.unique_field]
        if len(set(fields)) != len(fields):
            raise ValueError('主键、业务ID、文档ID、版本、租户、创建人及唯一名称必须使用不同字段')
        if len({child.table for child in self.children}) != len(self.children):
            raise ValueError('子表不能重复')
        for child in self.children:
            if child.table == self.table or child.root_field not in (
                    self.primary_key, self.business_id_field, self.document_id_field):
                raise ValueError('子表只能关联已冻结的主表身份字段，不能重复主表')
        return self

    @field_validator('*')
    @classmethod
    def no_credential_fields(cls, value, info):
        if isinstance(value, str) and re.search(
                r'password|passwd|secret|authorization|cookie|credential|token', value, re.I):
            raise ValueError('清理规则不能引用凭据字段')
        return value


class ApiResourceCleanupRules(StrictSchema):
    rules: list[ApiResourceCleanupRule] = Field(default_factory=list, max_length=10)

    @model_validator(mode='after')
    def unique_rules(self):
        if len({rule.key for rule in self.rules}) != len(self.rules):
            raise ValueError('清理规则key不能重复')
        if len({(rule.trigger_step_key, rule.api_info_id) for rule in self.rules}) != len(self.rules):
            raise ValueError('同一步骤的同一创建接口只能配置一条资源规则')
        return self


class ApiResourceTargetSnapshot(StrictSchema):
    binding_id: int
    database_id: int
    connection_version: str
    database_name: str
    schema_name: str
    redis_db: int | None = None


class ApiResourceProof(StrictSchema):
    version: int = Field(default=1, ge=1, le=1)
    unique_name: str
    tenant: str
    creator: str
    sql_target: ApiResourceTargetSnapshot
    es_target: ApiResourceTargetSnapshot
    index: str
    index_uuid: str
    request_sent: bool = False
    execution_owner: dict[str, str] = Field(default_factory=dict, max_length=2)
    response_identity: dict[str, str] = Field(default_factory=dict, max_length=3)
    # 仅保存七个身份字段，不保存整行或响应正文。
    root: dict[str, str] = Field(default_factory=dict, max_length=7)
    sql_cleaned: bool = False
    es_verified: bool = False
    unknown_permits: list[dict[str, str]] = Field(default_factory=list, max_length=64)
    uncertain_request_ids: list[str] = Field(default_factory=list, max_length=64)
