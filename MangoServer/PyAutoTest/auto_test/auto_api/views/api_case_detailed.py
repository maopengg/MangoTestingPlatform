# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
import json
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed, ApiInfo, ApiCase, ApiInfoResult
from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseSerializers
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoSerializers
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData

logger = logging.getLogger('api')


class ApiCaseDetailedSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCaseDetailed
        fields = '__all__'


class ApiCaseDetailedSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)
    case = ApiCaseSerializers(read_only=True)
    api_info = ApiInfoSerializers(read_only=True)

    class Meta:
        model = ApiCaseDetailed
        fields = '__all__'


class ApiCaseDetailedCRUD(ModelCRUD):
    model = ApiCaseDetailed
    queryset = ApiCaseDetailed.objects.all()
    serializer_class = ApiCaseDetailedSerializersC
    serializer = ApiCaseDetailedSerializers

    def get(self, request: Request):
        case_id = request.query_params.get('case_id')
        api_info_id = request.query_params.get('api_info_id')
        test_suite_id = request.query_params.get('test_suite_id')
        if api_info_id:
            api_case_detailed = ApiCaseDetailed.objects.filter(case=case_id, api_info=api_info_id).order_by(
                'case_sort')
        else:
            api_case_detailed = ApiCaseDetailed.objects.filter(case=case_id).order_by('case_sort')
        data = []
        for i in api_case_detailed:
            api_info_result = ApiInfoResult.objects.filter(case_detailed=i.id, test_suite_id=test_suite_id).first()
            if api_info_result:
                status = '通过' if api_info_result.status else '失败'
            else:
                status = None
            data.append({
                'id': i.id,
                'api_info_id': i.api_info.id,
                'case_sort': i.case_sort,
                'name': i.api_info.name,
                'method': i.api_info.method,
                'client': i.api_info.client,
                'status': api_info_result.status if api_info_result else None,
                'request': [{'key': 6, 'title': 'url', 'name': 'url', 'data': i.url, 'type': 'textarea'},
                            {'key': 1, 'title': '请求头', 'name': 'header', 'data': i.header, 'type': 'textarea'},
                            {'key': 2, 'title': '参数', 'name': 'params',
                             'data': json.dumps(i.params, ensure_ascii=False) if i.params else None,
                             'type': 'textarea'},
                            {'key': 3, 'title': '表单', 'name': 'data',
                             'data': json.dumps(i.data, ensure_ascii=False) if i.data else None, 'type': 'textarea'},
                            {'key': 4, 'title': 'json', 'name': 'json',
                             'data': json.dumps(i.json, ensure_ascii=False) if i.json else None, 'type': 'textarea'},
                            {'key': 5, 'title': '文件', 'name': 'file',
                             'data': json.dumps(i.file, ensure_ascii=False) if i.file else None, 'type': 'textarea'}],
                'front': [{'key': 10, 'title': '前置sql', 'name': 'front_sql', 'data': i.front_sql, 'type': 'list'}],
                'response': [{'key': 20, 'title': '基础信息',
                              'data': [{'label': 'url', 'value': api_info_result.url if api_info_result else None},
                                       {'label': 'code',
                                        'value': api_info_result.response_code if api_info_result else None},
                                       {'label': '响应时间',
                                        'value': api_info_result.response_time if api_info_result else None},
                                       {'label': '测试结果', 'value': status},
                                       {'label': '错误提示',
                                        'value': api_info_result.error_message if api_info_result else None},
                                       ],
                              'type': 'descriptions'},
                             {'key': 21, 'title': '响应头',
                              'data': api_info_result.response_headers if api_info_result else None,
                              'type': 'text'},
                             {'key': 22, 'title': '响应文本',
                              'data': api_info_result.response_text if api_info_result else None,
                              'type': 'text'}
                             ],
                'assertion': [
                    {
                        'key': 30,
                        'title': 'sql断言',
                        'name': 'ass_sql',
                        'data': i.ass_sql,
                        'type': 'assertion'
                    },
                    {'key': 31, 'title': '响应全匹配断言', 'name': 'ass_response_whole', 'data': i.ass_response_whole,
                     'type': 'textarea'},
                    {
                        'key': 32,
                        'title': '响应值断言',
                        'name': 'ass_response_value',
                        'data': i.ass_response_value,
                        'type': 'assertion'
                    }
                ],
                'posterior': [
                    {
                        'key': 40,
                        'title': '后置sql', 'name': 'posterior_sql',
                        'data': i.posterior_sql,
                        'type': 'posterior'
                    },
                    {
                        'key': 41,
                        'title': '后置响应结果提取', 'name': 'posterior_response',
                        'data': i.posterior_response,
                        'type': 'posterior'
                    },
                    {'key': 42, 'title': '后置等待', 'name': 'posterior_sleep', 'data': i.posterior_sleep,
                     'type': 'textarea'}
                ],
                'dump': [
                    {
                        'key': 50,
                        'title': 'sql清除', 'name': 'dump_data',
                        'data': i.dump_data,
                        'type': 'list'
                    }
                ],
                'cache': [
                    {
                        'key': 60,
                        'title': '缓存数据',
                        'data': api_info_result.all_cache if api_info_result else None,
                        'type': 'text'
                    }
                ]
            })
        return ResponseData.success('获取数据成功', data)

    def post(self, request: Request):
        data = request.data
        if data['module_name']:
            del data['module_name']
        api_info_obj = ApiInfo.objects.get(id=request.data.get('api_info'))
        data['url'] = api_info_obj.url
        data['params'] = api_info_obj.params
        data['data'] = api_info_obj.data
        data['json'] = api_info_obj.json
        data['file'] = api_info_obj.file
        data['header'] = json.dumps(api_info_obj.header) if api_info_obj.header else '${headers}'

        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            self.asynchronous_callback(request)
            return ResponseData.success('新增一条记录成功', serializer.data)
        else:
            logger.error(f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{str(serializer.errors)}')
            return ResponseData.fail(str(serializer.errors))

    def callback(self, _id):
        """
        排序
        @param _id: 用例ID
        @return:
        """
        data = {'id': _id, 'case_flow': '', 'name': ''}
        run = self.model.objects.filter(case=_id).order_by('case_sort')
        for i in run:
            data['case_flow'] += '->'
            if i.api_info:
                data['case_flow'] += i.api_info.name
        data['name'] = run[0].case.name
        from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseCRUD
        api_case = ApiCaseCRUD()
        res = api_case.serializer(instance=ApiCase.objects.get(pk=_id), data=data)
        if res.is_valid():
            res.save()
        else:
            logger.error(f'保存用例执行顺序报错！，报错结果：{str(res.errors)}')


class ApiCaseDetailedViews(ViewSet):
    model = ApiCaseDetailed
    serializer_class = ApiCaseDetailedSerializers

    @action(methods=['put'], detail=False)
    def put_case_sort(self, request: Request):
        """
        修改排序
        @param request:
        @return:
        """
        case_id = None
        for i in request.data.get('case_sort_list'):
            obj = self.model.objects.get(id=i['id'])
            obj.case_sort = i['case_sort']
            case_id = obj.case.id
            obj.save()
        ApiCaseDetailedCRUD().callback(case_id)
        return ResponseData.success('设置排序成功', )

    @action(methods=['put'], detail=False)
    def put_refresh_api_info(self, request: Request):
        api_info_detailed_obj = self.model.objects.get(id=request.data.get('id'))
        api_info_obj = ApiInfo.objects.get(id=api_info_detailed_obj.api_info.id)
        data = {
            'url': api_info_obj.url,
            'params': api_info_obj.params,
            'data': api_info_obj.data,
            'json': api_info_obj.json,
            'file': api_info_obj.file,
            'header': json.dumps(api_info_obj.header) if api_info_obj.header else '${headers}'
        }
        serializer = self.serializer_class(
            instance=api_info_detailed_obj,
            data=data
        )
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success('刷新接口成功', serializer.data)
        else:
            logger.error(f'执行刷新时报错，请检查！数据：{data}, 报错信息：{str(serializer.errors)}')
            return ResponseData.fail(str(serializer.errors))
