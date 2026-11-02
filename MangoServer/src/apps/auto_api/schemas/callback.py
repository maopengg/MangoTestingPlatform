from typing import Any

from pydantic import Field, ValidationError, model_validator

from src.common.schemas import StrictSchema
from src.apps.auto_api.enums.callback import (
    CallbackCheckType, CallbackDeliveryPolicy, CallbackEventMode, CallbackSource, CallbackResponseMode,
)
from src.apps.auto_api.exceptions import AutoApiError, API_CALLBACK_CONFIG_INVALID
from src.apps.auto_api.schemas.case_schema import ApiGeneralAssertionItem


class CallbackCacheReference(StrictSchema):
    cache_key: str = Field(min_length=1, max_length=128)


class CallbackDeliveryEvidence(StrictSchema):
    event_id: str = Field(min_length=1, max_length=256)
    raw_body_base64: str = ''
    body_sha256: str = Field(min_length=64, max_length=64)
    body_length: int = Field(ge=0)
    evidence_complete: bool = True
    evidence_expired: bool = False
    request_headers: dict[str, str] = Field(default_factory=dict)
    business_body: str = ''


class CallbackCorrelation(StrictSchema):
    source: CallbackSource = CallbackSource.ENVELOPE
    field: str = Field(min_length=1, max_length=256)
    expected: CallbackCacheReference

    @model_validator(mode='after')
    def validate_source(self):
        if self.source == CallbackSource.RAW:
            raise ValueError('关联字段不能使用完整正文')
        return self


class CallbackEvents(StrictSchema):
    mode: CallbackEventMode = CallbackEventMode.AT_LEAST
    count: int = Field(default=1, ge=1, le=100)


class CallbackCheck(StrictSchema):
    key: str = Field(min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9_-]+$')
    type: CallbackCheckType
    source: CallbackSource = CallbackSource.RAW
    field: str = Field(default='', max_length=256)
    operator: str = 'equals'
    expected: Any = None
    assertions: list[ApiGeneralAssertionItem] = Field(
        default_factory=list, max_length=30,
        description='字段检查复用通用断言和分组；actual 自动取回调字段，预期值使用触发前 Case 缓存快照。空列表保留旧 operator 语义。',
    )

    @model_validator(mode='after')
    def validate_check(self):
        if self.assertions and self.type != CallbackCheckType.FIELD:
            raise ValueError('通用断言仅适用于字段检查')
        if self.type == CallbackCheckType.FIELD and self.operator not in {'exists', 'equals', 'contains'}:
            raise ValueError('回调字段断言仅支持存在、相等、包含')
        if self.type == CallbackCheckType.COMPACT and self.source not in {CallbackSource.RAW, CallbackSource.BUSINESS}:
            raise ValueError('紧凑检查仅支持原始正文或解密正文')
        if self.type in {CallbackCheckType.SIGNATURE, CallbackCheckType.COMPACT_SIGNATURE_SIMULATION} and self.source != CallbackSource.RAW:
            raise ValueError('签名必须使用原始正文')
        return self


class CallbackRule(StrictSchema):
    key: str = Field(min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9_-]+$')
    name: str = Field(min_length=1, max_length=128)
    enabled: bool = True
    trigger_step_key: str = Field(pattern=r'^step-[1-9][0-9]*$')
    mock_config_id: int = Field(gt=0)
    correlation: CallbackCorrelation
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    observation_seconds: int = Field(default=0, ge=0, le=300)
    max_deliveries: int = Field(default=100, ge=1, le=100)
    min_deliveries: int = Field(default=1, ge=1, le=100)
    min_retry_interval_ms: int = Field(default=0, ge=0, le=300000)
    max_retry_interval_ms: int | None = Field(default=None, ge=0, le=300000)
    events: CallbackEvents = Field(default_factory=CallbackEvents)
    event_id_source: CallbackSource = CallbackSource.BUSINESS
    event_id_field: str = Field(default='$.header.event_id', min_length=1, max_length=256)
    delivery_policy: CallbackDeliveryPolicy = CallbackDeliveryPolicy.ALL
    response_mode: CallbackResponseMode = CallbackResponseMode.OBSERVE
    failure_status: int = Field(default=400, ge=400, le=599)
    checks: list[CallbackCheck] = Field(default_factory=list, min_length=1, max_length=30)

    @model_validator(mode='after')
    def validate_window(self):
        if not any(item.type != CallbackCheckType.COMPACT_SIGNATURE_SIMULATION for item in self.checks):
            raise ValueError('至少需要一个非诊断检查项')
        if self.event_id_source == CallbackSource.RAW:
            raise ValueError('事件ID必须来自明确字段')
        if self.observation_seconds >= self.timeout_seconds:
            raise ValueError('观察窗口必须小于等待超时')
        if self.events.mode == CallbackEventMode.EXACT and not self.observation_seconds:
            raise ValueError('精确数量检查必须配置观察窗口')
        if self.max_deliveries < 100 and not self.observation_seconds:
            raise ValueError('投递次数上限检查必须配置观察窗口')
        if self.min_deliveries > self.max_deliveries:
            raise ValueError('最少投递次数不能大于最多投递次数')
        if (self.min_deliveries > 1 or self.min_retry_interval_ms or self.max_retry_interval_ms is not None) and not self.observation_seconds:
            raise ValueError('重试次数与间隔检查必须配置观察窗口')
        if self.max_retry_interval_ms is not None and self.max_retry_interval_ms < self.min_retry_interval_ms:
            raise ValueError('重试间隔上限不能小于下限')
        if len({item.key for item in self.checks}) != len(self.checks):
            raise ValueError('检查项 key 不能重复')
        return self


def validate_callback_rules(value):
    if not isinstance(value, list) or len(value) > 5:
        raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('最多配置 5 条回调验证',))
    try:
        rules = [CallbackRule.model_validate(item) for item in value]
    except ValidationError as error:
        # 不输出包含期望值或敏感正文的 Pydantic 原始入参。
        first_error = error.errors(include_input=False)[0]
        location = '.'.join(str(part) for part in first_error['loc']) or '规则'
        message = first_error['msg'].removeprefix('Value error, ')
        raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=(f'{location}：{message}',)) from error
    if len({item.key for item in rules}) != len(rules):
        raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('规则 key 不能重复',))
    return [item.model_dump(mode='json') for item in rules]
