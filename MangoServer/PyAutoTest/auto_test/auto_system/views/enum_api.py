# -*- coding: utf-8 -*-
# @Project: auto_test
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
from PyAutoTest.tools.view_utils.response_data import ResponseData
from PyAutoTest.tools.view_utils.response_msg import *

log = logging.getLogger('system')


class EnumOptionViews(ViewSet):
    """枚举类api"""

    @action(methods=['get'], detail=False)
    def enum_client(self, request: Request):
        """
        端类型
        @param request: 
        @return: 
        """
        return ResponseData.success(RESPONSE_MSG_0076, ClientTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_method(self, request: Request):
        """
        获取客户端类型
        :param request:
        :return:
        """
        return ResponseData.success(RESPONSE_MSG_0076, MethodEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_api_public(self, request: Request):
        """
        获取公共类型
        :param request:
        :return:
        """
        return ResponseData.success(RESPONSE_MSG_0076, ApiPublicTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_end(self, request: Request):
        """
        获取客户端类型
        :param request:
        :return:
        """
        return ResponseData.success(RESPONSE_MSG_0076, ClientEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_notice(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, NoticeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_status(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0076, StatusEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_environment(self, request: Request):
        """
         获取环境信息
         :param request:
         :return:
         """
        return ResponseData.success(RESPONSE_MSG_0076, EnvironmentEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_platform(self, request: Request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        return ResponseData.success(RESPONSE_MSG_0076, DriveTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_browser(self, request: Request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success(RESPONSE_MSG_0076, BrowserTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_drive(self, request: Request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success(RESPONSE_MSG_0076, DriveTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_exp(self, request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success(RESPONSE_MSG_0076, ElementExpEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_autotest(self, request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success(RESPONSE_MSG_0076, AutoTestTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_case_level(self, request):
        """
        获取用例级别
        :param request:
        :return:
        """
        return ResponseData.success(RESPONSE_MSG_0106, CaseLevelEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_ui_public(self, request):
        """
        获取用例级别
        :param request:
        :return:
        """
        return ResponseData.success(RESPONSE_MSG_0106, UiPublicTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_ui_element_operation(self, request):
        """
        获取元素操作类型
        :param request:
        :return:
        """
        return ResponseData.success(RESPONSE_MSG_0106, ElementOperationEnum.get_option(k='value', v='label'))
