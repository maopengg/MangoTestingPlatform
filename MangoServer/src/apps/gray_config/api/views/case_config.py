# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.gray_config.api.serializers.gray_config import AutomationCaseGrayConfigSerializer, \
    AutomationCaseGrayConfigSerializerC
from src.apps.gray_config.api.views.base import LastUpdateUserCRUD
from src.apps.gray_config.models import AutomationCaseGrayConfig
from src.apps.gray_config.services.case_config import GrayCaseConfigService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0235


class DeprecatedCaseGrayConfigApiMixin:
    """保留旧调用兼容，但明确阻止新调用方继续依赖 Case 灰度绑定接口。"""

    deprecation_warning = '299 mango-testing-platform "API Case gray binding endpoint is deprecated"'

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Deprecation'] = 'true'
        response['Warning'] = self.deprecation_warning
        return response


class AutomationCaseGrayConfigCRUD(DeprecatedCaseGrayConfigApiMixin, LastUpdateUserCRUD):
    """已废弃：仅用于兼容历史 HTTP 调用，不再提供页面或 MCP 入口。"""

    model = AutomationCaseGrayConfig
    queryset = AutomationCaseGrayConfig.objects.all()
    serializer_class = AutomationCaseGrayConfigSerializerC
    serializer = AutomationCaseGrayConfigSerializer
    page_permission_key = 'gray.feature'
    not_matching_str = LastUpdateUserCRUD.not_matching_str + [
        'case_type',
        'scope',
        'api_case',
        'ui_case',
        'api_case_detailed',
        'api_case_detailed_parameter',
        'gray_feature',
    ]


class AutomationCaseGrayConfigViews(DeprecatedCaseGrayConfigApiMixin, ViewSet):
    """已废弃：仅用于兼容历史批量保存与范围替换调用。"""

    action_permission_map = {
        'batch_save': 'gray.feature:edit',
        'replace_scope': 'gray.feature:edit',
    }

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_save(self, request: Request):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        return ResponseData.success(
            RESPONSE_MSG_0235,
            GrayCaseConfigService.save_configs(request.data.get('items') or [], user=user),
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def replace_scope(self, request: Request):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        return ResponseData.success(
            RESPONSE_MSG_0235,
            GrayCaseConfigService.replace_scope_configs(
                request.data.get('scope') or {},
                request.data.get('items') or [],
                user=user,
            ),
        )
