# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 封装了分页查询，单条查询和增删改查
# @Time   : 2023-02-08 8:30
# @Author : 毛鹏
import logging
from threading import Thread

from django.core.exceptions import FieldError
from django.core.paginator import Paginator
from django.db.models.query import QuerySet
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request

from PyAutoTest.exceptions.tools_exception import InsideSaveError
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *

log = logging.getLogger('system')


class ModelCRUD(GenericAPIView):
    model = None
    # post专用
    serializer = None
    not_matching_str = ['pageSize', 'page', 'type', 'project', 'module', 'project_product', 'case_people']

    def get(self, request: Request):
        query_dict = {}
        for k, v in dict(request.query_params.lists()).items():
            if k and isinstance(v[0], str) and k not in self.not_matching_str and 'id' not in k:
                query_dict[f'{k}__contains'] = v[0]
            else:
                query_dict[k] = v[0]
        #
        project_id = request.headers.get('Project')
        if project_id and hasattr(self.model, 'project') and not query_dict.get('project'):
            query_dict['project'] = project_id

        if request.query_params.get("pageSize") and request.query_params.get("page"):
            del query_dict['pageSize']
            del query_dict['page']
            books = self.model.objects.filter(**query_dict)
            data_list, count = self.paging_list(request.query_params.get("pageSize"),
                                                request.query_params.get("page"),
                                                books,
                                                self.get_serializer_class())
            return ResponseData.success(RESPONSE_MSG_0001,
                                        data_list,
                                        count)
        else:
            books = self.model.objects.filter(**query_dict)
            serializer = self.get_serializer_class()
            try:
                books = serializer.setup_eager_loading(books)
            except FieldError:
                pass
            return ResponseData.success(RESPONSE_MSG_0001,
                                        serializer(instance=books, many=True).data,
                                        books.count())

    def post(self, request: Request):
        serializer = self.serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            self.asynchronous_callback(request)
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        else:
            log.error(f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{str(serializer.errors)}')
            return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    def put(self, request: Request):
        if isinstance(request, dict):
            data = request
            serializer = self.serializer(
                instance=self.model.objects.get(pk=request.get('id')),
                data=data
            )
        else:
            data = request.data
            serializer = self.serializer(
                instance=self.model.objects.get(pk=request.data.get('id')),
                data=data
            )
        if serializer.is_valid():
            serializer.save()
            self.asynchronous_callback(request, request.data.get('parent_id'))
            return ResponseData.success(RESPONSE_MSG_0082, serializer.data)
        else:
            log.error(f'执行修改时报错，请检查！数据：{data}, 报错信息：{str(serializer.errors)}')
            return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)

    def delete(self, request: Request):
        _id = request.query_params.get('id')
        id_list = [int(id_str) for id_str in request.query_params.getlist('id[]')]
        # 批量删
        if not _id and id_list:
            for i in id_list:
                self.model.objects.get(pk=i).delete()
        else:
            # 一条删
            model = self.model.objects.get(id=_id)
            model.delete()
            self.asynchronous_callback(request, request.query_params.get('parent_id'))
        return ResponseData.success(RESPONSE_MSG_0005)

    def asynchronous_callback(self, request: Request, _id: int = None):
        """
        反射的后置处理
        """
        if hasattr(self, 'callback'):
            from PyAutoTest.auto_test.auto_ui.views.ui_page_steps_detailed import UiPageStepsDetailedCRUD
            from PyAutoTest.auto_test.auto_ui.views.ui_case_steps_detailed import UiCaseStepsDetailedCRUD
            # from PyAutoTest.auto_test.auto_api.views.api_case_detailed import ApiCaseDetailedCRUD
            if isinstance(self, UiPageStepsDetailedCRUD):
                parent_id = request.data.get('page_step')
            elif isinstance(self, UiCaseStepsDetailedCRUD):
                parent_id = request.data.get('case')

            else:
                parent_id = request.data.get('id')
            if parent_id is None:
                parent_id = _id
            th = Thread(target=self.callback, args=(parent_id,))
            th.start()

    @classmethod
    def paging_list(cls, size: int, current: int, books: QuerySet, serializer) -> tuple[list, int]:
        """
        分页
        @param size:
        @param current:现在页数
        @param books:
        @param serializer:
        @return:
        """
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

    @classmethod
    def inside_post(cls, data: dict) -> dict:
        serializer = cls.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return serializer.data
        else:
            log.error(f'执行保存时报错，请检查！数据：{data}, 报错信息：{str(serializer.errors)}')
            raise InsideSaveError(*RESPONSE_MSG_0116, value=(serializer.errors,))

    @classmethod
    def inside_put(cls, _id: int, data: dict) -> dict:
        serializer = cls.serializer(instance=cls.model.objects.get(pk=_id), data=data)
        if serializer.is_valid():
            serializer.save()
            return serializer.data
        else:
            log.error(f'执行修改时报错，请检查！id:{_id}, 数据：{data}, 报错信息：{str(serializer.errors)}')
            raise InsideSaveError(*RESPONSE_MSG_0117, value=(serializer.errors,))

    @classmethod
    def inside_delete(cls, _id: int) -> None:
        """
        删除一条记录
        @param _id:
        @return:
        """
        cls.model.objects.get(id=_id).delete()
