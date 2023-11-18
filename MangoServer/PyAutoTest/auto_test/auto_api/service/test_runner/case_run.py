# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
from requests import Response

from PyAutoTest.auto_test.auto_api.models import ApiInfo
from PyAutoTest.auto_test.auto_api.service.driver.dependence import Dependence
from PyAutoTest.auto_test.auto_api.service.driver.http_request import HTTPRequest
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.enums.api_enum import MethodEnum
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from urllib.parse import urljoin

class ApiInfoRun(HTTPRequest, Dependence):

    def api_info_run(self, api_info_id: int, test_obj_id: int):
        api_info = ApiInfo.objects.get(id=api_info_id)
        test_object = TestObject.objects.get(id=test_obj_id)

        request_data_model = RequestDataModel(method=MethodEnum(api_info.method).name,
                                              url=urljoin(test_object.value, api_info.url),
                                              headers=api_info.header,
                                              params=api_info.params,
                                              data=api_info.data,
                                              json_data=api_info.json,
                                              file=None)
        response: Response = self.http(request_data_model)
        return ResponseDataModel(url=response.url,
                                 status_code=response.status_code,
                                 method=MethodEnum(api_info.method).name,
                                 headers=response.headers,
                                 params=api_info.params,
                                 data=api_info.data,
                                 json_data=api_info.json,
                                 file=None,
                                 text=response.text,
                                 response_json=response.json())
