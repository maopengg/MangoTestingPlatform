# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
from urllib.parse import urljoin

from src.auto_test.auto_api.models import ApiInfo
from src.auto_test.auto_api.service.base_tools.case_base import CaseBase
from src.enums.api_enum import MethodEnum
from src.enums.tools_enum import StatusEnum, TaskEnum
from src.models.api_model import RequestDataModel, ResponseDataModel
from src.tools.log_collector import log


class TestApiInfo(CaseBase):

    def __init__(self, user_id, test_env: int):
        super().__init__(user_id, test_env)

    def api_info_run(self, api_info_id: int) -> ResponseDataModel:
        self.api_info = ApiInfo.objects.get(id=api_info_id)
        self.api_info.status = TaskEnum.PROCEED.value
        self.api_info.save()
        self.project_product_id = self.api_info.project_product.id
        self.init_test_object()
        self.init_public()
        request_data = self.request_data_clean(RequestDataModel(
            method=MethodEnum(self.api_info.method).name,
            url=urljoin(self.test_object.value, self.api_info.url),
            headers=self.api_info.header if self.api_info.header else self.init_headers(),
            params=self.api_info.params,
            data=self.api_info.data,
            json_data=self.api_info.json,
            file=self.api_info.file))
        log.api.debug(f'接口调试请求数据：{request_data.model_dump_json()}')
        response: ResponseDataModel = self.http(request_data)
        response.name = self.api_info.name
        if response.status_code == 300 or response.status_code == 200:
            self.api_info.status = StatusEnum.SUCCESS.value
        else:
            self.api_info.status = StatusEnum.FAIL.value
        self.api_info.save()
        return response
