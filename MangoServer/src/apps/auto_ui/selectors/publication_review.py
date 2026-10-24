from src.apps.auto_ui.models import UiCase, UiCaseStepsDetailed, PageStepsDetailed
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.exceptions.definitions import UI_CASE_PUBLICATION_NOT_FOUND
from src.apps.auto_ui.enums import UiPublicTypeEnum, UiCasePublicationStatusEnum
from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.data_factory.enums.execution import DataFactoryCaseSourceTypeEnum
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.selectors.publication_review import publication_review_summary


class UiPublicationReviewSelector:
    @staticmethod
    def content(case):
        bindings = list(UiCaseStepsDetailed.objects.filter(case_id=case.id).select_related('page_step').order_by('case_sort'))
        nodes = list(PageStepsDetailed.objects.filter(page_step_id__in=[item.page_step_id for item in bindings]).values(
            'page_step_id', 'step_sort', 'ope_key', 'sql', 'sql_execute', 'func', 'custom', 'precondition', 'postcondition'))
        public_sql = list(UiQuerySelector.ui_public().filter(id__in=case.front_public or [],
                                                           type=UiPublicTypeEnum.SQL.value).values('name', 'value'))
        factories = list(DataFactoryQuerySelector.data_factory_case_config().filter(
            source_type=DataFactoryCaseSourceTypeEnum.UI_CASE.value, source_id=case.id).values(
                'id', 'name', 'stage', 'status', 'sort', 'source_type', 'source_id', 'template_id',
                'template__name', 'cleanup_strategy', 'field_overrides'))
        return {'front_sql': case.front_sql, 'posterior_sql': case.posterior_sql, 'front_custom': case.front_custom,
                'front_public': case.front_public, 'front_auth_config': case.front_auth_config,
                'nodes': nodes, 'data_factory_configs': factories,
                'public_dependencies': [{'sql': item['value'], 'name': item['name']} for item in public_sql],
                'step_details': [{'title': item.page_step.name, 'lines': [
                    f"节点 {node['step_sort']}：{node['ope_key'] or ('SQL' if node['sql'] or node['sql_execute'] else '自定义／条件')}"
                    for node in sorted(nodes, key=lambda entry: entry['step_sort']) if node['page_step_id'] == item.page_step_id
                ]} for item in bindings],
                'steps': [f'{index}. {item.page_step.name}' for index, item in enumerate(bindings, 1)]}

    @classmethod
    def review(cls, case_id, operator_id):
        case = UiCase.objects.select_related('project_product', 'module', 'case_people').filter(id=case_id).first()
        if not case:
            raise AutoUiError(UI_CASE_PUBLICATION_NOT_FOUND)
        result = publication_review_summary(case, product=case.project_product, case_type=TestCaseTypeEnum.UI.value,
                                            status=case.publication_status,
                                            is_pending=case.publication_status == UiCasePublicationStatusEnum.PREPUBLISHED.value,
                                            content=cls.content(case), operator_id=operator_id)
        return result
