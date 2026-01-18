# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 封装了分页查询，单条查询和增删改查
# @Time   : 2023-02-08 8:30
# @Author : 毛鹏
import json
import traceback
from threading import Thread

from django.core.exceptions import FieldError, FieldDoesNotExist
from django.core.paginator import Paginator
from django.db.models.query import QuerySet
from minio.error import S3Error
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request

from src.exceptions import ToolsError
from src.tools.decorator.error_response import error_response
from src.tools.log_collector import log
from src.tools.view import *
from ...auto_test.auto_pytest.models import PytestProduct
from ...auto_test.auto_system.models import ProjectProduct


def get(self, **kwargs):
    request = kwargs.get('request')

    def query(request):
        query_dict = {}
        for k, v in dict(request.query_params.lists()).items():
            if k and isinstance(v[0], str) and k not in self.not_matching_str and 'id' not in k:
                query_dict[f'{k}__contains'] = v[0]
            else:
                query_dict[k] = v[0]
        project_id = request.headers.get('Project', None)
        if query_dict.get('project_product') is None and project_id and hasattr(self.model, 'project_product'):
            project_product = kwargs.get('project_product').objects.filter(project_id=project_id)
            if self.model.__name__ in self.pytest_model:
                product = kwargs.get('pytest_product').objects.filter(
                    project_product_id__in=project_product.values_list('id', flat=True))
                query_dict['project_product_id__in'] = product.values_list('id', flat=True)
            else:
                query_dict['project_product_id__in'] = project_product.values_list('id', flat=True)
        return query_dict

    query_dict = query(request)
    paging = request.query_params.get("pageSize") and request.query_params.get("page")
    if paging:
        del query_dict['pageSize'], query_dict['page']
    try:
        try:
            self.model._meta.get_field('case_sort')
            books = self.model.objects.filter(**query_dict).order_by('case_sort')
        except kwargs.get('field_does_note_xist'):
            books = self.model.objects.filter(**query_dict)
        if paging:
            data_list, count = self.paging_list(
                request.query_params.get("pageSize"),
                request.query_params.get("page"),
                books,
                self.get_serializer_class()
            )
            return kwargs.get('response_data').success(kwargs.get('m_0001'), data_list, count)
        else:
            serializer = self.get_serializer_class()
            try:
                books = serializer.setup_eager_loading(books)
            except kwargs.get('field_error'):
                pass
            return kwargs.get('response_data') \
                .success(
                kwargs.get('m_0001'),
                serializer(instance=books, many=True).data,
                books.count()
            )
    except kwargs.get('s3_error') as error:
        kwargs.get('log').system.error(f'GET请求发送异常，请排查问题：{error}, error:{traceback.print_exc()}')
        return kwargs.get('response_data').fail(kwargs.get('m_0026'), )


def post(self, **kwargs):
    serializer = self.serializer(data=kwargs.get('request').data)
    if serializer.is_valid():
        serializer.save()
        self.asynchronous_callback(kwargs.get('request').data.get('parent_id'))
        return kwargs.get('response_data').success(kwargs.get('m_0002'), serializer.data)
    else:
        kwargs.get('log').system.error(
            f'执行保存时报错，请检查！数据：{kwargs.get("request").data}, 报错信息：{json.dumps(serializer.errors)}')
        return kwargs.get('response_data').fail(kwargs.get('m_0003'), serializer.errors)


def put(self, **kwargs):
    if isinstance(kwargs.get("request"), dict):
        data = kwargs.get("request")
        serializer = self.serializer(
            instance=self.model.objects.get(pk=kwargs.get("request").get('id')),
            data=data,
            partial=True
        )
    else:
        data = kwargs.get("request").data
        serializer = self.serializer(
            instance=self.model.objects.get(pk=kwargs.get("request").data.get('id')),
            data=data,
            partial=True
        )
    if serializer.is_valid():
        serializer.save()
        self.asynchronous_callback(kwargs.get("request").data.get('parent_id'))
        return kwargs.get('response_data').success(kwargs.get('m_0082'), serializer.data)
    else:
        kwargs.get('log').system.error(f'执行修改时报错，请检查！数据：{data}, 报错信息：{str(serializer.errors)}')
        return kwargs.get('response_data').fail(kwargs.get('m_0004'), serializer.errors)


def delete(self, **kwargs):
    _id = kwargs.get('request').query_params.get('id')
    id_list = [int(id_str) for id_str in kwargs.get('request').query_params.getlist('id[]')]
    try:
        if not _id and id_list:
            for i in id_list:
                self.model.objects.get(pk=i).delete()
        else:
            self.model.objects.get(id=_id).delete()
            self.asynchronous_callback(kwargs.get('request').query_params.get('parent_id'))
    except kwargs.get('tools_error') as error:
        return kwargs.get('response_data').fail((error.code, error.msg))
    except self.model.DoesNotExist:
        return kwargs.get('response_data').fail(kwargs.get('m_0029'))
    else:
        return kwargs.get('response_data').success(kwargs.get('m_0005'))


def inside_post(cls, **kwargs):
    serializer = cls.serializer(data=kwargs.get('data'))
    if serializer.is_valid():
        serializer.save()
        return dict(serializer.data)
    else:
        kwargs.get('log').system.error(
            f'执行内部保存时报错，请检查！数据：{kwargs.get("data")}, 报错信息：{json.dumps(serializer.errors)}')
        raise kwargs.get('tools_error')(*kwargs.get('m_0116'), value=(serializer.errors,))


def inside_put(cls, **kwargs):
    serializer = cls.serializer(instance=cls.model.objects.get(pk=kwargs.get('_id')), data=kwargs.get("data"),
                                partial=True)
    if serializer.is_valid():
        serializer.save()
        return dict(serializer.data)
    else:
        kwargs.get('log').system.error(
            f'执行内部修改时报错，请检查！id:{kwargs.get("_id")}, 数据：{kwargs.get("data")}, 报错信息：{str(serializer.errors)}')
        raise kwargs.get('tools_error')(*kwargs.get('m_0116'), value=(serializer.errors,))


def inside_delete(cls, **kwargs) -> None:
    cls.model.objects.get(id=kwargs.get('_id')).delete()


class ModelCRUD(GenericAPIView):
    model = None
    project_model = None
    serializer = None
    not_matching_str = [
        'pageSize', 'page',
        'type', 'status',
        'module', 'project_product', 'case_people', 'test_object', 'project', 'user'
    ]
    pytest_model = ['PytestAct', 'PytestCase', 'PytestTools', 'PytestTestFile']

    @error_response('system')
    def get(self, request: Request):
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
                          m_0116=RESPONSE_MSG_0117
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
