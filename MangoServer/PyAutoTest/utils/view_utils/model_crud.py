# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 封装了分页查询，单条查询和增删改查
# @Time   : 2023-02-08 8:30
# @Author : 毛鹏
import logging
from threading import Thread

from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_user.models import Project
from PyAutoTest.utils.view_utils.view_tools import paging_list

logger = logging.getLogger('system')


class ModelCRUD(GenericAPIView):
    model = None
    # post专用
    serializer = None

    def get(self, request):
        data_type = request.query_params.get('type')
        if data_type:
            books = self.model.objects.filter(type=int(data_type)).order_by('id')
        else:
            books = self.get_queryset()
        return Response({
            "code": 200,
            "msg": "获取数据成功~",
            "data": paging_list(
                request.query_params.get("pageSize"),
                request.query_params.get("page"),
                books,
                self.get_serializer_class()
            ),
            'totalSize': len(books)
        })

    def post(self, request):
        serializer = self.serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            if hasattr(self, 'callback'):
                th = Thread(target=self.callback, args=(serializer.data.get('case'),))
                th.start()
            return Response({
                'code': 200,
                'msg': '新增一条记录成功~',
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
        serializer = self.serializer(
            instance=self.model.objects.get(pk=request.data.get('id')),
            data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            if hasattr(self, 'callback'):
                th = Thread(target=self.callback, args=(request.data.get('case'),))
                th.start()
            return Response({
                'code': 200,
                'msg': '修改一条记录成功~',
                'data': serializer.data
            })
        else:
            logger.error(f'执行修改时报错，请检查！数据：{request.data}, 报错信息：{str(serializer.errors)}')
            return Response({
                'code': 300,
                'msg': str(serializer.errors),
                'data': ''
            })

    def delete(self, request):
        if '[' in request.query_params.get('id'):
            for i in eval(request.query_params.get('id')):
                self.model.objects.get(pk=i).delete()
            return Response({
                'code': 200,
                'msg': '删除成功',
                'data': ''
            })
        else:
            self.model.objects.get(pk=request.query_params.get('id')).delete()
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


class ModelR(ViewSet):
    model = None
    serializer_class = None

    @action(methods=['get'], detail=False)
    def query_by(self, request):
        if request.query_params.get('type'):
            return self.type_query_by(request)
        elif not request.query_params.get('type'):
            return self.not_type_query_by(request)

    def type_query_by(self, request):
        name = request.query_params.get('name')
        id_ = request.query_params.get('id')
        team = request.query_params.get('team')
        books = None
        if team is not None and name is not None:
            books = self.model.objects.filter(
                team=Project.objects.get(name=team).id,
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
        elif team:
            books = self.model.objects.filter(
                team=Project.objects.get(name=team).id,
                type=request.query_params.get('type')
            ).order_by('id')
        if books is not None:
            return Response({
                "code": 200,
                "msg": "获取数据成功~",
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

    def not_type_query_by(self, request):
        name = request.query_params.get('name')
        id_ = request.query_params.get('id')
        team = request.query_params.get('team')
        books = None
        if team is not None and name is not None:
            books = self.model.objects.filter(
                team=Project.objects.get(name=team).id,
                name=name
            ).order_by('id')
        elif name is not None and id_ is not None:
            books = self.model.objects.filter(name=name,
                                              id=id_).order_by('id')
        elif id_:
            books = self.model.objects.filter(id=id_).order_by('id')
        elif name:
            books = self.model.objects.filter(name=name).order_by('id')
        elif team:
            books = self.model.objects.filter(
                team=Project.objects.get(name=team).id
            ).order_by('id')
        if books is not None:
            return Response({
                "code": 200,
                "msg": "获取数据成功~",
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

    #
    # @action(methods=['get'], detail=False)
    # def query_by_id(self, request):
    #     books = self.model.objects.get(name=request.query_params.get('id'))
    #     return Response({
    #         "code": 200,
    #         "msg": "获取数据成功~",
    #         "data": paging_list(
    #             request.query_params.get("pageSize"),
    #             request.query_params.get("page"),
    #             books,
    #             self.serializer_class
    #         ),
    #         'totalSize': len(books)
    #     })
    #
    # @action(methods=['get'], detail=False)
    # def query_by_item(self, request):
    #     books = self.model.objects.filter(name=request.query_params.get('team'))
    #     return Response({
    #         "code": 200,
    #         "msg": "获取数据成功~",
    #         "data": paging_list(
    #             request.query_params.get("pageSize"),
    #             request.query_params.get("page"),
    #             books,
    #             self.serializer_class
    #         ),
    #         'totalSize': len(books)
    #     })
