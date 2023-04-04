from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.utils.cache_utils.redis import Cache
from PyAutoTest.utils.other_utils.random_data import RandomData
from PyAutoTest.utils.view_utils.view_tools import enum_list
from ..system_tools.enum import Environment
from ...auto_ui.case_run.case_data import CaseData


class SystemViews(ViewSet):

    @action(methods=['get'], detail=False)
    def test_func(self, request):
        r = CaseData(2)
        data = r.data_ui_case(1)
        return Response(data)

    @action(methods=['get'], detail=False)
    def get_test_environment(self, request, *args, **kwargs):
        return Response({
            'code': 200,
            'msg': '获取环境信息成功',
            'data': enum_list(Environment)
        })

    @action(methods=['get'], detail=False)
    def common_variable(self, request):
        """
        返回公共变量页
        @param request:
        @return:
        """
        return Response({
            'code': 200,
            'msg': '获取数据成功~',
            "data": RandomData().get_methods()
        })

    @action(methods=['get'], detail=False)
    def random_data(self, request):
        name = request.GET.get("name")
        if '()' in name:
            try:
                return Response({
                    'code': 200,
                    'msg': '获取数据成功~',
                    "data": str(RandomData().regular(name))
                })
            except:
                return Response({
                    'code': 300,
                    'msg': '函数数据格式错误~',
                    "data": ''
                })
        elif '${' in name and '}' in name:
            res1 = name.replace("${", "")
            name = res1.replace("}", "")
            if Cache().read_data_from_cache(name):
                return Response({
                    'code': 200,
                    'msg': '获取数据成功~',
                    "data": Cache().read_data_from_cache(name)
                })
            else:
                return Response({
                    'code': 300,
                    'msg': 'Redis缓存中不存在~',
                    "data": ''
                })
        else:
            return Response({
                'code': 300,
                'msg': '数据格式错误~',
                "data": ''
            })
