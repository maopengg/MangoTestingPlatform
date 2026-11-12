from mangotools.contracts.test_target import TestTargetConfig
from mangotools.exceptions.test_target import TestTargetResolutionError
from mangotools.test_target import resolve_test_target
from pydantic import ValidationError

from src.apps.test_center.exceptions import TEST_TARGET_INVALID, TEST_TARGET_UNRESOLVED, TestCenterError


class TestTargetService:
    @staticmethod
    def validate(config):
        try:
            return TestTargetConfig.model_validate(config).model_dump(mode='json')
        except ValidationError:
            raise TestCenterError(TEST_TARGET_INVALID) from None

    @staticmethod
    def resolve(test_object, test_data=None):
        try:
            return resolve_test_target(test_object.value, getattr(test_object, 'target_config', None),
                                       test_data.get_cache if test_data is not None else None)
        except TestTargetResolutionError as error:
            raise TestCenterError(TEST_TARGET_UNRESOLVED, value=(error.msg,)) from None
