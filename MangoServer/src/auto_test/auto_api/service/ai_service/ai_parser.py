# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: AI 解析服务 - 解析任意格式文本为接口数据，并推断测试用例配置
import json
from typing import Optional

from src.tools.log_collector import log


def _get_ai_config() -> dict:
    """从 CacheData 读取 AI 配置"""
    from src.auto_test.auto_system.models import CacheData
    config = {}
    keys = ['AI_API_KEY', 'AI_BASE_URL', 'AI_MODEL', 'AI_TIMEOUT']
    defaults = {
        'AI_API_KEY': None,
        'AI_BASE_URL': 'https://api.deepseek.com',
        'AI_MODEL': 'deepseek-chat',
        'AI_TIMEOUT': 60,
    }
    for key in keys:
        try:
            obj = CacheData.objects.get(key=key)
            config[key] = obj.value if obj.value else defaults[key]
        except CacheData.DoesNotExist:
            config[key] = defaults[key]
    log.api.debug(f'[AI配置] base_url={config.get("AI_BASE_URL")}, model={config.get("AI_MODEL")}, timeout={config.get("AI_TIMEOUT")}')
    return config


def _call_ai(messages: list, config: dict) -> dict:
    """调用大模型，返回解析后的 JSON dict"""
    from openai import OpenAI
    log.api.debug(f'[AI请求] model={config.get("AI_MODEL")}, messages数量={len(messages)}')
    client = OpenAI(
        api_key=config['AI_API_KEY'],
        base_url=config['AI_BASE_URL'],
        timeout=float(config['AI_TIMEOUT']),
    )
    response = client.chat.completions.create(
        model=config['AI_MODEL'],
        messages=messages,
        response_format={'type': 'json_object'},
    )
    content = response.choices[0].message.content
    log.api.debug(
        f'[AI响应] 原始内容长度={len(content)}, 内容={content[:500]}...'
        if len(content) > 500
        else f'[AI响应] 内容={content}'
    )
    import re as _re
    content = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    result = json.loads(content)
    log.api.debug(f'[AI响应] 解析后 keys={list(result.keys())}')
    return result


def parse_text_to_api(text: str, name: Optional[str] = None) -> dict:
    """
    将任意格式的文本解析为接口结构化数据。
    支持：cURL、接口文档文字、Postman JSON、HAR 片段、自然语言描述。
    注意：cURL 格式请在调用前用 curlparser 处理，此函数处理非 cURL 的其他格式。

    返回 dict 包含：
      name, url, method, params, json_body, data
    （不含 headers，由全局请求头统一管理）

    若文本中不包含任何请求信息，抛出 ValueError。
    """
    log.api.debug(f'[parse_text_to_api] 开始解析，文本长度={len(text)}, 自定义名称={name!r}')
    config = _get_ai_config()
    if not config.get('AI_API_KEY'):
        raise ValueError('AI_API_KEY 未配置，请在系统设置-配置管理中填写 AI 的 API Key')

    system_prompt = """你是一个专业的接口测试助手。
用户会给你各种格式的接口信息（接口文档文字、Postman JSON、HAR 片段、自然语言描述等）。
请解析并返回一个严格的 JSON 对象，包含以下字段：
- name: 接口名称（从文档或注释中提取，没有则根据URL语义命名，如果用户已提供则使用用户提供的）
- url: 接口路径（只保留path部分，去掉协议、域名和query string，以/开头）
- method: HTTP方法大写字符串，如 GET POST PUT DELETE PATCH
- params: query参数对象，没有则为null
- json_body: JSON body对象，没有则为null
- data: form-data对象，没有则为null
- has_request_info: 布尔值，文本中是否包含有效的接口请求信息（URL或HTTP方法），如果只是普通文字、无关内容则为false

注意：不需要返回 headers 字段，请求头由系统全局统一管理。
只返回 JSON，不要有任何额外说明文字。"""

    user_content = text
    if name:
        user_content = f'接口名称：{name}\n\n{text}'

    result = _call_ai([
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_content},
    ], config)

    has_request_info = result.get('has_request_info', True)  # 兼容旧模型不返回该字段
    url = (result.get('url') or '').strip()
    method = (result.get('method') or '').strip()
    log.api.debug(
        f'[parse_text_to_api] AI解析结果: has_request_info={has_request_info}, '
        f'url={url!r}, method={method!r}, name={result.get("name")!r}'
    )

    # 判断文本是否包含有效请求信息
    if has_request_info is False or (not url and not method):
        log.api.debug('[parse_text_to_api] 文本中未检测到有效的接口请求信息，拒绝解析')
        raise ValueError('上传的文本中未包含有效的接口请求信息（如 URL、HTTP 方法等），请粘贴接口文档、cURL 命令或相关请求描述')

    return result


def generate_case_config(api_info_id: int) -> list:
    """
    根据 ApiInfo 的完整信息，调用 AI 推断多条测试用例配置。
    一个接口会对应多个测试用例（正常流程、异常流程等）。
    返回预览数据列表（不写库），每项包含：
      case_name, step_name
    """
    from src.auto_test.auto_api.models import ApiInfo
    from src.enums.api_enum import MethodEnum

    log.api.debug(f'[generate_case_config] 开始推断用例，api_info_id={api_info_id}')
    config = _get_ai_config()
    if not config.get('AI_API_KEY'):
        raise ValueError('AI_API_KEY 未配置，请在系统设置-配置管理中填写 AI 的 API Key')

    api = ApiInfo.objects.get(id=api_info_id)
    method_name = MethodEnum.get_value(api.method) if api.method is not None else 'UNKNOWN'
    log.api.debug(f'[generate_case_config] 接口信息: name={api.name!r}, url={api.url!r}, method={method_name}')

    # 构造接口摘要给 AI（不含 headers，由全局管理）
    api_summary = {
        'name': api.name,
        'url': api.url,
        'method': method_name,
        'params': api.params,
        'json_body': api.json,
        'data': api.data,
    }

    system_prompt = """你是一个专业的接口测试专家。
根据给定的接口信息，生成多条测试用例配置，覆盖正常流程和常见异常场景。

返回严格的 JSON 对象，包含以下字段：
- cases: 数组，每项代表一条测试用例，每项包含：
  - case_name: 用例名称（如：接口名称_正常流程、接口名称_参数缺失、接口名称_未授权 等）
  - step_name: 步骤名称（格式：步骤1-接口名称）

要求：
1. 至少生成3条用例，包含正常流程和至少2个异常场景
2. case_name 不超过60个字符
3. step_name 不超过124个字符

只返回 JSON，不要有任何额外说明文字。"""

    result = _call_ai([
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': f'接口信息：\n{json.dumps(api_summary, ensure_ascii=False, indent=2)}'},
    ], config)

    cases = result.get('cases', [])
    log.api.debug(f'[generate_case_config] AI返回用例数量={len(cases)}')

    # 保底：AI 未返回 cases 时给一条默认
    if not cases:
        log.api.debug('[generate_case_config] AI未返回cases，使用默认用例')
        cases = [{'case_name': f'{api.name}_正常流程', 'step_name': f'步骤1-{api.name}'}]

    # 截断长度限制
    for case in cases:
        case.setdefault('case_name', f'{api.name}_自动用例')
        case.setdefault('step_name', f'步骤1-{api.name}')
        if len(case['case_name']) > 60:
            case['case_name'] = case['case_name'][:60]
        if len(case['step_name']) > 124:
            case['step_name'] = case['step_name'][:124]

    log.api.debug(f'[generate_case_config] 最终用例列表={[c["case_name"] for c in cases]}')
    return cases
