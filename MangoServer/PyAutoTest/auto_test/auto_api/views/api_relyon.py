# # -*- coding: utf-8 -*-
# # @Project: MangoServer
# # @Description:
# # @Time   : 2023-02-17 21:39
# # @Author : 毛鹏
# from rest_framework import serializers
# from rest_framework.decorators import action
# from rest_framework.request import Request
# from rest_framework.viewsets import ViewSet
#
# from PyAutoTest.auto_test.auto_api.models import ApiRelyOn
# from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseSerializers
# from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
# from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
#
#
# class ApiRelyOnSerializers(serializers.ModelSerializer):
#     class Meta:
#         model = ApiRelyOn
#         fields = '__all__'
#
#
# class ApiRelyOnSerializersC(serializers.ModelSerializer):
#     project = ProjectSerializers(read_only=True)
#     case = ApiCaseSerializers(read_only=True)
#
#     class Meta:
#         model = ApiRelyOn
#         fields = '__all__'
#
#
# class ApiRelyOnCRUD(ModelCRUD):
#     model = ApiRelyOn
#     queryset = ApiRelyOn.objects.all()
#     serializer_class = ApiRelyOnSerializersC
#     serializer = ApiRelyOnSerializers
#
#
# class ApiRelyOnViews(ViewSet):
#     model = ApiRelyOn
#     serializer_class = ApiRelyOnSerializers
#
#     @action(methods=['put'], detail=False)
#     def test(self, request: Request):
#         pass
