# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏

from django.db import connection

from src.auto_test.auto_pytest.models import PytestCase
from src.exceptions import *
from src.models.pytest_model import PytestCaseResultModel
from src.tools.decorator.retry import async_task_db_connection


class PtestTestReportWriting:

    @classmethod
    @async_task_db_connection(max_retries=3, retry_delay=2)
    def update_pytest_test_case(cls, data: PytestCaseResultModel):
        log.ui.debug(f'开始写入Pytest用例<{data.name}>测试结果，用例的测试状态是：{data.status}')
        case = PytestCase.objects.get(id=data.id)
        case.status = data.status
        case.result_data = data.result_data
        case.save()
