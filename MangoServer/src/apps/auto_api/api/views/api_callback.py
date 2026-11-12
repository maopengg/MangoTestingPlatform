from rest_framework.viewsets import ViewSet
from django.http import HttpResponse

from src.apps.auto_api.models import ApiCaseCallbackRun
from src.apps.auto_api.api.serializers.api_callback import (
    CallbackQuerySerializer, CallbackDeliveryQuerySerializer, CallbackDownloadQuerySerializer,
)
from src.apps.auto_api.selectors.callback import ApiCallbackSelector
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001


class ApiCallbackViews(ViewSet):
    model = ApiCaseCallbackRun
    serializer_class = CallbackQuerySerializer

    @error_response('api')
    def results(self, request):
        """获取 API 回调验证结果"""
        query = CallbackQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return ResponseData.success(RESPONSE_MSG_0001, ApiCallbackSelector.results(
            user=getattr(request.user, 'user_obj', None), **query.validated_data,
        ))

    @error_response('api')
    def deliveries(self, request):
        """获取 API 回调投递记录"""
        query = CallbackDeliveryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return ResponseData.success(RESPONSE_MSG_0001, ApiCallbackSelector.deliveries(
            user=getattr(request.user, 'user_obj', None), **query.validated_data,
        ))

    @error_response('api')
    def download(self, request):
        """下载 API 回调验证原始证据"""
        from src.common.logging import log
        query = CallbackDownloadQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        user = getattr(request.user, 'user_obj', None)
        body = ApiCallbackSelector.download(user=user, **query.validated_data)
        delivery_id = query.validated_data['delivery_id']
        log.api.info(f'导出回调原始证据：user={user.id}, delivery={delivery_id}')
        response = HttpResponse(body, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="callback-{delivery_id}.bin"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
