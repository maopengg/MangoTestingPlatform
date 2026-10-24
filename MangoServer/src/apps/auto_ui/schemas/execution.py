# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏

from typing import Any

from mangotools.contracts import (
    UiCaseExecutionContract,
    UiCaseResultContract,
    UiEnvironmentContract,
    UiFlowRuntimeNodeContract,
    UiPageStepExecutionContract,
    UiPageStepResultContract,
    UiPublicVariableContract,
    UiStepDataContract,
)
from pydantic import Field

from src.apps.auto_ui.schemas.auth import UiAuthCache
from src.apps.auto_ui.schemas.case_schema import (
    UiCaseFrontCustomSchema,
    UiCaseFrontSqlSchema,
    UiCasePosteriorSqlSchema,
)
from src.apps.auto_ui.schemas.element import UiElementExecution, UiElementExecutionResult
from src.common.schemas import StrictSchema


class UiStepControlSchema(StrictSchema):
    close_after_execution: bool = False
    before_wait_seconds: int = Field(default=0, ge=0, le=3600)
    after_wait_seconds: int = Field(default=0, ge=0, le=3600)
    close_live_after_execution: bool = False


class UiPageStepExecutionSchema(UiPageStepExecutionContract):
    element_list: list[UiElementExecution] | UiElementExecution = []
    environment_config: UiEnvironmentContract
    public_data_list: list[UiPublicVariableContract] = []
    flow_data: UiFlowRuntimeNodeContract | None = None
    step_control: UiStepControlSchema = Field(default_factory=UiStepControlSchema)


class UiCasePageStepExecutionSchema(UiPageStepExecutionSchema):
    execution_id: str | None = None
    case_steps_id: int | None = None
    case_data: list[UiStepDataContract] = []


class UiDebugPageStepExecutionSchema(UiPageStepExecutionSchema):
    send_user: str
    workspace_id: str | None = None
    slot_id: str | None = None
    executor_connection_id: str | None = None
    ui_auth_cache: UiAuthCache | None = None


class UiElementCheckCommand(UiDebugPageStepExecutionSchema):
    schema_version: int = 2
    check_id: str
    send_user: str
    check_mode: str = 'normal'


class UiElementCheckResultSchema(StrictSchema):
    schema_version: int = 2
    workspace_id: str | None = None
    slot_id: str | None = None
    executor_connection_id: str | None = None
    check_id: str
    check_mode: str = 'normal'
    element_id: int
    locator_version: int | None = None
    element_name: str
    test_env: int | None = None
    status: int = 0
    check_status: str = 'invalid'
    error_message: str | None = None
    page_url: str | None = None
    page_title: str | None = None
    duration_ms: int | None = None
    checked_time: str | None = None
    locator_groups: list[dict] = Field(default_factory=list)
    selected_result: UiElementExecutionResult | None = None
    expected_event_result: dict = Field(default_factory=dict)
    baseline: dict = Field(default_factory=dict)


class UiCaseExecutionSchema(UiCaseExecutionContract):
    front_custom: list[UiCaseFrontCustomSchema]
    front_sql: list[UiCaseFrontSqlSchema]
    posterior_sql: list[UiCasePosteriorSqlSchema]
    parametrize: list[dict] | list
    ui_auth_cache: UiAuthCache | None = None
    steps: list[UiCasePageStepExecutionSchema]


class UiPageStepResult(UiPageStepResultContract):
    element_result_list: Any


class UiCaseExecutionResult(UiCaseResultContract):
    steps: list[UiPageStepResult]
