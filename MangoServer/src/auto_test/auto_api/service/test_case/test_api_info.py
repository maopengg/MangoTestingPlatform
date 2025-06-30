# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import traceback

from src.auto_test.auto_api.models import ApiInfo
from src.auto_test.auto_api.service.base.api_info import ApiInfoBase
from src.enums.tools_enum import StatusEnum, TaskEnum
from src.models.api_model import ResponseModel


class TestApiInfo(ApiInfoBase):

    def __init__(self, user_id, test_env: int):
        super().__init__(user_id, test_env)

    def api_info_run(self, api_info_id: int) -> dict:
        api_info = ApiInfo.objects.get(id=api_info_id)
        try:
            api_info.status = TaskEnum.PROCEED.value
            api_info.save()
            self.init_test_object(api_info.project_product_id)
            self.init_public(api_info.project_product_id)
            response = self.api_request(api_info.id)
            api_info.status = TaskEnum.SUCCESS.value
            api_info.save()
            return self.save_api_info(api_info, response)
        except Exception as error:
            traceback.print_exc()
            api_info.status = TaskEnum.FAIL.value
            api_info.save()
            raise error

    def save_api_info(self, api_info: ApiInfo, response: ResponseModel):
        if response.code == 300 or response.code == 200:
            api_info.status = StatusEnum.SUCCESS.value
        else:
            api_info.status = StatusEnum.FAIL.value
        res = response.model_dump()
        res['name'] = api_info.name

        res['cache_all'] = self.test_data.get_all()
        api_info.result_data = res
        api_info.save()
        return res
