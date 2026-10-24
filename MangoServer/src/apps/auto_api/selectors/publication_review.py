from urllib.parse import urlsplit

from mangotools.enums import MethodEnum

from src.apps.auto_api.enums.case import ApiCaseReleaseStatusEnum
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.exceptions.definitions import API_VERSION_CASE_NOT_FOUND, API_CASE_PREPUBLICATION_NOT_FOUND
from src.apps.auto_api.models import ApiCase, ApiCaseRelease
from src.apps.auto_api.enums.public import ApiPublicTypeEnum
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.selectors.case_configuration import ApiCaseConfigurationSelector
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.selectors.publication_review import publication_review_summary


class ApiPublicationReviewSelector:
    @staticmethod
    def content(payload):
        content = dict(payload or {})
        steps, methods, details = [], [], []
        for index, step in enumerate(content.get('api_case_detailed') or [], 1):
            snapshot = step.get('api_info_snapshot') or {}
            info = (snapshot.get('payload') or {}).get('api_info') or {}
            method = MethodEnum.obj().get(info.get('method'), '未知协议／方法')
            methods.append(method)
            steps.append(f"{index}. {snapshot.get('name') or '未命名接口'} · {method} {urlsplit(str(info.get('url') or '')).path}")
            scenarios = step.get('api_case_detailed_parameter') or []
            details.append({'title': steps[-1], 'lines': [
                f"场景 {position}：{scenario.get('name') or '未命名'}；断言配置 " + '、'.join(
                    label for key, label in (
                        ('ass_general', '通用'), ('ass_jsonpath', 'JSONPath'), ('ass_sql', 'SQL'),
                        ('ass_json_all', 'JSON 全匹配'), ('ass_text_all', '文本全匹配'), ('ass_schema', 'Schema'),
                    ) if scenario.get(key)
                ) for position, scenario in enumerate(scenarios, 1)
            ] or ['未配置参数场景']})
        content.update(steps=steps, methods=methods, step_details=details)
        public_ids = (content.get('api_case') or {}).get('front_public') or []
        if public_ids:
            content['public_dependencies'] = [{'id': item['id'], 'status': item['status'], 'sql': item['value'], 'name': item['name']} for item in ApiQuerySelector.api_public().filter(
                id__in=public_ids, type=ApiPublicTypeEnum.SQL.value).values('id', 'status', 'name', 'value')]
        return content

    @classmethod
    def review(cls, case_id, operator_id):
        case = ApiCase.objects.select_related('project_product', 'module', 'case_people').filter(id=case_id).first()
        if not case:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,))
        release = ApiCaseRelease.objects.select_related('revision').filter(
            api_case_id=case_id, status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value).first()
        if not release:
            raise AutoApiError(API_CASE_PREPUBLICATION_NOT_FOUND)
        revision = release.revision
        # 执行场景属于 Case 元数据，不进入可执行快照；描述仍取待审核修订。
        from copy import copy
        candidate = copy(case)
        metadata = (revision.payload or {}).get('api_case') or {}
        candidate.scenario_description = metadata.get('scenario_description') or ''
        content = cls.content(revision.payload)
        result = publication_review_summary(candidate, product=case.project_product,
                                          case_type=TestCaseTypeEnum.API.value, status=release.status,
                                          is_pending=True,
                                          content=content, operator_id=operator_id, revision=revision)
        configuration = ApiCaseConfigurationSelector.from_payload(
            case.id, case.name, revision.payload, public_sql=content.get('public_dependencies') or [], include_content=True,
        )
        result.update(sql_count=configuration['sql_count'], factory_count=configuration['data_factory_count'],
                      configuration_details=configuration['items'], revision_id=revision.id)
        return result
