from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.exceptions import AutoPytestError
from src.apps.auto_pytest.exceptions.definitions import PYTEST_PUBLICATION_NOT_FOUND
from src.apps.auto_pytest.enums import PytestSourceStatusEnum, PytestAssetStatusEnum, PytestCasePublicationStatusEnum
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.selectors.publication_review import publication_review_summary


class PytestPublicationReviewSelector:
    @staticmethod
    def review(case_id, operator_id):
        case = PytestCase.objects.select_related('project_product__project_product', 'module', 'case_people').filter(id=case_id).first()
        if not case or not case.project_product or not case.project_product.project_product:
            raise AutoPytestError(PYTEST_PUBLICATION_NOT_FOUND)
        result = publication_review_summary(case, product=case.project_product.project_product,
                                            case_type=TestCaseTypeEnum.PYTEST.value, status=case.publication_status,
                                            is_pending=case.publication_status == PytestCasePublicationStatusEnum.PREPUBLISHED.value,
                                            content={'steps': [case.file_path], 'review_items': [
                                                {'label': 'Pytest 项目', 'content': case.project_product.name},
                                                {'label': '文件路径', 'content': case.file_path},
                                                {'label': '源码提交', 'content': case.source_commit or '未记录'},
                                            ]}, operator_id=operator_id)
        result['source_status'] = PytestSourceStatusEnum.obj().get(case.source_status)
        result['asset_status'] = PytestAssetStatusEnum.obj().get(case.asset_status)
        if case.source_status in (PytestSourceStatusEnum.MISSING.value, PytestSourceStatusEnum.PARSE_FAILED.value,
                                  PytestSourceStatusEnum.CONFLICT.value) or case.asset_status in (
            PytestAssetStatusEnum.DISABLED.value, PytestAssetStatusEnum.ARCHIVED.value, PytestAssetStatusEnum.IGNORED.value,
        ):
            result['eligibility_reasons'].append('源码不可用或资产已停用、归档、忽略')
        return result
