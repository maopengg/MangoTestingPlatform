from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator
from rest_framework import serializers

from src.common.schemas import TrimmedStrictSchema


class UiStepCondition(TrimmedStrictSchema):
    type: Literal[
        'url_path', 'page_title', 'visible_text', 'element_state',
    ]
    matcher: Literal[
        'equals', 'contains', 'starts_with', 'regex', 'count_gte',
        'visible', 'hidden', 'enabled', 'editable', 'checked',
    ]
    expected: Any = None
    element_id: int | None = Field(default=None, ge=1)
    count: int | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def validate_shape(self):
        compatible = {
            'url_path': {'equals', 'contains', 'starts_with', 'regex'},
            'page_title': {'equals', 'contains', 'starts_with', 'regex'},
            'visible_text': {'equals', 'contains', 'starts_with', 'regex', 'count_gte'},
            'element_state': {'visible', 'hidden', 'enabled', 'editable', 'checked'},
        }
        if self.matcher not in compatible[self.type]:
            raise ValueError(f'{self.matcher} is not supported for {self.type}')
        if self.type == 'element_state' and not self.element_id:
            raise ValueError('element_state requires element_id')
        if self.matcher == 'count_gte' and self.count is None:
            raise ValueError('count_gte requires count')
        if (
                self.type != 'element_state'
                and self.matcher not in {'visible', 'hidden', 'enabled', 'editable', 'checked'}
                and self.expected in (None, '')
        ):
            raise ValueError(f'{self.type} requires expected')
        return self


class UiStepConditionGroup(TrimmedStrictSchema):
    operator: Literal['all', 'any'] = 'all'
    conditions: list[UiStepCondition] = Field(default_factory=list, max_length=20)


class UiStepDurableLocator(TrimmedStrictSchema):
    exp: Literal[0, 2, 3, 4, 9]
    loc: str = Field(min_length=1, max_length=1000)
    sub: int | None = Field(default=None, ge=1)
    strategy: str = Field(min_length=1, max_length=80)


class UiStepHealingPolicy(TrimmedStrictSchema):
    mode: Literal['off', 'suggest_only', 'execute_low_risk'] = 'off'
    total_timeout_seconds: int = Field(default=60, ge=5, le=120)
    max_model_calls: int = Field(default=2, ge=1, le=3)
    max_patch_actions: int = Field(default=3, ge=1, le=5)
    max_recovery_rounds: int = Field(default=1, ge=1, le=2)
    allowed_actions: list[Literal[
        'retry_node', 'replace_target', 'insert_action', 'skip_node', 'jump_to_node',
    ]] = Field(default_factory=lambda: [
        'retry_node', 'replace_target', 'insert_action', 'skip_node', 'jump_to_node',
    ])
    auto_writeback: bool = True
    auto_writeback_min_confidence: float = Field(default=0.9, ge=0.7, le=1)

    @field_validator('allowed_actions')
    @classmethod
    def unique_actions(cls, value):
        return list(dict.fromkeys(value))


class UiStepRepairAction(TrimmedStrictSchema):
    action: Literal[
        'retry_node', 'replace_target', 'insert_action', 'skip_node', 'jump_to_node', 'abort',
    ]
    node_id: str | None = None
    operation_intent: Literal['activate', 'select', 'edit', 'close', 'expand', 'navigate'] | None = None
    target_ref: str | None = Field(default=None, pattern=r'^e[1-9]\d*$')
    target_name: str | None = Field(default=None, max_length=256)
    target_role: str | None = Field(default=None, max_length=80)
    target_tag: str | None = Field(default=None, max_length=80)
    durable_locators: list[UiStepDurableLocator] = Field(default_factory=list, max_length=3)
    placement: Literal['before', 'after'] | None = None
    value_binding: str | None = Field(default=None, max_length=256)
    value_literal: str | None = Field(default=None, min_length=1, max_length=256)
    reason: str = Field(min_length=1, max_length=500)
    expected_condition: UiStepConditionGroup = Field(default_factory=UiStepConditionGroup)

    @model_validator(mode='after')
    def validate_action_fields(self):
        if self.action in {'retry_node', 'skip_node', 'jump_to_node', 'replace_target'} and not self.node_id:
            raise ValueError(f'{self.action} requires node_id')
        if self.action in {'replace_target', 'insert_action'} and not self.target_ref:
            raise ValueError(f'{self.action} requires target_ref')
        if self.action == 'insert_action' and not self.operation_intent:
            raise ValueError('insert_action requires operation_intent')
        if self.value_binding and self.value_literal:
            raise ValueError('value_binding and value_literal are mutually exclusive')
        return self


class UiStepRepairPlan(TrimmedStrictSchema):
    schema_version: Literal[1] = 1
    current_phase: str | None = Field(default=None, max_length=128)
    diagnosis_code: str = Field(min_length=1, max_length=128)
    diagnosis_summary: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0, le=1)
    actions: list[UiStepRepairAction] = Field(default_factory=list, max_length=5)
    expected_checkpoint: str | None = Field(default=None, max_length=128)
    user_message: str = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def reject_conflicting_flow_control(self):
        flow_actions = [item for item in self.actions if item.action in {'skip_node', 'jump_to_node', 'abort'}]
        if len(flow_actions) > 1 or (flow_actions and self.actions[-1] is not flow_actions[0]):
            raise ValueError('流程控制动作最多一个且必须放在最后')
        return self


class UiPageStepHealReport(TrimmedStrictSchema):
    schema_version: Literal[1] = 1
    page_step_id: int = Field(ge=1)
    executor_task_id: int | None = Field(default=None, ge=1)
    trace_id: str = Field(pattern=r'^[0-9a-fA-F-]{32,36}$')
    dispatch_id: str | None = Field(default=None, max_length=128)
    test_env: int | None = None
    source_version: int = Field(ge=1)
    failed_node_id: str | None = Field(default=None, max_length=128)
    trigger: str = Field(min_length=1, max_length=128)
    before_state: dict = Field(default_factory=dict)
    after_state: dict = Field(default_factory=dict)
    proposed_plan: UiStepRepairPlan | None = None
    executed_plan: UiStepRepairPlan | None = None
    status: Literal['suggested', 'recovered', 'failed', 'rejected']
    writeback_status: Literal['none', 'pending_review'] = 'none'
    confidence: float = Field(default=0, ge=0, le=1)
    user_message: str = Field(default='', max_length=500)
    error_message: str | None = None
    auto_writeback_requested: bool = False

    @model_validator(mode='after')
    def validate_writeback_state(self):
        if self.writeback_status == 'pending_review' and self.status not in {'recovered', 'suggested'}:
            raise ValueError('only recovered or suggested reports may wait for review')
        return self


def validate_condition_group(value, field_name: str, *, allow_empty: bool = True) -> dict:
    if value in (None, ''):
        return {}
    if value == {} and allow_empty:
        return {}
    try:
        group = UiStepConditionGroup.model_validate(value)
        if allow_empty and not group.conditions:
            return {}
        return group.model_dump(mode='json')
    except ValidationError as error:
        raise serializers.ValidationError(f'{field_name}结构错误：{error}') from error


def validate_healing_policy(value) -> dict:
    if value in (None, '', {}):
        return UiStepHealingPolicy().model_dump(mode='json')
    try:
        return UiStepHealingPolicy.model_validate(value).model_dump(mode='json')
    except ValidationError as error:
        raise serializers.ValidationError(f'流程自愈策略结构错误：{error}') from error
