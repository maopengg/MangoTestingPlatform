# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiInfo
from PyAutoTest.auto_test.auto_api.service.driver.dependence import ApiDataHandle
from PyAutoTest.auto_test.auto_api.service.driver.http_request import HTTPRequest
from PyAutoTest.enums.api_enum import MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel


class ApiInfoRun(ApiDataHandle):

    def __init__(self, project_id: int, test_obj_id: int):
        super().__init__(project_id, test_obj_id)

    def api_info_run(self, api_info_id: int) -> ResponseDataModel:
        api_info_obj = self.get_api_info_obj(api_info_id)
        request_data_model = self.request_data(RequestDataModel(
            method=MethodEnum(api_info_obj.method).name,
            url=urljoin(self.test_object.value, api_info_obj.url),
            headers=api_info_obj.header if api_info_obj.header else '${headers}',
            params=api_info_obj.params,
            data=api_info_obj.data,
            json_data=api_info_obj.json,
            file=api_info_obj.file))
        response: ResponseDataModel = HTTPRequest.http(request_data_model)
        if response.status_code != 500:
            api_info_obj.status = StatusEnum.SUCCESS.value
            api_info_obj.save()
        return response

    @classmethod
    def get_api_info_obj(cls, api_info_id: int):
        return ApiInfo.objects.get(id=api_info_id)
