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

    @action(methods=['get'], detail=False)
    def shuyun_tag_mark_query(self, request):
        tag_type = request.query_params.get('tagType')
        plat_account = request.query_params.get('platAccount')
        plat_code = request.query_params.get('platCode')
        shop_id = request.query_params.get('shopId')
        if tag_type and plat_code and plat_account and shop_id:
            return Response({
                "code": 10000,
                "success": True,
                "data": [
                    {
                        "tagId": 2,  # 标签ID
                        "tagName": "已发放VIP4升级礼",  # 标签名称
                        "tagType": 1,  # 标签类型（0：云标签, 1：自定义标签）
                        "valueType": 4,  # 标签值类型(0：日期型, 1：字符输入型, 2:字符选择型, 3:数值输入型, 4:数值选择型)
                        "optionType": 1,
                        # 如果标签值类型为3:数值输入型或4:数值选择型, 代表（"0":"整数","1":"小数"）, 如果标签值类型为0：日期型,代表(0:年/月/日, 1:年/月)
                        "valueNumberOption": 0,  # 可打标签值个数(0:单选，1：多选, null:没有单选多选)，只有在标签值类型为2：字符选择型或者4:数值选择型时才会返回该字段
                        "validPeriod": 20,  # 标签值有效期,如果有有效期，为固定的一个整数。跟validPeriodType字段组合使用，表示多少天，多少月，多少年。-1:永久有效
                        "validPeriodType": 0,  # 标签值有效期类型(0:天, 1:月, 2:年)
                        "tagValue": [  # 打标值数组
                            "打乒乓球"
                        ]
                    }
                ]
            })
        else:
            return Response({
                "code": 10001,
                "success": False,
                "data": ""
            })
