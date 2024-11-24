# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiInfo
from PyAutoTest.auto_test.auto_api.service.base_tools.dependence import CaseMethod
from PyAutoTest.auto_test.auto_user.tools.factory import func_test_object_value
from PyAutoTest.enums.api_enum import MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum, AutoTypeEnum
from PyAutoTest.models.api_model import RequestDataModel, ResponseDataModel


class TestApiInfo(CaseMethod):

    def __init__(self, test_env: int, api_info_id: int):
        super().__init__()
        self.api_info = ApiInfo.objects.get(id=api_info_id)
        self.test_object = func_test_object_value(test_env,
                                                  self.api_info.project_product_id,
                                                  AutoTypeEnum.API.value)
        self.common_init(self.test_object, self.api_info.project_product_id)

    def api_info_run(self) -> ResponseDataModel:
        response: ResponseDataModel = self.send_request(RequestDataModel(
            method=MethodEnum(self.api_info.method).name,
            url=urljoin(self.test_object.value, self.api_info.url),
            headers=self.api_info.header,
            params=self.api_info.params,
            data=self.api_info.data,
            json_data=self.api_info.json,
            file=self.api_info.file), True)
        if response.status_code != 500:
            self.api_info.status = StatusEnum.SUCCESS.value
            self.api_info.save()
        return response
