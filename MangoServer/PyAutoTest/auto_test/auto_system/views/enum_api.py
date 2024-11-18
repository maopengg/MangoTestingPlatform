# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-01-08 15:51
# @Author : 毛鹏
import logging

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.enums.api_enum import *
from PyAutoTest.enums.system_enum import *
from PyAutoTest.enums.tools_enum import *
from PyAutoTest.enums.ui_enum import *
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *

log = logging.getLogger('system')


class EnumOptionViews(ViewSet):
    """枚举类api"""

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_client(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, ClientTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_method(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, MethodEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_api_public(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, ApiPublicTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_end(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, ClientEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_notice(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, NoticeEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_status(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, StatusEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_environment(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, EnvironmentEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_platform(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, DriveTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_browser(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, BrowserTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_drive(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, DriveTypeEnum.get_option(k='value', v='label'))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_exp(self, request):
        return ResponseData.success(RESPONSE_MSG_0076, ElementExpEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_autotest(self, request):
        return ResponseData.success(RESPONSE_MSG_0076, AutoTestTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_case_level(self, request):
        return ResponseData.success(RESPONSE_MSG_0106, CaseLevelEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_ui_public(self, request):
        return ResponseData.success(RESPONSE_MSG_0106, UiPublicTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_ui_element_operation(self, request):
        return ResponseData.success(RESPONSE_MSG_0106, ElementOperationEnum.get_option(k='value', v='label'))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_api_parameter_type(self, request):
        return ResponseData.success(RESPONSE_MSG_0106, ApiParameterTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_ui_device_type(self, request):
        return ResponseData.success(RESPONSE_MSG_0106, DeviceEnum.obj())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_product_type(self, request):
        return ResponseData.success(RESPONSE_MSG_0106, ProductTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_auto_type(self, request):
        return ResponseData.success(RESPONSE_MSG_0106, AutoTypeEnum.get_option())
