# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 封装了分页查询，单条查询和增删改查
# @Time   : 2023-02-08 8:30
# @Author : 毛鹏
import logging
from threading import Thread

from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_user.models import Project
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.view_tools import paging_list

logger = logging.getLogger('system')


class ModelCRUD(GenericAPIView):
    model = None
    # post专用
    serializer = None

    def get(self, request: Request):
        query_dict = dict(request.query_params.lists())
        page_size = request.query_params.get("pageSize")
        page = request.query_params.get("page")
        query_dict = {k: v[0] for k, v in query_dict.items()}
        project_id = request.headers.get('Project')
        if project_id and hasattr(self.model, 'project'):
            query_dict['project'] = project_id
        if page_size and page:
            del query_dict['pageSize']
            del query_dict['page']
            books = self.model.objects.filter(**query_dict)
            return ResponseData.success('获取数据成功', paging_list(
                request.query_params.get("pageSize"),
                request.query_params.get("page"),
                books,
                self.get_serializer_class()
            ), len(books))
        books = self.model.objects.filter(**query_dict)
        return ResponseData.success('获取数据成功',
                                    self.get_serializer_class()(instance=books, many=True).data,
                                    len(books))

    def post(self, request):
        serializer = self.serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            if hasattr(self, 'callback'):
                th = Thread(target=self.callback, args=(serializer.data.get('page_step'),))
                th.start()
            return Response({
                'code': 200,
                'msg': '新增一条记录成功',
                'data': serializer.data
            })
        else:
            logger.error(f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{str(serializer.errors)}')
            return Response({
                'code': 300,
                'msg': str(serializer.errors),
                'data': ''
            })

    def put(self, request):
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
            if hasattr(self, 'callback'):
                th = Thread(target=self.callback, args=(request.data.get('page_step'),))
                th.start()
            return Response({
                'code': 200,
                'msg': '修改一条记录成功',
                'data': serializer.data
            })
        else:
            if isinstance(request, dict):
                logger.error(f'执行修改时报错，请检查！数据：{request}, 报错信息：{str(serializer.errors)}')
            else:
                logger.error(f'执行修改时报错，请检查！数据：{request.data}, 报错信息：{str(serializer.errors)}')
            return Response({
                'code': 300,
                'msg': str(serializer.errors),
                'data': ''
            })

    def delete(self, request):
        # 批量删
        if '[' in request.query_params.get('id'):
            for i in eval(request.query_params.get('id')):
                self.model.objects.get(pk=i).delete()
            return Response({
                'code': 200,
                'msg': '删除成功',
                'data': ''
            })
        else:
            # 一条删
            self.model.objects.get(id=request.query_params.get('id')).delete()
            # if hasattr(self, 'callback'):
            #     name = self.model.objects.get(id=request.query_params.get('id')).page_step.name
            #     th = Thread(target=self.callback, args=(name,))
            #     th.start()
            return Response({
                'code': 200,
                'msg': '删除成功',
                'data': ''
            })
        # return Response({
        #     'code': 300,
        #     'msg': '删除失败，未查询到id~',
        #     'data': ''
        # })

    def asynchronous_callback(self, request):
        """
        完成
        """
        if hasattr(self, 'callback'):
            th = Thread(target=self.callback, args=(request.data.get('case'),))
            th.start()


class ModelQuery(ViewSet):
    model = None
    serializer_class = None

    @action(methods=['get'], detail=False)
    def query_by(self, request: Request):
        query_dict = dict(request.query_params.lists())
        del query_dict['pageSize']
        del query_dict['page']
        query_dict = {k: v[0] for k, v in query_dict.items()}
        books = self.model.objects.filter(**query_dict)
        return Response({
            "code": 200,
            "msg": "获取数据成功",
            "data": paging_list(
                request.query_params.get("pageSize"),
                request.query_params.get("page"),
                books,
                self.serializer_class
            ),
            'totalSize': len(books)
        })
        # if request.query_params.get('type'):
        #     # 有type页签的查询
        #     return self.type_query_by(request)
        # else:
        #     # 无type页签的查询
        #     return self.not_type_query_by(request)

    def type_query_by(self, request: Request):
        name = request.query_params.get('name')
        id_ = request.query_params.get('id')
        project = request.query_params.get('project')
        books = None
        if project is not None and name is not None:
            books = self.model.objects.filter(
                project=Project.objects.get(id=project).id,
                name=name,
                type=request.query_params.get('type')
            ).order_by('id')
        elif name is not None and id_ is not None:
            books = self.model.objects.filter(name=name,
                                              id=id_,
                                              type=request.query_params.get('type')).order_by('id')
        elif id_:
            books = self.model.objects.filter(id=id_,
                                              type=request.query_params.get('type')).order_by('id')
        elif name:
            books = self.model.objects.filter(name=name,
                                              type=request.query_params.get('type')).order_by('id')
        elif project:
            books = self.model.objects.filter(
                project=Project.objects.get(id=project).id,
                type=request.query_params.get('type')
            ).order_by('id')
        if books is not None:
            return Response({
                "code": 200,
                "msg": "获取数据成功",
                "data": paging_list(
                    request.query_params.get("pageSize"),
                    request.query_params.get("page"),
                    books,
                    self.serializer_class
                ),
                'totalSize': len(books)
            })
        return Response({
            "code": 300,
            "msg": "搜索结果为空",
            "data": [],
            'totalSize': None
        })

    def not_type_query_by(self, request: Request):
        pass
