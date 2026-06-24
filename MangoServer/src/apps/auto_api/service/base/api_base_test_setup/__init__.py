# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-07-04 17:18
# @Author : 毛鹏
import re
import traceback
from urllib.parse import urlparse, urljoin

from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.models import ApiInfo
from src.apps.auto_api.service.base.api_base_test_setup.base_request import BaseRequest
from src.apps.auto_api.service.base.api_base_test_setup.public_base import PublicBase
from src.common.enums.api_enum import MethodEnum
from src.common.exceptions import *
from src.common.models.api_model import RequestModel, ResponseModel
from src.common.tools.json_response import ensure_jsonpath_source


class APIBaseTestSetup(PublicBase):

    def api_request(self,
                    api_info_id,
                    test_env: int,
                    request_model: RequestModel = None,
                    ) -> ResponseModel:
        api_info = ApiInfo.objects.get(id=api_info_id)
        log.api.debug(f'执行API接口-1->ID:{api_info_id},name:{api_info.name}')
        previous_api_info_id = self.current_api_info_id
        self.current_api_info_id = api_info.id
        try:
            self.init_test_object(api_info.project_product_id, test_env)
            self.init_public(api_info.project_product_id, test_env)
        finally:
            self.current_api_info_id = previous_api_info_id
        # API info的请求
        if request_model is None:
            if api_info.headers is not None:
                headers = api_info.headers
            else:
                headers = self.init_headers(api_info.project_product_id)
            request_model = RequestModel(
                method=MethodEnum(api_info.method).name,
                url=api_info.url,
                headers=headers,
                params=api_info.params,
                protocol_type=api_info.protocol_type,
                body_type=api_info.body_type,
                body_config=api_info.body_config,
                sse_config=api_info.sse_config,
                posterior_file=api_info.posterior_file,
            )
        response = self.http(self.request_data_clean(request_model), api_info.project_product_id)
        try:
            if api_info.posterior_re:
                self.api_info_posterior_json_re(api_info.posterior_re, response)
            if api_info.posterior_json_path:
                self.api_info_posterior_json_path(api_info.posterior_json_path, response)
            if api_info.posterior_func:
                self.execute_analytic_func(api_info.posterior_func, self, response, error_msg=ERROR_MSG_0069)
            return response
        except (MangoServerError, MangoToolsError) as error:
            response.error_msg = error.msg
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
                elif key in {'body_config', 'sse_config', 'request_body', 'request_files', 'request_content_type'}:
                    continue
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
        ensure_jsonpath_source(response.json)
        for i in posterior_json_path:
            key: str = self.test_data.replace(i.get('key'))
            value: str = self.test_data.replace(i.get('value'))
            if not key or not value:
                raise ApiError(*ERROR_MSG_0006)
            if key and key.startswith('$.'):
                key = self.test_data.get_json_path_value(response.json, i.get('key'))
            self.test_data.set_cache(key, self.test_data.get_json_path_value(response.json, value))

    def api_info_posterior_json_re(self, posterior_re, response: ResponseModel):
        log.api.debug(f'执行API接口-3->后置正则:{posterior_re}')
        if response.text is None:
            raise ApiError(*ERROR_MSG_0015)
        for i in posterior_re:
            key: str = self.test_data.replace(i.get('key'))
            value: str = self.test_data.replace(i.get('value'))
            if not key or not value:
                raise ApiError(*ERROR_MSG_0018)
            try:
                res = re.findall(value, response.text)
            except re.error as error:
                raise ApiError(*ERROR_MSG_0091, value=(value, str(error))) from error
            if len(res) <= 0:
                raise ApiError(*ERROR_MSG_0017)
            self.test_data.set_cache(key, res[0])

    def analytic_func(self, func_str, func_name='func'):
        func_str = self.test_data.replace(func_str)
        log.api.debug(f'执行API接口-5->后置函数:{func_str}')
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

    def execute_analytic_func(self, func_str, *args, error_msg=ERROR_MSG_0014):
        try:
            return self.analytic_func(func_str)(*args)
        except MangoServerError as error:
            raise ApiError(*error_msg, value=(error.msg,)) from error
        except MangoToolsError as error:
            raise ApiError(*error_msg, value=(error.msg,)) from error
        except Exception as error:
            log.api.error(
                f'自定义函数执行失败，函数字符串：{func_str}，失败类型：{error}，失败明细：{traceback.format_exc()}')
            raise ApiError(*error_msg, value=(str(error),)) from error
