# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏

from src.apps.auto_api.services.execution.cases.test_case_parts.debugging import ApiTestCaseDebuggingMixin
from src.apps.auto_api.services.execution.cases.test_case_parts.execution import ApiTestCaseExecutionMixin
from src.apps.auto_api.services.execution.cases.test_case_parts.lifecycle import ApiTestCaseLifecycleMixin
from src.apps.auto_api.services.execution.cases.test_case_parts.parameter import ApiTestCaseParameterMixin
from src.apps.auto_api.services.execution.cases.test_case_parts.protocol import ApiTestCaseProtocolMixin
from src.apps.auto_api.services.execution.cases.test_case_parts.step import ApiTestCaseStepMixin
from src.apps.auto_api.services.execution.cases.test_case_parts.recovery import ApiTestCaseRecoveryMixin


class TestCase(ApiTestCaseProtocolMixin, ApiTestCaseLifecycleMixin, ApiTestCaseExecutionMixin, ApiTestCaseRecoveryMixin,
               ApiTestCaseDebuggingMixin, ApiTestCaseStepMixin, ApiTestCaseParameterMixin):
    pass
