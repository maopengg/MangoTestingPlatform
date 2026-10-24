# -*- coding: utf-8 -*-
from requests import RequestException
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.exceptions import AiError
from src.apps.system.services.ai.client import AiService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0163


class AiViews(ViewSet):
    action_permission_map = {
        'test': 'system.settings:debug',
    }

    @action(methods=['post'], detail=False)
    @error_response('system')
    def test(self, request: Request):
        try:
            capability = str(request.data.get('capability') or 'text').strip().lower()
            data = AiService.test_config(capability)
        except (AiError, RequestException) as error:
            return ResponseData.success(RESPONSE_MSG_0163, {
                "status": False,
                "message": str(error),
            })
        return ResponseData.success(RESPONSE_MSG_0163, {
            "status": True,
            "message": "视觉模型配置测试成功" if capability == 'vision' else "文本模型配置测试成功",
            **data,
        })
