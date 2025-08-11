# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-07-04 17:18
# @Author : 毛鹏
import mimetypes
import traceback
from urllib.parse import urlparse, urljoin

from mangotools.exceptions import MangoToolsError

from src.auto_test.auto_api.models import ApiInfo
from src.auto_test.auto_api.service.base.api_base_test_setup.base_request import BaseRequest
from src.auto_test.auto_api.service.base.api_base_test_setup.public_base import PublicBase
from src.enums.api_enum import MethodEnum
from src.exceptions import *
from src.models.api_model import RequestModel, ResponseModel


class APIBaseTestSetup(PublicBase):


    def api_request(self,
                    api_info_id,
                    test_env: int,
                    request_model: RequestModel = None,
                    is_merge_headers=False,
                    is_error=False,
                    ) -> ResponseModel:
        api_info = ApiInfo.objects.get(id=api_info_id)
        log.api.debug(f'执行API接口-1->ID:{api_info_id},name:{api_info.name}')
        self.init_public(api_info.project_product_id, test_env)
        self.init_test_object(api_info.project_product_id, test_env)
        # API info的请求
        if request_model is None:
            if is_merge_headers and api_info.headers:
                headers = self.init_headers(api_info.project_product_id)
                self.update_dict_case_insensitive(headers, api_info.headers)
            elif api_info.headers is not None:
                headers = api_info.headers
            else:
                headers = self.init_headers(api_info.project_product_id)
            request_model = RequestModel(
                method=MethodEnum(api_info.method).name,
                url=api_info.url,
                headers=headers,
                params=api_info.params,
                data=api_info.data,
                json=api_info.json,
                file=api_info.file,
                posterior_file=api_info.posterior_file,
            )
        response = self.http(self.request_data_clean(request_model))
        try:
            if api_info.posterior_re:
                self.api_info_posterior_json_re(api_info.posterior_re, response)
            if api_info.posterior_json_path:
                self.api_info_posterior_json_path(api_info.posterior_json_path, response)
            if api_info.posterior_func:
                self.analytic_func(api_info.posterior_func)(self, response)
            return response
        except (MangoServerError, MangoToolsError) as error:
            if is_error:
                raise error
            return response

    def request_data_clean(self, request_data_model: RequestModel) -> RequestModel:
        log.api.debug(f'清洗请求数据-1->{request_data_model.model_dump_json()}')
        try:
            for key, value in request_data_model:
                if key == 'headers':
                    value = self.test_data.replace(value)
                    if value and isinstance(value, str):
                        value = self.test_data.loads(value) if value else value
                    setattr(request_data_model, key, value)
                elif key == 'file':
                    if request_data_model.file:
                        file = []
                        for i in request_data_model.file:
                            if not isinstance(i, dict):
                                raise ApiError(*ERROR_MSG_0025)
                            for k, v in i.items():
                                file_path = self.test_data.replace(v)
                                file_name = self.test_data.identify_parentheses(v)[0].replace('(', '').replace(')', '')
                                mime_type, _ = mimetypes.guess_type(file_path)
                                if mime_type is None:
                                    mime_type = 'application/octet-stream'
                                file.append((k, (file_name, open(file_path, 'rb'), mime_type)))
                        request_data_model.file = file
                else:
                    value = self.test_data.replace(value)
                    setattr(request_data_model, key, value)
            result = urlparse(request_data_model.url)
            if not all([result.scheme, result.netloc]):
                request_data_model.url = urljoin(self.test_object.value, request_data_model.url)
        except MangoToolsError as error:
            traceback.print_exc()
            raise ApiError(error.code, error.msg)
        log.api.debug(f'清洗请求数据-2->{request_data_model}')
        return request_data_model

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
