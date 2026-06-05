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
from django.db import models
from django.db.models.query import QuerySet
from minio.error import S3Error
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from src.apps.auto_system.models import ProjectProduct
from src.apps.auto_pytest.models import PytestProduct
from src.common.exceptions import ToolsError
from src.common.tools.decorator.error_response import error_response
from src.common.tools.log_collector import log
from src.common.tools.view import *

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

    def has_invalid_integer_filter(self, query_dict: dict) -> bool:
        for key, value in query_dict.items():
            if not isinstance(value, str):
                continue
            field_name = key.split('__', 1)[0]
            try:
                field = self.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue
            target_field = field.target_field if isinstance(field, models.ForeignKey) else field
            if not isinstance(target_field, models.IntegerField):
                continue
            try:
                int(value)
            except ValueError:
                return True
        return False

    @error_response('system')
    def get(self, request: Request):
        def query() -> dict:
            query_dict = {}
            for k, v in dict(request.query_params.lists()).items():
                if k and isinstance(v[0], str) and k not in self.not_matching_str and 'id' not in k:
                    query_dict[f'{k}__contains'] = v[0]
                else:
                    query_dict[k] = v[0]
            project_id = request.headers.get('Project', None)
            if query_dict.get('project_product') is None and project_id and hasattr(self.model, 'project_product'):
                project_product = ProjectProduct.objects.filter(project_id=project_id)
                if self.model.__name__ in self.pytest_model:
                    product = PytestProduct.objects.filter(
                        project_product_id__in=project_product.values_list('id', flat=True)
                    )
                    query_dict['project_product_id__in'] = product.values_list('id', flat=True)
                else:
                    query_dict['project_product_id__in'] = project_product.values_list('id', flat=True)
            return query_dict

        query_dict = query()
        paging = request.query_params.get("pageSize") and request.query_params.get("page")
        if paging:
            del query_dict['pageSize'], query_dict['page']
        try:
            if self.has_invalid_integer_filter(query_dict):
                books = self.model.objects.none()
            else:
                try:
                    self.model._meta.get_field('case_sort')
                    books = self.model.objects.filter(**query_dict).order_by('case_sort')
                except FieldDoesNotExist:
                    books = self.model.objects.filter(**query_dict)
            if paging:
                data_list, count = self.paging_list(
                    request.query_params.get("pageSize"),
                    request.query_params.get("page"),
                    books,
                    self.get_serializer_class()
                )
                return ResponseData.success(RESPONSE_MSG_0001, data_list, count)
            serializer = self.get_serializer_class()
            try:
                books = serializer.setup_eager_loading(books)
            except FieldError:
                pass
            return ResponseData.success(
                RESPONSE_MSG_0001,
                serializer(instance=books, many=True).data,
                books.count()
            )
        except S3Error as error:
            log.system.error(f'GET请求发送异常，请排查问题：{error}, error:{traceback.print_exc()}')
            return ResponseData.fail(RESPONSE_MSG_0026)

    @error_response('system')
    def post(self, request: Request):
        serializer = self.serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            self.asynchronous_callback(request.data.get('parent_id'))
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        log.system.error(
            f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{json.dumps(serializer.errors)}')
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response('system')
    def put(self, request: Request):
        if isinstance(request, dict):
            data = request
            instance_id = request.get('id')
        else:
            data = request.data
            instance_id = request.data.get('id')
        try:
            instance = self.model.objects.get(pk=instance_id)
        except self.model.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0158)
        serializer = self.serializer(
            instance=instance,
            data=data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            parent_id = data.get('parent_id')
            self.asynchronous_callback(parent_id)
            return ResponseData.success(RESPONSE_MSG_0082, serializer.data)
        log.system.error(f'执行修改时报错，请检查！数据：{data}, 报错信息：{str(serializer.errors)}')
        return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)

    @error_response('system')
    def delete(self, request: Request):
        _id = request.query_params.get('id')
        id_list = [int(id_str) for id_str in request.query_params.getlist('id[]')]
        try:
            if not _id and id_list:
                for i in id_list:
                    self.model.objects.get(pk=i).delete()
            else:
                self.model.objects.get(id=_id).delete()
                self.asynchronous_callback(request.query_params.get('parent_id'))
        except ToolsError as error:
            return ResponseData.fail((error.code, error.msg))
        except self.model.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0029)
        else:
            return ResponseData.success(RESPONSE_MSG_0005)

    @classmethod
    def inside_post(cls, data: dict) -> dict:
        serializer = cls.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return dict(serializer.data)
        log.system.error(f'执行内部保存时报错，请检查！数据：{data}, 报错信息：{json.dumps(serializer.errors)}')
        raise ToolsError(*RESPONSE_MSG_0116, value=(serializer.errors,))

    @classmethod
    def inside_put(cls, _id: int, data: dict) -> dict:
        serializer = cls.serializer(instance=cls.model.objects.get(pk=_id), data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return dict(serializer.data)
        log.system.error(f'执行内部修改时报错，请检查！id:{_id}, 数据：{data}, 报错信息：{str(serializer.errors)}')
        raise ToolsError(*RESPONSE_MSG_0117, value=(serializer.errors,))

    @classmethod
    def inside_delete(cls, _id: int) -> None:
        cls.model.objects.get(id=_id).delete()

    def asynchronous_callback(self, parent_id: int = None):
        if hasattr(self, 'callback'):
            th = Thread(target=self.callback, args=(parent_id,))
            th.start()

    @classmethod
    def paging_list(
            cls,
            size: int,
            current: int,
            books: QuerySet,
            serializer
    ) -> tuple[list, int]:

        size = int(size)
        current = int(current)

        try:
            queryset = serializer.setup_eager_loading(books)
        except (AttributeError, FieldError):
            queryset = books

        paginator = Paginator(queryset, size)

        # 防止页码越界
        if current > paginator.num_pages and paginator.num_pages > 0:
            current = paginator.num_pages

        page_obj = paginator.page(current)

        data = serializer(
            instance=page_obj.object_list,
            many=True
        ).data

        return data, paginator.count
