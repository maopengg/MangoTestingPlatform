# # -*- coding: utf-8 -*-
# # @Project: 芒果测试平台
# # @Description:
# # @Time   : 2023-03-25 18:54
# # @Author : 毛鹏
# from urllib.parse import urlparse
#
# from rest_framework import serializers
# from rest_framework.decorators import action
# from rest_framework.request import Request
# from rest_framework.viewsets import ViewSet
#
# from src.auto_test.auto_system.consumers import ChatConsumer
# from src.auto_test.auto_system.models import TestObject, ProjectProduct
# from src.auto_test.auto_ui.models import UiConfig
# from src.auto_test.auto_user.models import User
# from src.auto_test.auto_user.views.user import UserSerializers
# from src.enums.socket_api_enum import UiSocketEnum
# from src.enums.system_enum import ClientTypeEnum
# from src.enums.tools_enum import StatusEnum, AutoTypeEnum
# from src.models.socket_model import SocketDataModel, QueueModel
# from src.models.ui_model import RecordingModel
# from src.tools.decorator.error_response import error_response
# from src.tools.view.model_crud import ModelCRUD
# from src.tools.view.response_data import ResponseData
# from src.tools.view.response_msg import *
#
#
# class UiConfigSerializers(serializers.ModelSerializer):
#     create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
#     update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
#
#     class Meta:
#         model = UiConfig
#         fields = '__all__'
#
#
# class UiConfigSerializersC(serializers.ModelSerializer):
#     create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
#     update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
#     user = UserSerializers(read_only=True)
#
#     class Meta:
#         model = UiConfig
#         fields = '__all__'
#
#     @staticmethod
#     def setup_eager_loading(queryset):
#         queryset = queryset.select_related(
#             'user_id')
#         return queryset
#
#
# class UiConfigCRUD(ModelCRUD):
#     model = UiConfig
#     queryset = UiConfig.objects.all()
#     serializer_class = UiConfigSerializersC
#     serializer = UiConfigSerializers
#
#
# class UiConfigViews(ViewSet):
#     model = UiConfig
#     serializer_class = UiConfigSerializers
#
#     @action(methods=['put'], detail=False)
#     @error_response('ui')
#     def put_status(self, request: Request):
#         """
#         获取操作类型
#         :param request:
#         :return:
#         """
#         status = request.data.get('status')
#         web_max = request.data.get('web_max')
#         web_recording = request.data.get('web_recording')
#         web_headers = request.data.get('web_headers')
#         obj = self.model.objects.get(id=request.data.get('id'))
#
#         if status is not None:
#             obj_list = self.model.objects.filter(user_id=obj.user_id)
#             for i in obj_list:
#                 if i.status == StatusEnum.SUCCESS.value and i.type == obj.type and i.id != obj.id:
#                     return ResponseData.fail(RESPONSE_MSG_0056)
#             obj.status = status
#             obj.save()
#             return ResponseData.success(RESPONSE_MSG_0057, )
#         if web_headers is not None:
#             obj.config['web_headers'] = web_headers
#             obj.save()
#             return ResponseData.success(RESPONSE_MSG_0057, )
#         if web_max is not None:
#             obj.config['web_max'] = web_max
#             obj.save()
#             return ResponseData.success(RESPONSE_MSG_0057, )
#         if web_recording is not None:
#             obj.config['web_recording'] = web_recording
#             obj.save()
#             return ResponseData.success(RESPONSE_MSG_0057, )
#
#
