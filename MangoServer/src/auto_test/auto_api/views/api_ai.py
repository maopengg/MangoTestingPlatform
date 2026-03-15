# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: AI 写用例相关视图
import json
from urllib.parse import urlparse, parse_qs

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.tools.decorator.error_response import error_response
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class ApiAiViews(ViewSet):

    @action(methods=['POST'], detail=False)
    @error_response('api')
    def post_ai_import(self, request: Request):
        """
        步骤1：解析文本 -> 写入 ApiInfo -> 返回解析结果
        支持 cURL / 接口文档 / Postman / 自然语言等任意格式
        不解析 headers，由系统全局请求头统一管理
        """
        text = request.data.get('text', '').strip()
        # 清理可能导致 JSON 解析失败的控制字符（保留换行和制表符）
        import re as _re
        text = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        name = request.data.get('name', '').strip() or None
        project_product_id = request.data.get('project_product_id')
        module_id = request.data.get('module_id')
        api_type = request.data.get('api_type', 1)

        if not text:
            return ResponseData.fail((400, '请粘贴接口信息'))
        if not project_product_id or not module_id:
            return ResponseData.fail((400, '请选择产品和模块'))

        from src.auto_test.auto_api.views.api_info import ApiInfoCRUD
        from src.enums.api_enum import MethodEnum

        if text.lower().startswith('curl'):
            from curlparser import parse
            parsed = parse(text)

            url_components = urlparse(parsed.url)
            path = url_components.path
            api_name = name or path.split('/')[-1] or 'cURL导入接口'

            result = {
                'name': api_name,
                'module': module_id,
                'project_product': project_product_id,
                'type': api_type,
                'url': path,
                'method': MethodEnum.get_key(parsed.method),
            }
            query_params = parse_qs(url_components.query)
            params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
            if params:
                result['params'] = json.dumps(params, indent=4, ensure_ascii=False)
            if parsed.json and parsed.data:
                result['json'] = json.dumps(parsed.json, indent=4, ensure_ascii=False)
            elif parsed.json is None and parsed.data:
                result['data'] = json.dumps(parsed.data, indent=4, ensure_ascii=False)
            elif parsed.json and parsed.data is None:
                result['json'] = json.dumps(parsed.json, indent=4, ensure_ascii=False)
        else:
            from src.auto_test.auto_api.service.ai_service.ai_parser import parse_text_to_api
            parsed_ai = parse_text_to_api(text, name)
            method_str = (parsed_ai.get('method') or 'GET').upper()
            result = {
                'name': parsed_ai.get('name') or name or '未命名接口',
                'module': module_id,
                'project_product': project_product_id,
                'type': api_type,
                'url': parsed_ai.get('url') or '/',
                'method': MethodEnum.get_key(method_str),
            }
            if parsed_ai.get('params'):
                result['params'] = json.dumps(parsed_ai['params'], indent=4, ensure_ascii=False)
            if parsed_ai.get('json_body'):
                result['json'] = json.dumps(parsed_ai['json_body'], indent=4, ensure_ascii=False)
            if parsed_ai.get('data'):
                result['data'] = json.dumps(parsed_ai['data'], indent=4, ensure_ascii=False)

        api_res = ApiInfoCRUD.inside_post(result)

        return ResponseData.success(RESPONSE_MSG_0140, data={
            'api_info_id': api_res.get('id'),
            'name': api_res.get('name'),
            'url': api_res.get('url'),
            'method': api_res.get('method'),
            'params': api_res.get('params'),
            'json': api_res.get('json'),
            'data': api_res.get('data'),
        })

    @action(methods=['POST'], detail=False)
    @error_response('api')
    def post_ai_preview_case(self, request: Request):
        """
        步骤2：根据 ApiInfo ID，AI 推断多条用例配置，只返回预览数据列表，不写库
        """
        api_info_id = request.data.get('api_info_id')
        case_people_id = request.data.get('case_people_id')

        if not api_info_id:
            return ResponseData.fail((400, '请提供 api_info_id'))
        if not case_people_id:
            return ResponseData.fail((400, '请选择用例责任人'))

        from src.auto_test.auto_api.service.ai_service.ai_parser import generate_case_config
        cases = generate_case_config(api_info_id)

        return ResponseData.success(RESPONSE_MSG_0011, data={
            'api_info_id': api_info_id,
            'case_people_id': case_people_id,
            'cases': cases,
        })

    @action(methods=['POST'], detail=False)
    @error_response('api')
    def post_ai_confirm_case(self, request: Request):
        """
        步骤3：用户确认后，将多条用例基本信息写入数据库（只含基本信息和请求，不含断言/提取等）
        """
        from django.db import transaction
        from src.auto_test.auto_api.models import ApiInfo
        from src.auto_test.auto_api.views.api_case import ApiCaseCRUD
        from src.auto_test.auto_api.views.api_case_detailed import ApiCaseDetailedCRUD
        from src.enums.tools_enum import StatusEnum

        api_info_id = request.data.get('api_info_id')
        case_people_id = request.data.get('case_people_id')
        cases = request.data.get('cases', [])
        front_custom = request.data.get('front_custom', [])
        front_sql_list = request.data.get('front_sql', [])
        posterior_sql_list = request.data.get('posterior_sql', [])
        front_headers_list = request.data.get('front_headers', [])

        if not api_info_id or not case_people_id:
            return ResponseData.fail((400, 'api_info_id 和 case_people_id 为必填项'))
        if not cases:
            return ResponseData.fail((400, '请至少提供一条用例'))

        try:
            api = ApiInfo.objects.get(id=api_info_id)
        except ApiInfo.DoesNotExist:
            return ResponseData.fail((400, f'ApiInfo ID={api_info_id} 不存在'))

        created = []
        with transaction.atomic():
            for idx, item in enumerate(cases):
                case_name = (item.get('case_name') or f'{api.name}_自动用例_{idx + 1}')[:64]
                step_name = (item.get('step_name') or f'步骤1-{api.name}')[:124]

                case_data = {
                    'name': case_name,
                    'project_product': api.project_product_id,
                    'module': api.module_id,
                    'case_people': case_people_id,
                    'level': 1,
                    'status': StatusEnum.FAIL.value,
                    'parametrize': [],
                    'front_custom': front_custom,
                    'front_sql': front_sql_list,
                    'front_headers': front_headers_list,
                    'posterior_sql': posterior_sql_list,
                }
                case_res = ApiCaseCRUD.inside_post(case_data)
                case_id = case_res.get('id')

                detailed_data = {
                    'case': case_id,
                    'api_info': api_info_id,
                    'case_sort': 1,
                    'status': StatusEnum.FAIL.value,
                }
                detailed_res = ApiCaseDetailedCRUD.inside_post(detailed_data)
                detailed_id = detailed_res.get('id')

                # 创建 ApiCaseDetailedParameter，复制 ApiInfo 的请求数据
                from src.auto_test.auto_api.views.api_case_detailed_parameter import ApiCaseDetailedParameterCRUD
                param_data = {
                    'case_detailed': detailed_id,
                    'name': step_name,
                    'params': api.params,
                    'data': api.data,
                    'json': api.json,
                    'file': api.file,
                    'status': StatusEnum.FAIL.value,
                }
                ApiCaseDetailedParameterCRUD.inside_post(param_data)
                created.append({'case_id': case_id, 'detailed_id': detailed_id, 'case_name': case_name})

        return ResponseData.success(RESPONSE_MSG_0009, data={'created': created})
