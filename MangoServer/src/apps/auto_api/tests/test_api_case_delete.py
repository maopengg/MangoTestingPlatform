from django.test import TestCase
from mangotools.enums import TaskEnum

from src.apps.auto_api.models import ApiCase, ApiCaseRelease, ApiCaseRevision
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import (
    ProductModule,
    Project,
    ProjectProduct,
    TestSuite,
    TestSuiteDetails,
)
from src.apps.user.models import User


class ApiCaseDeleteTests(TestCase):
    def test_delete_preserves_report_and_detaches_version_references(self):
        project = Project.objects.create(name='删除测试项目')
        product = ProjectProduct.objects.create(project=project, name='开放平台')
        module = ProductModule.objects.create(project_product=product, name='订单模块')
        owner = User.objects.create(name='删除测试负责人', username='api_case_delete_owner', password='pwd')
        api_case = ApiCase.objects.create(
            project_product=product,
            module=module,
            name='待删除 API Case',
            case_people=owner,
        )
        revision = ApiCaseRevision.objects.create(
            api_case=api_case,
            revision_no=1,
            payload={},
            checksum='delete-test-checksum',
        )
        release = ApiCaseRelease.objects.create(
            api_case=api_case,
            revision=revision,
            version_no=1,
            version_label='V1',
            is_current=True,
        )
        suite = TestSuite.objects.create(
            id=987654322,
            project_product=product,
            test_env=0,
            user=owner,
            status=TaskEnum.FAIL.value,
            is_notice=0,
        )
        detail = TestSuiteDetails.objects.create(
            test_suite=suite,
            type=TestCaseTypeEnum.API.value,
            project_product=product,
            test_env=0,
            case_id=api_case.id,
            case_name=api_case.name,
            status=TaskEnum.FAIL.value,
            retry=0,
            api_case_revision=revision,
            api_case_release=release,
            config_checksum=revision.checksum,
        )
        case_id = api_case.id

        api_case.delete()

        detail.refresh_from_db()
        self.assertFalse(ApiCase.objects.filter(id=case_id).exists())
        self.assertFalse(ApiCaseRevision.objects.filter(id=revision.id).exists())
        self.assertFalse(ApiCaseRelease.objects.filter(id=release.id).exists())
        self.assertIsNone(detail.api_case_revision_id)
        self.assertIsNone(detail.api_case_release_id)
        self.assertIsNone(detail.config_checksum)
        self.assertEqual(detail.case_id, case_id)
        self.assertEqual(detail.case_name, '待删除 API Case')
