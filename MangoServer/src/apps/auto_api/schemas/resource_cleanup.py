import re
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator, model_validator

from src.common.schemas import StrictSchema
from src.apps.data_factory.schemas.elasticsearch import EsIndexTemplate
from src.apps.data_factory.schemas.cleanup_history import CleanupHistoryEntry


ResourceIdentifier = Annotated[str, StringConstraints(min_length=1, max_length=64,
                                                     pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')]
ResourcePath = Annotated[str, StringConstraints(min_length=1, max_length=256,
                                               pattern=r'^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$')]
ResourceEsPath = Annotated[str, StringConstraints(min_length=1, max_length=256,
    pattern=r'^[A-Za-z_][A-Za-z0-9_]*(?:\[\])?(?:\.[A-Za-z_][A-Za-z0-9_]*)*$')]


class ApiResourceEsIdentityMapping(StrictSchema):
    es_business_id_path: ResourceEsPath
    es_version_path: ResourceEsPath

    @field_validator('*')
    @classmethod
    def no_credentials(cls, value):
        if isinstance(value, str) and re.search(r'password|passwd|secret|authorization|cookie|credential|token', value, re.I):
            raise ValueError('ES归属映射不能引用凭据字段')
        return value

    @model_validator(mode='after')
    def same_owner_element(self):
        paths = (self.es_business_id_path, self.es_version_path)
        if any('[]' in path for path in paths):
            if not all('[]' in path for path in paths) or len({path.split('[]')[0] for path in paths}) != 1:
                raise ValueError('ES数组业务ID和版本必须定位同一数组元素')
        return self


class ApiResourceEsIdentityCorrection(ApiResourceEsIdentityMapping):
    operator_id: int = Field(gt=0)
    corrected_at: str


class ApiResourceChildMapping(StrictSchema):
    original_table: ResourceIdentifier
    table: ResourceIdentifier
    foreign_key: ResourceIdentifier


class ApiResourceChildCorrection(ApiResourceChildMapping):
    operator_id: int = Field(gt=0)
    corrected_at: str


class ApiResourceChildRule(StrictSchema):
    table: ResourceIdentifier
    foreign_key: ResourceIdentifier
    root_field: ResourceIdentifier
    tenant_field: ResourceIdentifier
    max_rows: int = Field(default=1000, ge=1, le=10000)


class ApiResourceVersionUpdate(StrictSchema):
    trigger_step_key: str = Field(pattern=r'^step-[1-9][0-9]*$')
    api_info_id: int = Field(gt=0)
    request_id_path: ResourcePath | None = None
    request_id_in_url: bool = False
    response_id_path: ResourcePath
    response_version_path: ResourcePath
    success_response: dict[ResourcePath, bool | int | str] = Field(min_length=1, max_length=5)

    @model_validator(mode='after')
    def one_request_identity(self):
        if bool(self.request_id_path) == self.request_id_in_url:
            raise ValueError('资源变更必须且只能指定请求正文ID路径或URL路径ID')
        return self


class ApiResourceVersionTransition(StrictSchema):
    step_id: int = Field(gt=0)
    parameter_id: int = Field(gt=0)
    api_info_id: int = Field(gt=0)
    before_version: str
    root_after: dict[str, str] = Field(min_length=7, max_length=7)
    response_digest: str
    confirmed_at: str


class ApiResourceMutationAttempt(StrictSchema):
    resource_id: int
    update: ApiResourceVersionUpdate
    root_before: dict[str, str]


class ApiResourceRejectionRecovery(StrictSchema):
    rejection_response: dict[ResourcePath, bool] = Field(min_length=1, max_length=5)

    @field_validator('rejection_response', mode='before')
    @classmethod
    def explicit_false(cls, value):
        if not isinstance(value, dict) or any(type(item) is not bool or item is not False for item in value.values()):
            raise ValueError('历史拒绝响应只接受明确的布尔false契约')
        return value


class ApiResourceRejectionEvidence(StrictSchema):
    operator_id: int = Field(gt=0)
    confirmed_at: str
    execution_result_id: int = Field(gt=0)
    result_checksum: str
    response_digest: str
    rejection_response: dict[str, bool]


class ApiResourceRecoveryEvidence(StrictSchema):
    identity_mapping: ApiResourceEsIdentityMapping | None = None
    child_mapping: list[ApiResourceChildMapping] = Field(default_factory=list, max_length=10)
    rejection_recovery: ApiResourceRejectionRecovery | None = None


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
    name_source_key: ResourceIdentifier | None = None
    rejection_response: dict[ResourcePath, str | int | bool] = Field(default_factory=dict, max_length=5)
    request_unique_path: ResourcePath
    tenant_cache_key: ResourceIdentifier
    creator_cache_key: ResourceIdentifier
    response_id_path: ResourcePath = 'data.projectId'
    response_document_id_path: ResourcePath = 'data.groupId'
    response_version_path: ResourcePath = 'data.projectVersion'
    index_template: EsIndexTemplate = Field(description='精确索引：固定名称、example_{tenant}或{tenant}。不自动建索引，不允许通配或多索引。')
    es_tenant_path: ResourcePath = 'tenantId'
    es_business_id_path: ResourceEsPath = 'projectId'
    es_document_id_path: ResourcePath = 'groupId'
    es_version_path: ResourceEsPath = 'sourceVersion'
    children: list[ApiResourceChildRule] = Field(default_factory=list, max_length=10)
    observation_seconds: int = Field(default=15, ge=15, le=120)
    poll_seconds: int = Field(default=1, ge=1, le=5)
    version_updates: list[ApiResourceVersionUpdate] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def distinct_identity(self):
        ApiResourceEsIdentityMapping(es_business_id_path=self.es_business_id_path,
                                     es_version_path=self.es_version_path)
        if self.name_source_key == self.key:
            raise ValueError('名称只能复用本执行前序已登记的资源')
        if any(type(value) is not bool or value is not False for value in self.rejection_response.values()):
            raise ValueError('拒绝响应必须显式匹配布尔false，不接受成功响应或空匹配')
        fields = [self.primary_key, self.business_id_field, self.document_id_field,
                  self.version_field, self.tenant_field, self.creator_field, self.unique_field]
        if len(set(fields)) != len(fields):
            raise ValueError('主键、业务ID、文档ID、版本、租户、创建人及唯一名称必须使用不同字段')
        if len({child.table for child in self.children}) != len(self.children):
            raise ValueError('子表不能重复')
        if len({(item.trigger_step_key, item.api_info_id) for item in self.version_updates}) != len(self.version_updates):
            raise ValueError('资源变更步骤不能重复')
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
        by_key = {rule.key: rule for rule in self.rules}
        for rule in self.rules:
            if rule.name_source_key:
                source = by_key.get(rule.name_source_key)
                if source is None or any(getattr(source, key) != getattr(rule, key) for key in (
                    'sql_datasource_alias_id', 'es_datasource_alias_id', 'table', 'primary_key',
                    'business_id_field', 'document_id_field', 'version_field', 'tenant_field',
                    'creator_field', 'unique_field', 'tenant_cache_key', 'creator_cache_key', 'index_template')):
                    raise ValueError('同名来源规则必须存在，且数据源、身份字段及租户来源必须一致')
        return self


class ApiResourceTargetSnapshot(StrictSchema):
    binding_id: int
    database_id: int
    connection_version: str
    database_name: str
    schema_name: str
    redis_db: int | None = None


class ApiResourceProof(StrictSchema):
    cleanup_history: list[CleanupHistoryEntry] = Field(default_factory=list)
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
    existing_root: dict[str, str] = Field(default_factory=dict, max_length=7)
    rejection_confirmed: bool = False
    sql_cleaned: bool = False
    es_verified: bool = False
    unknown_permits: list[dict[str, str]] = Field(default_factory=list, max_length=64)
    uncertain_request_ids: list[str] = Field(default_factory=list, max_length=64)
    es_identity_correction: ApiResourceEsIdentityCorrection | None = None
    child_corrections: list[ApiResourceChildCorrection] = Field(default_factory=list, max_length=10)
    version_transitions: list[ApiResourceVersionTransition] = Field(default_factory=list, max_length=50)
    rejection_evidence: ApiResourceRejectionEvidence | None = None
