# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import re

from mangotools.decorator import get_data_method_info
from mangotools.enums import NoticeEnum
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from django.conf import settings
from src.common.enums.api_enum import *
from src.common.enums.data_factory_enum import *
from src.common.enums.monitoring_enum import MonitoringTaskStatusEnum, MonitoringLogStatusEnum
from src.common.enums.pytest_enum import *
from src.common.enums.system_enum import *
from src.common.enums.tools_enum import *
from src.common.enums.ui_enum import *
from src.common.exceptions import MangoServerError
from src.common.tools.decorator.error_response import error_response
from src.common.tools.obtain_assertion import ObtainAssertion, func_info as assertion_func_info
from src.common.tools.obtain_test_data import ObtainTestData
from src.common.tools.view import *


class SystemViews(ViewSet):
    @staticmethod
    def _find_assertion_method(method_name: str):
        for type_group in assertion_func_info:
            for class_group in type_group.get('children') or []:
                for method in class_group.get('children') or []:
                    if method.get('value') == method_name:
                        return method
        return None

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_api(self, request: Request):
        enum_dict = {
            'cline_type': ClientTypeEnum.get_option(),
            'method': MethodEnum.get_option(),
            'api_public_type': ApiPublicTypeEnum.get_option(),
            'api_auth_type': ApiAuthTypeEnum.get_option(),
            'api_auth_refresh_mode': ApiAuthRefreshModeEnum.get_option(),
            'api_auth_refresh_status': ApiAuthRefreshStatusEnum.get_option(),
            'api_client': ApiClientEnum.get_option(),
            'notice': NoticeEnum.get_option(),
            'status': StatusEnum.get_option(),
            'drive_type': DriveTypeEnum.get_option(),
            'browser_type': BrowserTypeEnum.get_option(),
            'element_exp': ElementExpEnum.get_option(),
            'case_level': CaseLevelEnum.get_option(),
            'ui_public': UiPublicTypeEnum.get_option(),
            'element_ope': ElementOperationEnum.get_option(),
            'api_parameter_type': ApiParameterTypeEnum.get_option(),
            'api_case_scenario_layer': ApiCaseScenarioLayerEnum.get_option(),
            'api_case_scenario_type': ApiCaseScenarioTypeEnum.get_option(),
            'api_case_scenario_tag': ApiCaseScenarioTagEnum.get_option(),
            'product_type': ProductTypeEnum.get_option(),
            'auto_type': AutoTypeEnum.get_option(),
            'database_type': DatabaseTypeEnum.get_option(),
            'data_factory_source_mode': DataFactorySourceModeEnum.get_option(),
            'data_factory_operation_type': DataFactoryOperationTypeEnum.get_option(),
            'data_factory_generator_type': DataFactoryGeneratorTypeEnum.get_option(),
            'data_factory_cleanup_strategy': DataFactoryCleanupStrategyEnum.get_option(),
            'data_factory_template_config_status': DataFactoryTemplateConfigStatusEnum.get_option(),
            'data_factory_template_usage_scope': DataFactoryTemplateUsageScopeEnum.get_option(),
            'data_factory_execution_source': DataFactoryExecutionSourceEnum.get_option(),
            'data_factory_execution_stage': DataFactoryExecutionStageEnum.get_option(),
            'data_factory_execution_status': DataFactoryExecutionStatusEnum.get_option(),
            'data_factory_cleanup_status': DataFactoryCleanupStatusEnum.get_option(),
            'task_status': TaskEnum.get_option(),
            'environment_type': EnvironmentEnum.get_option(),
            'test_case_type': TestCaseTypeEnum.get_option(),
            'file_status': FileStatusEnum.get_option(),
            'monitoring_task_status': MonitoringTaskStatusEnum.get_option(),
            'monitoring_log_status': MonitoringLogStatusEnum.get_option(),
            'test_suite_notice': TestSuiteNoticeEnum.get_option(),
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
        return ResponseData.success(RESPONSE_MSG_0061, get_data_method_info())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def random_data(self, request: Request):
        name = (request.GET.get("name") or "").strip()
        if name.startswith("${{") and name.endswith("}}"):
            name = name[3:-2].strip()
        elif name.startswith("${") and name.endswith("}"):
            name = name[2:-1].strip()
        if not name:
            return ResponseData.fail(RESPONSE_MSG_0063)
        match = re.search(r'\((.*?)\)', name)
        if match:
            try:
                return ResponseData.success(RESPONSE_MSG_0062, str(ObtainTestData().regular(name)))
            except MangoServerError as error:
                return ResponseData.fail((error.code, error.msg), )
        return ResponseData.fail(RESPONSE_MSG_0060)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def assertion_list(self, request: Request):
        """
        返回断言方法页
        @param request:
        @return:
        """
        return ResponseData.success((200, '获取断言方法成功'), assertion_func_info)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def assertion_test(self, request: Request):
        method = (request.data.get('method') or '').strip()
        if not method:
            return ResponseData.fail((300, '请先选择断言方法'))
        if not self._find_assertion_method(method):
            return ResponseData.fail(RESPONSE_MSG_0060)

        actual = request.data.get('actual')
        expect = request.data.get('expect')
        try:
            message = ObtainAssertion().ass(method=method, actual=actual, expect=expect)
            return ResponseData.success((200, '断言执行完成'), {
                'status': True,
                'message': message or '断言通过',
            })
        except Exception as error:
            return ResponseData.success((200, '断言执行完成'), {
                'status': False,
                'message': str(error),
            })

    @action(methods=['post'], detail=False)
    @error_response('system')
    def set_debug_log(self, request: Request):
        is_debug = request.data.get('is_debug')
        if is_debug is not None:
            settings.IS_DEBUG_LOG = is_debug
        return ResponseData.success(RESPONSE_MSG_0136, data={'is_debug': settings.IS_DEBUG_LOG})


class SystemShareViews(SystemViews):
    authentication_classes = []
