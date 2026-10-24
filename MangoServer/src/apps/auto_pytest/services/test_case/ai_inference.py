from __future__ import annotations

import re
from collections import defaultdict

from src.apps.ai.exceptions import AiError
from src.apps.ai.services.core import extract_ai_json
from src.apps.auto_api.enums.case import (
    ApiCaseScenarioLayerEnum,
    ApiCaseScenarioTagEnum,
    ApiCaseScenarioTypeEnum,
)
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_PERMISSION_INVALID,
    PYTEST_FAILED,
)
from src.apps.auto_pytest.services.git_management.repository_service import RepositoryGitService
from src.apps.system.services.ai.client import AiService
from src.apps.test_center.enums import CaseLevelEnum
from src.apps.test_center.models import ProductModule
from src.common.prompts.pytest_case_inference import build_pytest_case_inference_messages


class PytestCaseAiInferenceService:
    MAX_BATCH_SIZE = 500
    AI_CHUNK_SIZE = 8
    MAX_SOURCE_CHARS = 12000
    SENSITIVE_PATTERN = re.compile(
        r'(?i)([\"\']?(?:authorization|api[_-]?key|access[_-]?token|password|passwd|secret|cookie)'
        r'[\"\']?\s*[=:]\s*)([\"\'])(.*?)(\2)'
    )

    @classmethod
    def normalize_case_ids(cls, raw_case_ids) -> list[int]:
        if not isinstance(raw_case_ids, list) or not 1 <= len(raw_case_ids) <= cls.MAX_BATCH_SIZE:
            raise AutoPytestError(PYTEST_PERMISSION_INVALID)
        case_ids = []
        seen = set()
        for raw_id in raw_case_ids:
            try:
                case_id = int(raw_id)
            except (TypeError, ValueError):
                raise AutoPytestError(PYTEST_PERMISSION_INVALID)
            if case_id <= 0 or case_id in seen:
                raise AutoPytestError(PYTEST_PERMISSION_INVALID)
            seen.add(case_id)
            case_ids.append(case_id)
        return case_ids

    @classmethod
    def infer(cls, queryset, raw_case_ids) -> dict:
        case_ids = cls.normalize_case_ids(raw_case_ids)
        cases = list(
            queryset.filter(id__in=case_ids).select_related(
                'project_product__project_product',
                'project_product__repository__credential',
                'module',
            )
        )
        if len(cases) != len(case_ids):
            raise AutoPytestError(PYTEST_PERMISSION_INVALID)
        case_map = {case.id: case for case in cases}
        ordered_cases = [case_map[case_id] for case_id in case_ids]
        modules = cls._load_modules(ordered_cases)
        source_map = cls._load_sources(ordered_cases)
        predictions = []
        try:
            for start in range(0, len(ordered_cases), cls.AI_CHUNK_SIZE):
                chunk = ordered_cases[start:start + cls.AI_CHUNK_SIZE]
                payload = cls._build_payload(chunk, modules, source_map)
                response = AiService.json_chat(
                    build_pytest_case_inference_messages(payload),
                    temperature=0,
                    max_tokens=6000,
                    thinking={'type': 'disabled'},
                )
                parsed = extract_ai_json(response)
                predictions.extend(cls._normalize_predictions(chunk, modules, parsed))
        except AutoPytestError:
            raise
        except AiError as error:
            raise AutoPytestError(PYTEST_FAILED, value=(str(error),)) from error
        except Exception as error:
            raise AutoPytestError(PYTEST_FAILED, value=(type(error).__name__,)) from error
        return {'predictions': predictions, 'inferred_count': len(predictions)}

    @staticmethod
    def _load_modules(cases) -> dict[int, list[ProductModule]]:
        project_product_ids = {
            case.project_product.project_product_id
            for case in cases
            if case.project_product_id and case.project_product
        }
        modules = ProductModule.objects.filter(
            project_product_id__in=project_product_ids,
            level=3,
        ).select_related('parent', 'parent__parent').order_by('project_product_id', 'sort', 'id')
        result = defaultdict(list)
        for module in modules:
            result[module.project_product_id].append(module)
        return dict(result)

    @classmethod
    def _load_sources(cls, cases) -> dict[tuple[int, str], str]:
        source_map = {}
        for case in cases:
            key = (case.project_product_id, case.file_path)
            if key in source_map:
                continue
            try:
                source = RepositoryGitService.for_product(case.project_product).remote_file_content(
                    case.file_path
                )
                source_map[key] = cls._sanitize_source(source)
            except Exception as error:
                source_map[key] = f'[源码读取失败：{type(error).__name__}]'
        return source_map

    @classmethod
    def _sanitize_source(cls, source: str) -> str:
        text = str(source or '')[:cls.MAX_SOURCE_CHARS]
        return cls.SENSITIVE_PATTERN.sub(lambda match: f'{match.group(1)}"***"', text)

    @classmethod
    def _build_payload(cls, cases, modules, source_map) -> dict:
        return {
            'allowed_values': {
                'level': CaseLevelEnum.obj(),
                'scenario_layer': ApiCaseScenarioLayerEnum.obj(),
                'scenario_type': ApiCaseScenarioTypeEnum.obj(),
                'scenario_tags': ApiCaseScenarioTagEnum.obj(),
            },
            'module_candidates': {
                str(project_product_id): [
                    {'id': module.id, 'path': module.get_full_path()}
                    for module in project_modules
                ]
                for project_product_id, project_modules in modules.items()
            },
            'cases': [
                {
                    'id': case.id,
                    'project_product_id': case.project_product.project_product_id,
                    'file_path': case.file_path,
                    'feature_file_path': case.feature_file_path,
                    'source': source_map.get((case.project_product_id, case.file_path), ''),
                    'current': cls._current_values(case),
                }
                for case in cases
            ],
        }

    @staticmethod
    def _current_values(case) -> dict:
        return {
            'name': case.name,
            'module': case.module_id,
            'level': case.level,
            'scenario_layer': case.scenario_layer,
            'scenario_type': case.scenario_type,
            'scenario_tags': list(case.scenario_tags or []),
            'scenario_description': case.scenario_description or '',
        }

    @classmethod
    def _normalize_predictions(cls, cases, modules, parsed) -> list[dict]:
        raw_predictions = parsed.get('predictions') if isinstance(parsed, dict) else []
        raw_map = {
            int(item['id']): item
            for item in raw_predictions or []
            if isinstance(item, dict) and str(item.get('id') or '').isdigit()
        }
        allowed_levels = set(CaseLevelEnum.obj())
        allowed_layers = set(ApiCaseScenarioLayerEnum.obj())
        allowed_types = set(ApiCaseScenarioTypeEnum.obj())
        allowed_tags = set(ApiCaseScenarioTagEnum.obj())
        result = []
        for case in cases:
            current = cls._current_values(case)
            raw = raw_map.get(case.id, {})
            allowed_module_ids = {
                module.id
                for module in modules.get(case.project_product.project_product_id, [])
            }
            module_id = cls._valid_int(raw.get('module'), allowed_module_ids, current['module'])
            name = str(raw.get('name') or current['name']).strip()[:1024] or current['name']
            description = str(
                raw.get('scenario_description') or current['scenario_description']
            ).strip()[:2000]
            raw_tags = raw.get('scenario_tags')
            tags = [tag for tag in raw_tags if tag in allowed_tags] if isinstance(raw_tags, list) else []
            if not tags:
                tags = [tag for tag in current['scenario_tags'] if tag in allowed_tags]
            result.append({
                'id': case.id,
                'name': name,
                'module': module_id,
                'asset_status': case.asset_status,
                'level': cls._valid_int(raw.get('level'), allowed_levels, current['level']),
                'scenario_layer': cls._valid_int(
                    raw.get('scenario_layer'), allowed_layers, current['scenario_layer']
                ),
                'scenario_type': cls._valid_int(
                    raw.get('scenario_type'), allowed_types, current['scenario_type']
                ),
                'scenario_tags': tags,
                'scenario_description': description,
            })
        return result

    @staticmethod
    def _valid_int(value, allowed_values: set, fallback):
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return fallback
        return normalized if normalized in allowed_values else fallback
