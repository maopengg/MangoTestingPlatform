from pydantic import StrictBool, ValidationError

from src.apps.auto_api.exceptions import API_RECOVERY_CONFIG_INVALID, AutoApiError
from src.common.schemas import StrictSchema


class ApiStepExecutionConfig(StrictSchema):
    is_recovery: StrictBool = False

    @classmethod
    def parse_config(cls, value):
        try:
            return cls.model_validate(value)
        except ValidationError as error:
            raise AutoApiError(API_RECOVERY_CONFIG_INVALID) from error


def is_recovery_step(step):
    return ApiStepExecutionConfig.parse_config(getattr(step, 'execution_config', {})).is_recovery
