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
        return ResponseData.success('获取枚举类型成功', ClientTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_method(self, request: Request):
        """
        获取客户端类型
        :param request:
        :return:
        """
        return ResponseData.success('获取枚举类型成功', MethodEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_public(self, request: Request):
        """
        获取公共类型
        :param request:
        :return:
        """
        return ResponseData.success('获取枚举类型成功', ApiPublicTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_end(self, request: Request):
        """
        获取客户端类型
        :param request:
        :return:
        """
        return ResponseData.success('获取枚举类型成功', ClientEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_notice(self, request: Request):
        return ResponseData.success('获取枚举类型成功', NoticeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_status(self, request: Request):
        return ResponseData.success('获取枚举类型成功', StatusEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_environment(self, request: Request):
        """
         获取环境信息
         :param request:
         :return:
         """
        return ResponseData.success('获取枚举类型成功', EnvironmentEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_platform(self, request: Request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        return ResponseData.success('获取枚举类型成功', DriveTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_browser(self, request: Request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success('获取枚举类型成功', BrowserTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_drive(self, request: Request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success('获取枚举类型成功', DriveTypeEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_exp(self, request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success('获取枚举类型成功', ElementExpEnum.get_option())

    @action(methods=['get'], detail=False)
    def enum_autotest(self, request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success('获取枚举类型成功', AutoTestTypeEnum.get_option())
