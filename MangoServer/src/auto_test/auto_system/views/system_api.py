# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import re
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.enums.api_enum import *
from src.enums.system_enum import *
from src.enums.tools_enum import *
from src.enums.ui_enum import *
from src.exceptions import MangoServerError
from src.tools.decorator.error_response import error_response
from src.tools.redis.redis import Cache
from src.tools.view import *
from mangokit import NoticeEnum
from mangokit import ObtainRandomData
from mangokit.tools.method import class_methods


class SystemViews(ViewSet):
    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_api(self, request: Request):
        enum_dict = {
            'cline_type': ClientTypeEnum.get_option(),
            'method': MethodEnum.get_option(),
            'api_public_type': ApiPublicTypeEnum.get_option(),
            'api_client': ApiClientEnum.get_option(),
            'notice': NoticeEnum.get_option(),
            'status': StatusEnum.get_option(),
            'drive_type': DriveTypeEnum.get_option(),
            'browser_type': BrowserTypeEnum.get_option(),
            'element_exp': ElementExpEnum.get_option(),
            'auto_test_type': AutoTestTypeEnum.get_option(),
            'case_level': CaseLevelEnum.get_option(),
            'ui_public': UiPublicTypeEnum.get_option(),
            'element_ope': ElementOperationEnum.get_option(),
            'api_parameter_type': ApiParameterTypeEnum.get_option(),
            'device': DeviceEnum.obj(),
            'product_type': ProductTypeEnum.get_option(),
            'auto_type': AutoTypeEnum.get_option(),
            'task_status': TaskEnum.get_option(),
            'environment_type': EnvironmentEnum.get_option(),
        }
        return ResponseData.success(RESPONSE_MSG_0076, enum_dict)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def common_variable(self, request: Request):
        """
        返回公共变量页
        @param request:
        @return:
        """
        return ResponseData.success(RESPONSE_MSG_0061, [i.model_dump() for i in class_methods(ObtainRandomData)])

    @action(methods=['get'], detail=False)
    @error_response('system')
    def random_data(self, request: Request):
        name = request.GET.get("name")
        res1 = name.replace("${", "")
        name: str = res1.replace("}", "").strip()
        if not name:
            return ResponseData.fail(RESPONSE_MSG_0063)
        match = re.search(r'\((.*?)\)', name)
        if match:
            try:
                return ResponseData.success(RESPONSE_MSG_0062, str(ObtainRandomData().regular(name)))
            except MangoServerError as error:
                return ResponseData.fail((error.code, error.msg), )
        else:
            if Cache().read_data_from_cache(name):
                return ResponseData.success(RESPONSE_MSG_0062, Cache().read_data_from_cache(name))
            else:
                return ResponseData.fail(RESPONSE_MSG_0060)
