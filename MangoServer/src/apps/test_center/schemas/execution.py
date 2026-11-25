from typing import Any

from mangotools.contracts import PytestExecutionResult, TestSuiteDetailResultContract

from src.apps.auto_api.schemas.execution import ApiCaseExecutionResult
from src.apps.auto_ui.schemas.execution import UiCaseExecutionResult
from src.apps.test_center.enums import TestCaseTypeEnum
from src.common.schemas import StrictSchema


class TestSuiteDetailResultSchema(StrictSchema):
    """Server-side typed form of the executor result wire contract."""

    id: int
    type: TestCaseTypeEnum
    test_suite: int
    status: int
    attempt: int | None = None
    error_message: str | None = None
    result_data: UiCaseExecutionResult | ApiCaseExecutionResult | list[dict[str, Any]] | PytestExecutionResult

    @classmethod
    def from_contract(cls, contract: TestSuiteDetailResultContract) -> "TestSuiteDetailResultSchema":
        payload = contract.model_dump()
        result_data = payload["result_data"]
        if contract.type == TestCaseTypeEnum.UI:
            payload["result_data"] = UiCaseExecutionResult.model_validate(result_data)
        elif contract.type == TestCaseTypeEnum.API:
            payload["result_data"] = ApiCaseExecutionResult.model_validate(result_data)
        elif contract.type == TestCaseTypeEnum.PYTEST:
            payload["result_data"] = PytestExecutionResult.model_validate(result_data)
        return cls.model_validate(payload)


__all__ = ["TestSuiteDetailResultSchema"]
