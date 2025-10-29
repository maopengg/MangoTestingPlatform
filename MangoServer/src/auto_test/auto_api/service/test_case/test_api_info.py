# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

from src.auto_test.auto_api.models import ApiInfo
from src.auto_test.auto_api.service.base.api_base_test_setup import APIBaseTestSetup
from src.enums.tools_enum import StatusEnum, TaskEnum
from src.models.api_model import ResponseModel
from src.tools.log_collector import log


class TestApiInfo:

    def __init__(self, user_id, test_env: int):
        self.user_id = user_id
        self.test_env = test_env
        self.test_setup = APIBaseTestSetup()

    def api_info_run(self, api_info_id: int) -> dict:
        api_info = ApiInfo.objects.get(id=api_info_id)
        try:
            api_info.status = TaskEnum.PROCEED.value
            api_info.save()
            response = self.test_setup.api_request(api_info.id, self.test_env, is_merge_headers=True)
            api_info.status = TaskEnum.SUCCESS.value
            api_info.save()
            return self.save_api_info(api_info, response)
        except Exception as error:
            log.api.debug(f'API执行报错：{error}')
            api_info.status = TaskEnum.FAIL.value
            api_info.save()
            raise error

    def save_api_info(self, api_info: ApiInfo, response: ResponseModel):
        api_info.status = api_info.status = StatusEnum.SUCCESS.value if response.code == 300 or response.code == 200 else StatusEnum.FAIL.value
        res = response.model_dump()
        res['name'] = api_info.name
        res['cache_all'] = self.test_setup.test_data.get_all()
        api_info.result_data = res
        api_info.save()
        return res
