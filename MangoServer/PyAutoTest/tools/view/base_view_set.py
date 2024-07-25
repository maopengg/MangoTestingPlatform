# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-07-25 上午10:19
# @Author : 毛鹏
from rest_framework.viewsets import ViewSet


class BaseViewSet(ViewSet):
    # @error_response()
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
