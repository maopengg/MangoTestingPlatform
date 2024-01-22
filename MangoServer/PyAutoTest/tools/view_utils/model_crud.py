# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 封装了分页查询，单条查询和增删改查
# @Time   : 2023-02-08 8:30
# @Author : 毛鹏
import logging
from threading import Thread

from django.core.paginator import Paginator
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request

from PyAutoTest.tools.view_utils.response_data import ResponseData

logger = logging.getLogger('system')


class ModelCRUD(GenericAPIView):
    model = None
    # post专用
    serializer = None

    def get(self, request: Request):
        not_matching_str = ['pageSize', 'page', 'type', 'project', 'module_name']
        query_dict = {}
        for k, v in dict(request.query_params.lists()).items():
            if k and isinstance(v[0], str) and k not in not_matching_str and 'id' not in k:
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
            return ResponseData.success('获取数据成功',
                                        self.paging_list(request.query_params.get("pageSize"),
                                                         request.query_params.get("page"),
                                                         books,
                                                         self.get_serializer_class()),
                                        len(books))
        else:
            books = self.model.objects.filter(**query_dict)
            return ResponseData.success('获取数据成功',
                                        self.get_serializer_class()(instance=books, many=True).data,
                                        len(books))

    def post(self, request: Request):
        serializer = self.serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            self.asynchronous_callback(request)
            return ResponseData.success('新增一条记录成功', serializer.data)
        else:
            logger.error(f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{str(serializer.errors)}')
            return ResponseData.fail(str(serializer.errors))

    def put(self, request: Request):
        if isinstance(request, dict):
            serializer = self.serializer(
                instance=self.model.objects.get(pk=request.get('id')),
                data=request
            )
        else:
            serializer = self.serializer(
                instance=self.model.objects.get(pk=request.data.get('id')),
                data=request.data
            )
        if serializer.is_valid():
            serializer.save()
            self.asynchronous_callback(request)
            return ResponseData.success('修改一条记录成功', serializer.data)
        else:
            if isinstance(request, dict):
                logger.error(f'执行修改时报错，请检查！数据：{request}, 报错信息：{str(serializer.errors)}')
            else:
                logger.error(f'执行修改时报错，请检查！数据：{request.data}, 报错信息：{str(serializer.errors)}')
            return ResponseData.fail(str(serializer.errors))

    def delete(self, request: Request):
        # 批量删
        if '[' in request.query_params.get('id'):
            for i in eval(request.query_params.get('id')):
                self.model.objects.get(pk=i).delete()
        else:
            # 一条删
            model = self.model.objects.get(id=request.query_params.get('id'))
            # case_id = model.case.id
            model.delete()
            self.asynchronous_callback(request, model.id)
        return ResponseData.success('删除成功')

    def asynchronous_callback(self, request: Request, case_id: int = None):
        """
        反射的后置处理
        """
        if hasattr(self, 'callback'):
            from PyAutoTest.auto_test.auto_ui.views.ui_case_steps_detailed import UiCaseStepsDetailedCRUD
            from PyAutoTest.auto_test.auto_ui.views.ui_page_steps_detailed import UiPageStepsDetailedCRUD
            from PyAutoTest.auto_test.auto_api.views.api_case_detailed import ApiCaseDetailedCRUD
            if isinstance(self, UiPageStepsDetailedCRUD):
                _id = request.data.get('page_step')
                if _id is None:
                    _id = request.query_params.get('page_step')
            elif isinstance(self, UiCaseStepsDetailedCRUD):
                _id = request.data.get('case')
                if _id is None:
                    _id = request.query_params.get('case')
            elif isinstance(self, ApiCaseDetailedCRUD):
                if request.method == "DELETE":
                    _id = case_id
                else:
                    _id = request.data.get('case')
                    if _id is None:
                        _id = request.query_params.get('case')
            else:
                return
            if _id is not None:
                th = Thread(target=self.callback, args=(_id,))
                th.start()

    @classmethod
    def paging_list(cls, size: int, current: int, books, serializer) -> list:
        """
        分页
        @param size:
        @param current:现在页数
        @param books:
        @param serializer:
        @return:
        """
        if int(books.count()) <= int(size):
            current = 1
        return serializer(instance=Paginator(books, size).page(current), many=True).data

    def inside_post(self, data: dict) -> dict:
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return serializer.data
        else:
            logger.error(f'执行保存时报错，请检查！数据：{data}, 报错信息：{str(serializer.errors)}')

    def inside_put(self, _id: int, data: dict) -> dict:
        serializer = self.serializer(instance=self.model.objects.get(pk=_id), data=data)
        if serializer.is_valid():
            serializer.save()
            return serializer.data
        else:
            logger.error(f'执行修改时报错，请检查！id:{_id}, 数据：{data}, 报错信息：{str(serializer.errors)}')

    def inside_delete(self, _id: int) -> None:
        """
        删除一条记录
        @param _id:
        @return:
        """
        self.model.objects.get(id=_id).delete()
