import json
import re

from requests import RequestException

from src.apps.system.exceptions import AiError
from src.apps.system.services.ai.client import AiService
from src.common.prompts.api_assertion_diagnosis import build_assertion_diagnosis_messages


class AssertionDiagnosisService:
    MAX_ASSERTIONS = 100
    MAX_VALUE_LENGTH = 500
    MAX_CONTEXT_LENGTH = 24000
    MAX_FAILED_ITEMS = 20
    SENSITIVE_KEY = re.compile(r'authorization|cookie|token|password|secret|api[_-]?key', re.I)
    SENSITIVE_TEXT = re.compile(
        r'(?i)(bearer\s+)[a-z0-9._~+/-]+|'
        r'(["\']?(?:authorization|cookie|token|password|secret|api[_-]?key)["\']?\s*[:=]\s*(?:bearer\s+)?["\']?)[^"\'\s,;}]+',
    )

    @classmethod
    def _safe_value(cls, value, key='', depth=0):
        if cls.SENSITIVE_KEY.search(str(key)):
            return '[已隐藏]'
        if depth >= 3:
            return '[嵌套内容已省略]'
        if isinstance(value, dict):
            cleaned = {str(k)[:80]: cls._safe_value(v, k, depth + 1) for k, v in list(value.items())[:15]}
            encoded = json.dumps(cleaned, ensure_ascii=False)
            return cleaned if len(encoded) <= cls.MAX_VALUE_LENGTH else encoded[:cls.MAX_VALUE_LENGTH] + '…'
        if isinstance(value, list):
            cleaned = [cls._safe_value(v, depth=depth + 1) for v in value[:15]]
            encoded = json.dumps(cleaned, ensure_ascii=False)
            return cleaned if len(encoded) <= cls.MAX_VALUE_LENGTH else encoded[:cls.MAX_VALUE_LENGTH] + '…'
        text = str(value if value is not None else '')
        text = cls.SENSITIVE_TEXT.sub(lambda match: (match.group(1) or match.group(2)) + '[已隐藏]', text)
        return text[:cls.MAX_VALUE_LENGTH]

    @classmethod
    def analyze(cls, raw_assertions) -> dict:
        if not isinstance(raw_assertions, list):
            return cls._unavailable('断言数据格式不正确', 0)
        failed = [(index, item) for index, item in enumerate(raw_assertions)
                  if isinstance(item, dict) and str(item.get('status')) == '0']
        if not failed:
            return cls._unavailable('没有失败断言，无需 AI 分析', 0)
        assertions = []
        for index, item in failed[:cls.MAX_FAILED_ITEMS]:
            assertion = {
                'assertion_index': index,
                'method': cls._safe_value(item.get('method'), 'method'),
                'message': cls._safe_value(item.get('ass_msg'), 'message'),
                'actual': cls._safe_value(item.get('actual'), 'actual'),
                'expected': cls._safe_value(item.get('expect'), 'expected'),
                'actual_source': cls._safe_value(item.get('actual_source'), 'actual_source'),
                'expected_source': cls._safe_value(item.get('expect_source'), 'expected_source'),
                'source_type': cls._safe_value(item.get('source_type'), 'source_type'),
                'group': cls._safe_value(item.get('group_name'), 'group'),
                'group_logic': cls._safe_value(item.get('group_logic'), 'group_logic'),
                'raw_config': cls._safe_value(item.get('raw_config'), 'raw_config'),
                'resolved_config': cls._safe_value(item.get('resolved_config'), 'resolved_config'),
            }
            assertions.append(assertion)
            if len(json.dumps(assertions, ensure_ascii=False)) > cls.MAX_CONTEXT_LENGTH:
                assertions.pop()
                break
        omitted_count = len(failed) - len(assertions)
        base = {'failed_count': len(failed), 'analyzed_count': 0,
                'omitted_count': omitted_count, 'items': []}
        if not assertions:
            return {'available': False, 'reason': '断言内容过长，请缩小分析范围',
                    'summary': '', **base}
        try:
            config = AiService.load_config()
            AiService._validate_base_config(config)
        except AiError:
            return {'available': False, 'reason': '尚未配置可用的 AI 服务，请先在系统设置中配置',
                    'summary': '', **base}
        try:
            response = AiService.json_chat(
                messages=build_assertion_diagnosis_messages(assertions),
                temperature=0,
                max_tokens=1000,
                thinking={'type': 'disabled'},
            )
            content = ((response.get('choices') or [{}])[0].get('message') or {}).get('content')
            parsed = content if isinstance(content, dict) else json.loads(str(content or '{}'))
            valid_indices = {item['assertion_index'] for item in assertions}
            seen = set()
            items = []
            for item in parsed.get('items') or []:
                if not isinstance(item, dict):
                    continue
                index = item.get('assertion_index')
                if type(index) is not int or index not in valid_indices or index in seen:
                    continue
                explanation = str(item.get('explanation') or '').strip()[:120]
                if not explanation:
                    continue
                seen.add(index)
                items.append({
                    'assertion_index': index,
                    'explanation': explanation,
                    'next_check': str(item.get('next_check') or '').strip()[:100],
                })
            if not items:
                raise ValueError('empty assertion analysis')
            return {
                'available': True,
                'reason': '',
                'summary': str(parsed.get('summary') or '已分析失败断言').strip()[:160],
                'failed_count': len(failed),
                'analyzed_count': len(items),
                'omitted_count': len(failed) - len(items),
                'items': items,
            }
        except (AiError, RequestException, ValueError, TypeError, KeyError, IndexError):
            return {'available': False, 'reason': 'AI 分析暂时不可用，请稍后重试',
                    'summary': '', **base}
        except Exception:
            return {'available': False, 'reason': 'AI 分析暂时不可用，请稍后重试',
                    'summary': '', **base}

    @staticmethod
    def _unavailable(reason: str, failed_count: int) -> dict:
        return {'available': False, 'reason': reason, 'summary': '', 'failed_count': failed_count,
                'analyzed_count': 0, 'omitted_count': 0, 'items': []}
