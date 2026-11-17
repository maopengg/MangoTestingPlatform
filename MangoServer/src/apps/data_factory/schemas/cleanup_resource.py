import re

from pydantic import Field, field_validator

from src.apps.data_factory.enums.cleanup_resource import EsCleanupModeEnum
from src.apps.data_factory.enums.cleanup import DataFactoryCleanupModeEnum
from src.apps.data_factory.schemas.performance import DatasourceInfrastructureIssue
from src.common.schemas import StrictSchema


class EsCleanupLineageRule(StrictSchema):
    entity_id: int = Field(gt=0)
    parent_field: str = Field(max_length=128, pattern=r'^[A-Za-z_][A-Za-z0-9_]*$',
        description='子记录中的父引用字段，其值必须等于本次根记录已冻结的ES文档ID；不推测SQL主键/业务ID映射。')
    tenant_field: str = Field(max_length=128, pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')
    id_field: str = Field(default='id', max_length=128, pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')
    collection_path: str = Field(max_length=256, pattern=r'^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$')
    document_id_path: str = Field(max_length=256, pattern=r'^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$')

    @field_validator('parent_field', 'tenant_field', 'id_field', 'collection_path', 'document_id_path')
    @classmethod
    def reject_credentials(cls, value):
        if re.search(r'password|passwd|pwd|token|secret|cookie|authorization|credential', value, re.IGNORECASE):
            raise ValueError('资源定位字段不能是凭据字段')
        return value


class EsCleanupLineageRow(StrictSchema):
    item_id: int = Field(gt=0)
    primary_value: str = Field(min_length=1, max_length=256)
    document_id: str = Field(min_length=1, max_length=256, pattern=r'^[A-Za-z0-9_-]+$')


class EsCleanupRule(StrictSchema):
    datasource_alias_id: int = Field(gt=0)
    document_id_field: str | None = Field(
        default=None, max_length=128, pattern=r'^[A-Za-z_][A-Za-z0-9_]*$',
        description='ES文档ID取自本次落库记录的哪个字段；不传/null使用数据库主键。显式指定后缺值必须失败，不回退主键。',
    )
    index_template: str = Field(
        min_length=1, max_length=200, pattern=r'^(?:\{tenant\}|[a-z0-9][a-z0-9_-]*(?:\{tenant\})?)$',
        description='精确索引名称，支持固定名称、example_{tenant}或单独{tenant}；最多一个末尾租户占位符，禁止通配符、多索引及路径。渲染后仍校验实际索引和资源归属。',
    )
    tenant_field: str = Field(default='tenant_id', max_length=128, pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')
    tenant_path: str = Field(default='tenant_id', max_length=256, pattern=r'^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$')
    mode: EsCleanupModeEnum = EsCleanupModeEnum.VERIFY
    timeout_seconds: int = Field(default=15, ge=2, le=60)
    poll_seconds: int = Field(default=1, ge=1, le=5)
    tenant_lineage: EsCleanupLineageRule | None = Field(default=None,
        description='仅用于根租户字段缺失的局部ES文档：以同执行、同数据库绑定的已创建子记录证明租户和父子归属；必须匹配完整且无重复的子ID集合。不能使用存量行或修改历史冻结规则。')

    @field_validator('tenant_field', 'tenant_path', 'document_id_field')
    @classmethod
    def reject_credential_fields(cls, value):
        if value is not None and re.search(r'password|passwd|pwd|token|secret|cookie|authorization|credential', value, re.IGNORECASE):
            raise ValueError('资源定位字段不能是凭据字段')
        return value


class EsCleanupRules(StrictSchema):
    rules: list[EsCleanupRule] = Field(default_factory=list, max_length=5)


class EsCleanupSnapshot(StrictSchema):
    rule: EsCleanupRule
    binding_id: int = Field(gt=0)
    connection_id: int = Field(gt=0)
    connection_version: str
    environment: int = Field(ge=0)
    index: str = Field(min_length=1, max_length=255, pattern=r'^[a-z0-9][a-z0-9_-]*$')
    document_id: str = Field(min_length=1, max_length=256, pattern=r'^[A-Za-z0-9_-]+$')
    document_id_field: str | None = Field(default=None, max_length=128, pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')
    row_primary_value: str | None = Field(default=None, min_length=1, max_length=256)
    tenant: str = Field(min_length=1, max_length=128)
    baseline_absent: bool
    requested_index: str | None = Field(default=None, max_length=255, pattern=r'^[a-z0-9][a-z0-9_-]*$')
    index_uuid: str | None = Field(default=None, min_length=1, max_length=128)
    lineage_rows: list[EsCleanupLineageRow] = Field(default_factory=list, max_length=100)


class EsCleanupCheckResult(StrictSchema):
    snapshot_index: int | None = Field(default=None, ge=0, le=4)
    index: str
    document_id: str
    success: bool
    checked_at: str
    attempts: int = Field(ge=0)
    error: str = ''


class EsCleanupCheckpoint(StrictSchema):
    task_id: int | None = Field(default=None, ge=1)
    snapshot_index: int = Field(ge=0, le=4)
    generation: int = Field(ge=0)
    started_at: float
    deadline: float
    next_check_at: float
    last_checked_at: float | None = None
    absent_count: int = Field(default=0, ge=0)
    final_count: int = Field(default=0, ge=0)
    attempts: int = Field(default=0, ge=0)
    interval: float = Field(default=1, ge=1, le=5)


class EsUnknownPermit(StrictSchema):
    group: str = Field(pattern=r'^[a-f0-9]{32}$')
    owner: str = Field(pattern=r'^[a-f0-9]{32}$')
    index: str
    document_id: str


class EsUncertainRequest(StrictSchema):
    request_id: str = Field(min_length=1, max_length=128)
    index: str
    document_id: str


class CleanupResourceState(StrictSchema):
    version: int = Field(default=1, ge=1, le=1)
    snapshots: list[EsCleanupSnapshot] = Field(default_factory=list, max_length=5)
    sql_cleaned: bool = False
    results: list[EsCleanupCheckResult] = Field(default_factory=list, max_length=5)
    checkpoints: list[EsCleanupCheckpoint] = Field(default_factory=list, max_length=5)
    unknown_permits: list[EsUnknownPermit] = Field(default_factory=list, max_length=64)
    uncertain_requests: list[EsUncertainRequest] = Field(default_factory=list, max_length=64)


class CleanupTaskPayload(StrictSchema):
    execution_id: int = Field(ge=1)
    mode: DataFactoryCleanupModeEnum = DataFactoryCleanupModeEnum.SCHEDULED
    force_cleanup: bool = True
    allow_missing: bool = True
    parent_case_detail_id: int | None = Field(default=None, ge=1)
    parent_attempt: int | None = Field(default=None, ge=1)

    @field_validator('mode', mode='before')
    @classmethod
    def parse_mode(cls, value):
        return DataFactoryCleanupModeEnum(value)


class CleanupReportOwner(StrictSchema):
    parent_case_detail_id: int = Field(ge=1)
    parent_attempt: int = Field(ge=1)


class FactoryExecutionOwner(StrictSchema):
    process_token: str = Field(min_length=1, max_length=64)
    process_started_at: str = Field(min_length=1, max_length=64)
    worker_name: str = Field(min_length=1, max_length=128)
    trace_id: int | None = Field(default=None, ge=1)
    trace_key: str | None = Field(default=None, max_length=64)


class FactoryExecutionReconciliation(StrictSchema):
    checked_at: str
    reason: str
    previous_error: str | None = Field(default=None, max_length=1000)


class CleanupTaskProgress(StrictSchema):
    started_at: float | None = None
    sql_done: bool = False
    active_seconds: float = Field(default=0, ge=0)
    verification_failed: bool = False
    generation: int = Field(default=0, ge=0)
    claim_token: str | None = Field(default=None, max_length=32)
    infrastructure_issues: list[DatasourceInfrastructureIssue] = Field(default_factory=list)
