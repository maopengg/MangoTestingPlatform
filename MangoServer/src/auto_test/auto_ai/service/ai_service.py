# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: AI分析服务，对接 DeepSeek / OpenAI 兼容接口
# @Author : 毛鹏
import json
import threading
import time

from src.enums.ai_enum import (
    AiRequirementStatusEnum,
    AiConfirmStatusEnum,
    AiTestPointTypeEnum,
    AiCasePriorityEnum,
    AiCaseTypeEnum,
    AiCaseStatusEnum,
)
from src.enums.system_enum import CacheDataKeyEnum
from src.tools.log_collector import log


def _get_ai_client():
    from openai import OpenAI
    api_key = CacheDataKeyEnum.get_cache_value(CacheDataKeyEnum.AI_API_KEY)
    base_url = CacheDataKeyEnum.get_cache_value(CacheDataKeyEnum.AI_BASE_URL)
    model = CacheDataKeyEnum.get_cache_value(CacheDataKeyEnum.AI_MODEL)
    timeout = int(CacheDataKeyEnum.get_cache_value(CacheDataKeyEnum.AI_TIMEOUT) or 300)
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    return client, model


def _call_ai(system_prompt: str, user_prompt: str, max_retries: int = 3) -> str:
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            client, model = _get_ai_client()
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_err = e
            retry_msg = '重试中...' if attempt < max_retries else '已达最大重试次数'
            log.system.warning(f'[AI] 第 {attempt} 次调用失败: {e}，{retry_msg}')
            if attempt < max_retries:
                time.sleep(2 * attempt)
    raise last_err


def _parse_json_from_ai(text: str):
    text = text.strip()
    if text.startswith('```'):
        lines = [l for l in text.split('\n') if not l.strip().startswith('```')]
        text = '\n'.join(lines).strip()
    return json.loads(text)


class AiService:

    @staticmethod
    def start_analyze(requirement_id: int, user_id: int):
        t = threading.Thread(
            target=AiService._do_analyze,
            args=(requirement_id,),
            daemon=True,
            name=f'ai-analyze-{requirement_id}'
        )
        t.start()

    @staticmethod
    def start_generate_points(requirement_id: int):
        t = threading.Thread(
            target=AiService._do_generate_points,
            args=(requirement_id,),
            daemon=True,
            name=f'ai-points-{requirement_id}'
        )
        t.start()

    @staticmethod
    def start_generate_cases(requirement_id: int):
        t = threading.Thread(
            target=AiService._do_generate_cases,
            args=(requirement_id,),
            daemon=True,
            name=f'ai-cases-{requirement_id}'
        )
        t.start()

    @staticmethod
    def _do_analyze(requirement_id: int):
        from src.auto_test.auto_ai.models import AiRequirement, AiRequirementSplit
        try:
            req = AiRequirement.objects.get(id=requirement_id)
            AiRequirement.objects.filter(id=requirement_id).update(
                status=AiRequirementStatusEnum.SPLITTING.value
            )
            content = AiService._get_requirement_content(req)
            system_prompt = (
                '你是一名资深测试工程师，擅长需求分析和测试用例设计。'
                '请根据用户提供的需求文档，将需求拆分为多个功能子模块。'
                '输出严格为 JSON 数组，每个元素包含字段：'
                'name（子模块名称）、description（功能描述）、sort（排序数字从1开始）。'
                '只输出 JSON，不要任何多余文字。'
            )
            raw = _call_ai(system_prompt, f'需求文档内容如下：\n\n{content}')
            splits = _parse_json_from_ai(raw)
            AiRequirementSplit.objects.filter(requirement_id=requirement_id).delete()
            for item in splits:
                AiRequirementSplit.objects.create(
                    project_product_id=req.project_product_id,
                    module_id=req.module_id,
                    requirement_id=requirement_id,
                    name=item.get('name', ''),
                    description=item.get('description', ''),
                    sort=item.get('sort', 0),
                    is_confirmed=AiConfirmStatusEnum.PENDING.value,
                    ai_raw=raw,
                )
            AiRequirement.objects.filter(id=requirement_id).update(
                status=AiRequirementStatusEnum.WAIT_CONFIRM_SPLIT.value
            )
            log.system.info(f'[AI] 需求 {requirement_id} 拆分完成，共 {len(splits)} 个子模块')
        except Exception as e:
            import traceback
            log.system.error(f'[AI] 需求拆分失败 req_id={requirement_id}: {e}\n{traceback.format_exc()}')
            from src.auto_test.auto_ai.models import AiRequirement
            AiRequirement.objects.filter(id=requirement_id).update(
                status=AiRequirementStatusEnum.FAILED.value,
                error_msg=str(e)
            )

    @staticmethod
    def _do_generate_points(requirement_id: int):
        from src.auto_test.auto_ai.models import AiRequirement, AiRequirementSplit, AiTestPoint
        try:
            req = AiRequirement.objects.get(id=requirement_id)
            AiRequirement.objects.filter(id=requirement_id).update(
                status=AiRequirementStatusEnum.GENERATING_POINTS.value
            )
            confirmed_splits = AiRequirementSplit.objects.filter(
                requirement_id=requirement_id,
                is_confirmed=AiConfirmStatusEnum.CONFIRMED.value
            )
            AiTestPoint.objects.filter(requirement_id=requirement_id).delete()
            system_prompt = (
                '你是一名资深测试工程师。请根据提供的功能子模块描述，生成测试点列表。'
                '输出严格为 JSON 数组，每个元素包含字段：'
                'name（测试点名称）、description（测试点描述）、'
                'test_type（测试类型，0=功能,1=边界,2=异常,3=性能）。'
                '只输出 JSON，不要任何多余文字。'
            )
            for split in confirmed_splits:
                user_prompt = (
                    f'功能子模块：{split.name}\n'
                    f'模块描述：{split.description or ""}\n'
                    f'请为该模块生成完整的测试点。'
                )
                raw = _call_ai(system_prompt, user_prompt)
                points = _parse_json_from_ai(raw)
                for item in points:
                    AiTestPoint.objects.create(
                        project_product_id=req.project_product_id,
                        module_id=req.module_id,
                        requirement_id=requirement_id,
                        requirement_split_id=split.id,
                        name=item.get('name', ''),
                        description=item.get('description', ''),
                        test_type=item.get('test_type', AiTestPointTypeEnum.FUNCTIONAL.value),
                        is_confirmed=AiConfirmStatusEnum.PENDING.value,
                    )
            AiRequirement.objects.filter(id=requirement_id).update(
                status=AiRequirementStatusEnum.WAIT_CONFIRM_POINTS.value
            )
            log.system.info(f'[AI] 需求 {requirement_id} 测试点生成完成')
        except Exception as e:
            import traceback
            log.system.error(f'[AI] 测试点生成失败 req_id={requirement_id}: {e}\n{traceback.format_exc()}')
            from src.auto_test.auto_ai.models import AiRequirement
            AiRequirement.objects.filter(id=requirement_id).update(
                status=AiRequirementStatusEnum.FAILED.value,
                error_msg=str(e)
            )

    @staticmethod
    def _do_generate_cases(requirement_id: int):
        from src.auto_test.auto_ai.models import AiRequirement, AiTestPoint, AiTestCase
        try:
            req = AiRequirement.objects.get(id=requirement_id)
            AiRequirement.objects.filter(id=requirement_id).update(
                status=AiRequirementStatusEnum.GENERATING_CASES.value
            )
            confirmed_points = AiTestPoint.objects.filter(
                requirement_id=requirement_id,
                is_confirmed=AiConfirmStatusEnum.CONFIRMED.value
            ).select_related('requirement_split')
            AiTestCase.objects.filter(requirement_id=requirement_id).delete()
            system_prompt = (
                '你是一名资深测试工程师。请根据提供的测试点，生成标准的功能测试用例。'
                '输出严格为 JSON 数组，每个元素包含字段：'
                'case_no（用例编号，如TC-001）、title（用例标题）、'
                'precondition（前置条件）、'
                'steps（测试步骤，数组，每个元素为字符串）、'
                'expected（预期结果）、'
                'priority（优先级，0=低,1=中,2=高,3=紧急）、'
                'case_type（用例类型，0=正常,1=异常,2=边界）。'
                '只输出 JSON，不要任何多余文字。'
            )
            case_counter = 1
            for point in confirmed_points:
                split_name = point.requirement_split.name if point.requirement_split else ''
                user_prompt = (
                    f'测试点名称：{point.name}\n'
                    f'测试点描述：{point.description or ""}\n'
                    f'所属模块：{split_name}\n'
                    f'请为该测试点生成详细测试用例，用例编号从 TC-{case_counter:03d} 开始。'
                )
                raw = _call_ai(system_prompt, user_prompt)
                cases = _parse_json_from_ai(raw)
                for item in cases:
                    AiTestCase.objects.create(
                        project_product_id=req.project_product_id,
                        module_id=req.module_id,
                        requirement_id=requirement_id,
                        requirement_split_id=point.requirement_split_id,
                        test_point_id=point.id,
                        case_no=item.get('case_no', f'TC-{case_counter:03d}'),
                        title=item.get('title', ''),
                        module_name=split_name,
                        precondition=item.get('precondition', ''),
                        steps=item.get('steps', []),
                        expected=item.get('expected', ''),
                        priority=item.get('priority', AiCasePriorityEnum.MEDIUM.value),
                        case_type=item.get('case_type', AiCaseTypeEnum.NORMAL.value),
                        status=AiCaseStatusEnum.DRAFT.value,
                    )
                    case_counter += 1
            AiRequirement.objects.filter(id=requirement_id).update(
                status=AiRequirementStatusEnum.COMPLETED.value
            )
            log.system.info(f'[AI] 需求 {requirement_id} 用例生成完成，共 {case_counter - 1} 条')
        except Exception as e:
            import traceback
            log.system.error(f'[AI] 用例生成失败 req_id={requirement_id}: {e}\n{traceback.format_exc()}')
            from src.auto_test.auto_ai.models import AiRequirement
            AiRequirement.objects.filter(id=requirement_id).update(
                status=AiRequirementStatusEnum.FAILED.value,
                error_msg=str(e)
            )

    @staticmethod
    def _get_requirement_content(req) -> str:
        from src.enums.ai_enum import AiRequirementInputTypeEnum
        input_type = req.input_type
        if input_type == AiRequirementInputTypeEnum.TEXT.value:
            return req.input_content or ''
        elif input_type == AiRequirementInputTypeEnum.URL.value:
            import requests
            from bs4 import BeautifulSoup
            resp = requests.get(req.input_content, timeout=30)
            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            return soup.get_text(separator='\n', strip=True)[:8000]
        elif input_type == AiRequirementInputTypeEnum.WORD.value:
            from docx import Document
            doc = Document(req.input_file.path)
            return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())[:8000]
        elif input_type == AiRequirementInputTypeEnum.IMAGE.value:
            import base64
            with open(req.input_file.path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            return f'[IMAGE_BASE64]{b64}'
        return req.input_content or ''
