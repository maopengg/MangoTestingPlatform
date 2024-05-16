# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiInfo
from PyAutoTest.auto_test.auto_api.service.base.dependence import CaseMethod
from PyAutoTest.auto_test.auto_api.service.base.http_base import HTTPRequest
from PyAutoTest.enums.api_enum import MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel


class ApiInfoRun(CaseMethod):

    def __init__(self, test_obj_id: int, api_info_id: int):
        super().__init__()
        self.api_info = ApiInfo.objects.get(id=api_info_id)
        self.common_init(test_obj_id, self.api_info.project_product_id)

    def api_info_run(self) -> ResponseDataModel:
        request_data_model = self.request_data(RequestDataModel(
            method=MethodEnum(self.api_info.method).name,
            url=urljoin(self.test_object.value, self.api_info.url),
            headers=self.api_info.header if self.api_info.header else '${headers}',
            params=self.api_info.params,
            data=self.api_info.data,
            json_data=self.api_info.json,
            file=self.api_info.file), True)
        response: ResponseDataModel = HTTPRequest().http(request_data_model)
        if response.status_code != 500:
            self.api_info.status = StatusEnum.SUCCESS.value
            self.api_info.save()
        return response

    @classmethod
    def get_api_info_obj(cls, api_info_id: int):
        return
