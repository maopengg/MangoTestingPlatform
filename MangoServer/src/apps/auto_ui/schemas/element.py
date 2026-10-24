from mangotools.models import MethodModel
from pydantic import Field

from src.common.schemas import StrictSchema


class UiElementLocator(StrictSchema):
    exp: int | None = None
    loc: str = ""
    sub: int | None = None
    is_iframe: int | None = None
    prompt: str | None = None
    slot: int | None = None
    is_placeholder: bool = False


class UiElementExecution(StrictSchema):
    id: int
    element_id: int | None = None
    type: int
    name: str | None
    category: str | None = None
    ai_heal_status: int = 0
    element_version: int | None = None
    description_template: str | None = None
    page_url: str | None = None
    frame_path: list[dict] = Field(default_factory=list)
    collect_snapshot: bool = False
    elements: list[UiElementLocator] = Field(default_factory=list)
    sleep: int | None
    ope_key: str | None
    ope_value: list[MethodModel] = Field(default_factory=list)
    sql_execute: list[dict] | None = None
    custom: list[dict] | None = None
    condition_value: dict | None = None
    func: str | None = None
    precondition: dict | None = None
    postcondition: dict | None = None


class UiElementLocatorResult(StrictSchema):
    loc: str | None = None
    exp: int | None = None
    ele_quantity: int = 0
    element_text: str | None = None
    text_snippets: list[str] = Field(default_factory=list)
    visible: bool | None = None
    enabled: bool | None = None
    editable: bool | None = None
    bounding_box: dict | None = None
    locate_duration_ms: int | None = None
    sub: int | None = None
    is_iframe: int | None


class UiElementExecutionResult(StrictSchema):
    id: int
    name: str | None = None
    sleep: int | None = None
    type: int
    ope_key: str | None = None
    ope_value: list[MethodModel] | None = None
    sql_execute: list[dict] | None = None
    custom: list[dict] | None = None
    condition_value: dict | None = None
    ass_msg: str | None = None
    test_time: str | None = None
    stop_time: str | None = None
    duration_ms: int | None = None
    page_url: str | None = None
    page_title: str | None = None
    viewport: dict | None = None
    elements: list[UiElementLocatorResult] = Field(default_factory=list)
    status: int = 0
    error_message: str | None = None
    picture_path: str | None = None
    picture_name: str | None = None
    locator_engine: dict = Field(default_factory=dict)
    next_node_id: int | None = None


__all__ = ["UiElementExecution", "UiElementExecutionResult", "UiElementLocator", "UiElementLocatorResult"]
