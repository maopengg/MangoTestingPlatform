# -*- coding: utf-8 -*-
from requests import RequestException
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.system.service.ai.client import AiConfigError, AiService
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import RESPONSE_MSG_0163


class AiViews(ViewSet):
    @action(methods=['post'], detail=False)
    @error_response('system')
    def test(self, request: Request):
        try:
            data = AiService.test_config()
        except (AiConfigError, RequestException) as error:
            return ResponseData.success(RESPONSE_MSG_0163, {
                "status": False,
                "message": str(error),
            })
        return ResponseData.success(RESPONSE_MSG_0163, {
            "status": True,
            "message": "AI配置测试成功",
            **data,
        })
