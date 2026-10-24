from __future__ import annotations

import json
import logging
import re
from hashlib import sha256
from uuid import uuid4

from django.core.cache import cache
from django.utils import timezone
from requests import RequestException

from src.apps.ai.exceptions import AiError
from src.apps.ai.services.core import extract_ai_json
from src.apps.system.services.ai.client import AiService
from src.apps.system.services.system_config import SystemConfigService
from src.apps.task_center.models import Tasks
from src.common.prompts.quality_effectiveness import (
    build_quality_effectiveness_insight_messages,
    build_quality_effectiveness_summary_messages,
)

logger = logging.getLogger(__name__)


class AutomationEffectivenessAiMixin:
    @staticmethod
    def _refresh_task_diagnostic_paths(data: dict) -> dict:
        """保持效能统计缓存不变，仅同步低成本的排查文档状态。"""
        task_health = data.get('task_health') if isinstance(data, dict) else None
        if not isinstance(task_health, list) or not task_health:
            return data
        task_ids = {
            int(item.get('task_id'))
            for item in task_health
            if (
                    isinstance(item, dict)
                    and str(item.get('task_id') or '').isdigit()
            )
        }
        if not task_ids:
            return data
        diagnostic_paths = dict(
            Tasks.objects.filter(id__in=task_ids).values_list('id', 'diagnostic_file_path')
        )
        for item in task_health:
            if not isinstance(item, dict):
                continue
            task_id = item.get('task_id')
            normalized_task_id = int(task_id) if str(task_id or '').isdigit() else None
            item['diagnostic_file_path'] = diagnostic_paths.get(normalized_task_id)
        return data

    @classmethod
    def clear_cache(cls, request) -> None:
        cache.set(cls._generation_key(request), uuid4().hex, timeout=None)

    @classmethod
    def ai_summary(cls, request) -> dict:
        if isinstance(request.data, dict) and request.data.get('mode') == 'insights':
            return cls._ai_insights(request)
        overview = request.data.get('overview') if isinstance(request.data, dict) else None
        context = request.data.get('context') if isinstance(request.data, dict) else None
        force = bool(request.data.get('force')) if isinstance(request.data, dict) else False
        if not isinstance(overview, dict):
            return cls._ai_unavailable('缺少可供分析的质量效能数据')
        context = context if isinstance(context, dict) else {}
        ai_input = {
            'context': context,
            'overview': overview,
        }
        payload = json.dumps(ai_input, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        cache_key = cls._ai_summary_cache_key(request, payload)
        if not force:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data
        try:
            config = AiService.load_config()
            AiService._validate_base_config(config)
            response = AiService.json_chat(
                messages=build_quality_effectiveness_summary_messages(payload),
                temperature=0,
                max_tokens=2600,
                thinking={'type': 'disabled'},
            )
            summary = cls._normalize_ai_summary(extract_ai_json(response))
        except (AiError, RequestException, ValueError, TypeError, KeyError) as error:
            return cls._ai_unavailable(str(error))
        except Exception:
            logger.exception('生成自动化效能AI总结失败')
            return cls._ai_unavailable('AI总结生成失败，请稍后重试或检查AI配置')
        result = {
            'available': True,
            'model': config.model,
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': summary,
        }
        cache.set(cache_key, result, SystemConfigService.get_ranged_int('EFFECTIVENESS_AI_CACHE_SECONDS'))
        return result

    @classmethod
    def _ai_insights(cls, request) -> dict:
        overview = request.data.get('overview') if isinstance(request.data, dict) else None
        context = request.data.get('context') if isinstance(request.data, dict) else None
        force = bool(request.data.get('force')) if isinstance(request.data, dict) else False
        requested_keys = request.data.get('insight_keys') if isinstance(request.data, dict) else None
        if not isinstance(overview, dict):
            return cls._ai_unavailable('缺少可供解读的质量效能数据')
        context = context if isinstance(context, dict) else {}
        keys = (
            [key for key in requested_keys if key in cls.AI_INSIGHT_CONFIGS]
            if isinstance(requested_keys, list)
            else list(cls.AI_INSIGHT_CONFIGS)
        )
        insights = {}
        pending = []
        for key in keys:
            insight_input = cls._ai_insight_input(key, overview, context)
            payload = json.dumps(
                insight_input,
                ensure_ascii=False,
                sort_keys=True,
                separators=(',', ':'),
            )
            cache_key = cls._ai_insight_cache_key(request, key, payload)
            cached_data = None if force else cache.get(cache_key)
            if isinstance(cached_data, dict) and cached_data.get('insight'):
                insights[key] = cached_data['insight']
            else:
                pending.append((key, payload, cache_key))

        if not pending:
            return {
                'available': bool(insights),
                'model': '',
                'generated_at': '',
                'insights': insights,
            }
        try:
            config = AiService.load_config()
            AiService._validate_base_config(config)
        except (AiError, RequestException, ValueError, TypeError, KeyError) as error:
            if insights:
                return {
                    'available': True,
                    'model': '',
                    'generated_at': '',
                    'insights': insights,
                }
            return cls._ai_unavailable(str(error))

        for key, payload, cache_key in pending:
            try:
                response = AiService.json_chat(
                    messages=build_quality_effectiveness_insight_messages(key, payload),
                    temperature=0,
                    max_tokens=280,
                    thinking={'type': 'disabled'},
                )
                value = extract_ai_json(response)
                insight = cls._humanize_ai_text(
                    value.get('insight') if isinstance(value, dict) else '',
                    240,
                )
                if not insight:
                    continue
                insights[key] = insight
                cache.set(
                    cache_key,
                    {'insight': insight},
                    SystemConfigService.get_ranged_int('EFFECTIVENESS_AI_CACHE_SECONDS'),
                )
            except (AiError, RequestException, ValueError, TypeError, KeyError):
                continue
            except Exception:
                logger.exception('生成自动化效能组件解读失败: %s', key)

        if not insights:
            return cls._ai_unavailable('AI未返回有效的组件解读')
        return {
            'available': True,
            'model': config.model,
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'insights': insights,
        }

    @classmethod
    def _ai_insight_input(cls, key: str, overview: dict, context: dict) -> dict:
        config = cls.AI_INSIGHT_CONFIGS[key]
        return {
            'context': context,
            'component': config['title'],
            'data': {
                data_key: overview.get(data_key)
                for data_key in config['data_keys']
            },
        }

    @classmethod
    def _ai_insight_cache_key(cls, request, key: str, payload: str) -> str:
        scope_digest = sha256(cls._permission_scope(request).encode('utf-8')).hexdigest()[:16]
        payload_digest = sha256(payload.encode('utf-8')).hexdigest()[:24]
        return (
            f'{cls.CACHE_PREFIX}:ai-insight:{cls.AI_INSIGHT_PROMPT_VERSION}:'
            f'{key}:scope:{scope_digest}:payload:{payload_digest}'
        )

    @classmethod
    def _ai_summary_cache_key(cls, request, payload: str) -> str:
        scope_digest = sha256(cls._permission_scope(request).encode('utf-8')).hexdigest()[:16]
        payload_digest = sha256(payload.encode('utf-8')).hexdigest()[:24]
        return (
            f'{cls.CACHE_PREFIX}:ai-summary:{cls.AI_SUMMARY_PROMPT_VERSION}:'
            f'scope:{scope_digest}:payload:{payload_digest}'
        )

    @classmethod
    def _normalize_ai_summary(cls, value: dict) -> dict:
        if not isinstance(value, dict):
            raise ValueError('AI未返回有效的结构化总结')

        def text(key, limit):
            return cls._humanize_ai_text(value.get(key), limit)

        def items(key, limit, fields):
            result = []
            for item in value.get(key) or []:
                if not isinstance(item, dict):
                    continue
                normalized = {}
                for field in fields:
                    if field in {'severity', 'priority', 'target_type', 'target_value'}:
                        normalized[field] = str(item.get(field) or '').strip()[:500]
                    else:
                        normalized[field] = cls._humanize_ai_text(item.get(field), 500)
                if normalized.get('title'):
                    result.append(normalized)
                if len(result) >= limit:
                    break
            return result

        trend = value.get('quality_trend') if isinstance(value.get('quality_trend'), dict) else {}
        status = str(trend.get('status') or 'unknown').strip().lower()
        if status not in {'improving', 'stable', 'declining', 'unknown'}:
            status = 'unknown'

        def insight_map(field, keys):
            raw_insights = value.get(field) if isinstance(value.get(field), dict) else {}
            result = {}
            for key in keys:
                insight = cls._humanize_ai_text(raw_insights.get(key), 240)
                if insight:
                    result[key] = insight
            return result

        chart_insights = insight_map(
            'chart_insights',
            (
                'trend',
                'environment',
                'task_type',
                'coverage_scope',
                'module_risk',
                'issue_pareto',
                'environment_task_matrix',
                'module_change',
                'automation_type',
                'task_health',
                'failed_case_ranking',
            ),
        )
        component_insights = insight_map(
            'component_insights',
            ('overview', 'status', 'modules', 'benefits'),
        )
        summary = {
            'headline': text('headline', 48) or '质量效能总结',
            'executive_summary': text('executive_summary', 600),
            'quality_trend': {
                'status': status,
                'label': cls._humanize_ai_text(trend.get('label'), 48) or '暂无明确趋势',
                'analysis': cls._humanize_ai_text(trend.get('analysis'), 400),
            },
            'benefits': items('benefits', 4, ('title', 'detail', 'evidence')),
            'risks': items('risks', 5, ('title', 'detail', 'severity')),
            'recommendations': items(
                'recommendations',
                5,
                ('title', 'detail', 'priority', 'target_type', 'target_value'),
            ),
            'chart_insights': chart_insights,
            'component_insights': component_insights,
        }
        for recommendation in summary['recommendations']:
            if recommendation.get('target_type') not in {
                'module',
                'environment',
                'task',
                'status',
                'all',
            }:
                recommendation['target_type'] = 'all'
            if recommendation['target_type'] == 'all':
                recommendation['target_value'] = ''
        if not summary['executive_summary']:
            raise ValueError('AI总结内容为空')
        return summary

    @classmethod
    def _humanize_ai_text(cls, value, limit: int) -> str:
        text = str(value or '').strip()
        for field, (label, unit) in cls.AI_METRIC_LABELS.items():
            pattern = rf'\b{re.escape(field)}\s*=\s*([+-]?\d+(?:\.\d+)?%?)'

            def replace_metric(match, *, metric_label=label, metric_unit=unit):
                metric_value = match.group(1)
                suffix = '' if metric_value.endswith('%') else metric_unit
                separator = '' if suffix in {'', '%'} else ' '
                return f'{metric_label} {metric_value}{separator}{suffix}'

            text = re.sub(pattern, replace_metric, text, flags=re.IGNORECASE)
        text = re.sub(
            r'\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\s*=\s*[^,，;；。\s]+',
            '',
            text,
        )
        text = re.sub(r'\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b', '', text)
        text = re.sub(r'\s*[,，;；]\s*[,，;；]+', '，', text)
        text = re.sub(r'\s*,\s*', '，', text)
        return text.strip(' ,，;；')[:limit]

    @staticmethod
    def _ai_unavailable(reason: str) -> dict:
        return {
            'available': False,
            'reason': str(reason or 'AI服务暂不可用')[:300],
            'setup_path': '/system/settings/index',
        }
