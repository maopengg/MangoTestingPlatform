"""平台通知配置与报告展示数据，仅用于后端进程内发送。"""

from pydantic import Field
from mangotools.enums import TestCaseTypeEnum
from src.common.schemas import StrictSchema


class EmailNoticeModel(StrictSchema):
    send_user: str
    email_host: str
    stamp_key: str
    send_list: list[str]


class ReportFailureModel(StrictSchema):
    case_type: TestCaseTypeEnum
    task_name: str = ''
    case_name: str
    target_name: str
    message: str


class TestReportModel(StrictSchema):
    failure_details: list[ReportFailureModel] = Field(default_factory=list)
    failure_details_note: str = ''
    excluded_count: int = 0
    test_suite_id: int | None = None
    task_name: str | None = None
    project_name: str
    product_name: str | None = None

    test_environment: str

    case_sum: int

    api_case_sum: int | None = None
    api_fail: int | None = None

    ui_case_sum: int | None = None
    ui_fail: int | None = None

    pytest_case_sum: int | None = None
    pytest_fail: int | None = None

    success: int
    success_rate: float
    warning: int = 0
    fail: int

    execution_duration: str
    test_time: str


class WeChatNoticeModel(StrictSchema):
    webhook: str


class FeiShuNoticeModel(StrictSchema):
    webhook: str


class DingDingNoticeModel(StrictSchema):
    webhook: str
