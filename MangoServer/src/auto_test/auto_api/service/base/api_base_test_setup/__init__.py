# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-07-04 17:18
# @Author : 毛鹏
from urllib.parse import urljoin

from mangotools.exceptions import MangoToolsError

from src.auto_test.auto_api.models import ApiInfo
from src.auto_test.auto_api.service.base.api_base_test_setup.public_base import PublicBase
from src.enums.api_enum import MethodEnum
from src.exceptions import *
from src.models.api_model import RequestModel, ResponseModel


class APIBaseTestSetup(PublicBase):

    def api_request(self, api_info_id: int, request_model: RequestModel = None, is_error=True,
                    is_merge_headers=False) -> ResponseModel:
        log.api.debug(f'执行API接口-1->ID:{api_info_id}')
        api_info = ApiInfo.objects.get(id=api_info_id)
        if is_merge_headers and api_info.headers:
            headers = self.init_headers(api_info.project_product.id)
            headers.update(api_info.headers)
        elif api_info.headers is not None:
            headers = api_info.headers
        else:
            headers = self.init_headers(api_info.project_product.id)
        if request_model is None:
            request_model = self.request_data_clean(RequestModel(
                method=MethodEnum(api_info.method).name,
                url=urljoin(self.test_object.value, api_info.url),
                headers=headers,
                params=api_info.params,
                data=api_info.data,
                json=api_info.json,
                file=api_info.file))
        response = self.http(request_model)
        try:
            if api_info.posterior_re:
                self.api_info_posterior_json_re(api_info.posterior_re, response)
            if api_info.posterior_json_path:
                self.api_info_posterior_json_path(api_info.posterior_json_path, response)
            if api_info.posterior_func:
                self.analytic_func(api_info.posterior_func)(self, response)
        except MangoToolsError as error:
            if is_error:
                raise ApiError(error.code, error.msg)
        except Exception as error:
            log.api.error(f'api_info的请求失败，api_id:{api_info_id}, error:{error}')
            if is_error:
                raise error
        return response

    def api_info_posterior_json_path(self, posterior_json_path: list[dict], response: ResponseModel):
        log.api.debug(f'执行API接口-4->后置jsonpath:{posterior_json_path}')
        if response.json is None:
            raise ApiError(*ERROR_MSG_0023)
        for i in posterior_json_path:
            self.test_data.set_cache(i.get('key'), self.test_data.get_json_path_value(response.json, i.get('value')))

    def api_info_posterior_json_re(self, posterior_re: str, response: ResponseModel):
        log.api.debug(f'执行API接口-3->后置正则:{posterior_re}')

    @staticmethod
    def analytic_func(func_str, func_name='func'):
        log.api.debug(f'执行API接口-4->后置函数:{func_str}')
        try:
            global_namespace = {}
            exec(func_str, global_namespace)
            return global_namespace[func_name]
        except Exception as error:
            log.api.warning(f'函数字符串：{func_str}')
            import traceback
            log.api.error(
                f'自定义函数执行失败，函数字符串：{func_str}，失败类型：{error}，失败明细：{traceback.format_exc()}')
            raise ToolsError(*ERROR_MSG_0014)
