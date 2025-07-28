# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 封装了分页查询，单条查询和增删改查
# @Time   : 2023-02-08 8:30
# @Author : 毛鹏
from threading import Thread

from django.core.exceptions import FieldError, FieldDoesNotExist
from django.core.paginator import Paginator
from django.db.models.query import QuerySet
from mangotools.mangos import get, post, put, delete, inside_post, inside_put, inside_delete
from minio.error import S3Error
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request

from src.exceptions import ToolsError
from src.tools.decorator.error_response import error_response
from src.tools.log_collector import log
from src.tools.view import *


class ModelCRUD(GenericAPIView):
    model = None
    project_model = None
    serializer = None
    not_matching_str = [
        'pageSize', 'page',
        'type', 'status',
        'module', 'project_product', 'case_people', 'test_object', 'project', 'user',
    ]
    pytest_model = ['PytestAct', 'PytestCase', 'PytestTools', 'PytestTestFile']

    @error_response('system')
    def get(self, request: Request):
        from src.auto_test.auto_system.models import ProjectProduct
        from src.auto_test.auto_pytest.models import PytestProduct
        return get(self,
                   request=request,
                   project_product=ProjectProduct,
                   pytest_product=PytestProduct,
                   log=log,
                   field_does_note_xist=FieldDoesNotExist,
                   s3_error=S3Error,
                   response_data=ResponseData,
                   field_error=FieldError,
                   m_0001=RESPONSE_MSG_0001,
                   m_0026=RESPONSE_MSG_0026,
                   m_0027=RESPONSE_MSG_0027,
                   )

    @error_response('system')
    def post(self, request: Request):
        return post(self,
                    request=request,
                    response_data=ResponseData,
                    log=log,
                    m_0002=RESPONSE_MSG_0002,
                    m_0003=RESPONSE_MSG_0003
                    )

    @error_response('system')
    def put(self, request: Request):
        return put(self,
                   request=request,
                   response_data=ResponseData,
                   log=log,
                   m_0082=RESPONSE_MSG_0082,
                   m_0004=RESPONSE_MSG_0004
                   )

    @error_response('system')
    def delete(self, request: Request):
        return delete(self,
                      request=request,
                      log=log,
                      response_data=ResponseData,
                      m_0029=RESPONSE_MSG_0029,
                      m_0005=RESPONSE_MSG_0005,
                      tools_error=ToolsError,
                      )

    @classmethod
    def inside_post(cls, data: dict) -> dict:
        return inside_post(cls,
                           data=data,
                           log=log,
                           tools_error=ToolsError,
                           m_0116=RESPONSE_MSG_0116
                           )

    @classmethod
    def inside_put(cls, _id: int, data: dict) -> dict:
        return inside_put(cls,
                          _id=_id,
                          data=data,
                          log=log,
                          tools_error=ToolsError,
                          m_0116=RESPONSE_MSG_0116
                          )

    @classmethod
    def inside_delete(cls, _id: int) -> None:
        return inside_delete(cls, _id=_id)

    def asynchronous_callback(self, parent_id: int = None):
        if hasattr(self, 'callback'):
            th = Thread(target=self.callback, args=(parent_id,))
            th.start()

    @classmethod
    def paging_list(cls, size: int, current: int, books: QuerySet, serializer) -> tuple[list, int]:
        count = books.count()
        if count <= int(size):
            current = 1
        try:
            return serializer(
                instance=Paginator(serializer.setup_eager_loading(books), size).page(current),
                many=True).data, count
        except FieldError:
            return serializer(
                instance=Paginator(books, size).page(current),
                many=True).data, count
