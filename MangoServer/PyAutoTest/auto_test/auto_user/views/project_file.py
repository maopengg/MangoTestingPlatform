# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-01 12:45
# @Author : 毛鹏
import logging
import os

from django.http import FileResponse
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from PyAutoTest.auto_test.auto_system.models import Project
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *
from PyAutoTest.auto_test.auto_system.service.mini_io.mini_io import MiniIo
#
#
#
# class ProjectFileViews(ViewSet):

# @action(methods=['get'], detail=False)
# def text.txt(self, request: Request):
#     FilesCRUD().initialization()
#     return ResponseData.success(RESPONSE_MSG_0026, FilesCRUD().get_project_all_list())

# @action(methods=['get'], detail=False)
# def get_project_all_list(self, request: Request):
#     return ResponseData.success(RESPONSE_MSG_0026, FilesCRUD().get_project_all_list())

# @action(methods=['post'], detail=False)
# def upload_files(self, request: Request):
#     project_id = request.headers.get('Project')
#     if not project_id:
#         return ResponseData.fail(RESPONSE_MSG_0028, )
#     project = Project.objects.get(project_id)
#     try:
#         file_obj = request.FILES['file']
#         MiniIo().file_object_write(project.bucket_name, file_obj.name, file_obj)
#         return ResponseData.success(RESPONSE_MSG_0027, )
#     except MangoServerError as error:
#         return ResponseData.fail((error.code, error.msg), )
#
# @action(methods=['get'], detail=False)
# def download_file(self, request: Request):
#     project_id = request.query_params.get('project_id')
#     file_name = request.query_params.get('file_name')
#     file_obj = FilesCRUD(project_id)
#     file_path = os.path.join(file_obj.project_upload_folder, file_name)
#     if os.path.exists(file_path):
#         response = FileResponse(open(file_path, 'rb'))
#         response['Content-Disposition'] = f'attachment; filename="{file_name}"'
#         return response
#     else:
#         return ResponseData.fail(RESPONSE_MSG_0029)
#
# @action(methods=['get'], detail=False)
# def delete_file(self, request: Request):
#     project_id = request.query_params.get('project_id')
#     file_name = request.query_params.get('file_name')
#     FilesCRUD(project_id).delete_file(file_name)
#     return ResponseData.success(RESPONSE_MSG_0030)
