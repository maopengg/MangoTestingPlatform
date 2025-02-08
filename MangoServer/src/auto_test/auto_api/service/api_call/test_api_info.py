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

    def api_info_run(self, api_info_id: int) -> dict:
        api_info = ApiInfo.objects.get(id=api_info_id)
        api_info.status = TaskEnum.PROCEED.value
        api_info.save()
        self.project_product_id = api_info.project_product.id
        self.init_test_object()
        self.init_public()
        request_data = self.request_data_clean(RequestDataModel(
            method=MethodEnum(api_info.method).name,
            url=urljoin(self.test_object.value, api_info.url),
            headers=api_info.header if api_info.header else self.init_headers(),
            params=api_info.params,
            data=api_info.data,
            json_data=api_info.json,
            file=api_info.file))
        log.api.debug(f'接口调试请求数据：{request_data.model_dump_json()}')
        response: ResponseDataModel = self.http(request_data)
        self.api_info_front_json_re(api_info, response)
        self.api_info_front_json_path(api_info, response)
        return self.save_api_info(api_info, response)

    def save_api_info(self, api_info: ApiInfo, response: ResponseDataModel):
        if response.status_code == 300 or response.status_code == 200:
            api_info.status = StatusEnum.SUCCESS.value
        else:
            api_info.status = StatusEnum.FAIL.value
        res = response.model_dump()
        res['name'] = api_info.name

        res['cache_all'] = self.get_all()
        api_info.result_data = res
        api_info.save()
        return res
