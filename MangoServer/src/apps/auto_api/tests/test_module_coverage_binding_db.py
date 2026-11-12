from django.test import TestCase

from src.apps.auto_api.models import ApiInfo, ApiInfoHttpConfig, ApiCase, ApiCaseRevision, ModuleCoverageCase
from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService as Service
from src.apps.auto_api.tests.test_module_coverage import ModuleCoverageLifecycleTests as Helpers
from src.apps.test_center.models import ProductModule
from src.apps.user.models import User


class HistoricalBindingDatabaseTests(TestCase):
    setUp = Helpers.setUp
    run_scan = Helpers.run_scan
    case_item = staticmethod(Helpers.case_item)
    interface_item = staticmethod(Helpers.interface_item)

    def test_eight_historical_bindings_survive_reupload_completion_and_direct_rebind(self):
        api = ApiInfo.objects.create(project_product=self.product, module=self.module,
                                     name='AUTO接口', url='/api/contracts/search')
        ApiInfoHttpConfig.objects.create(api_info=api, method=1, url='/api/contracts/search',
                                         body_type='none', is_text_params=1)
        items = [self.case_item(f'AUTO_{index}', f'AUTO场景{index}') for index in range(8)]
        self.run_scan('a' * 40, items)
        owner_module = self.module
        consumer_module = ProductModule.objects.create(project_product=self.product, name='AUTO复用模块', level=1)
        self.module = consumer_module
        self.run_scan('b' * 40, [self.case_item('AUTO_CONSUMER', 'AUTO消费者场景')])
        self.module = owner_module
        user = User.objects.create(name='AUTO负责人', username='AUTO_BINDING', password='AUTO')
        bindings = []
        for index, item in enumerate(items):
            api_case = ApiCase.objects.create(project_product=self.product, module=consumer_module,
                                              name=f'AUTO用例{index}', case_people=user)
            revision = ApiCaseRevision.objects.create(api_case=api_case, revision_no=1,
                payload={'api_case_detailed': [{'api_info_id': api.id}]}, checksum=f'AUTO_{index}')
            coverage = ModuleCoverageCase.objects.get(source_key=item['source_key'])
            historical_revision = None if index == 0 else revision
            coverage.api_case, coverage.api_case_revision, coverage.status = api_case, historical_revision, 'completed'
            coverage.save(update_fields=['api_case', 'api_case_revision', 'status'])
            historical = coverage.current_snapshot
            historical.api_case, historical.api_case_revision = api_case, historical_revision
            historical.save(update_fields=['api_case', 'api_case_revision'])
            bindings.append((coverage.id, api_case.id, revision.id))
            item.update(api_case_id=api_case.id, api_case_revision_id=revision.id)
            item['payload']['current_status'] = 'completed'
        scan = Service.create_scan({'project_product_id': self.product.id, 'module_id': owner_module.id,
            'repository_key': 'backend', 'branch': 'main', 'commit_sha': 'c' * 40,
            'idempotency_key': 'AUTO_REUPLOAD', 'expected_case_count': 8, 'expected_interface_count': 1})
        Service.upload_interfaces(scan.id, [self.interface_item()])
        self.assertEqual(Service.upload_cases(scan.id, items)['created'], 0)
        self.assertEqual(Service.upload_cases(scan.id, items)['unchanged'], 8)
        self.assertTrue(Service.validation(scan)['valid'])
        Service.complete_scan(scan.id)
        self.assertEqual(ApiCase.objects.count(), 8)
        for coverage_id, case_id, revision_id in bindings:
            bound = Service.bind_api_case(coverage_id, case_id)
            self.assertEqual(bound.api_case_revision_id, revision_id)
            self.assertEqual(bound.coverage_validity, 'valid')
        coverage_id, case_id, revision_id = bindings[0]
        different = ApiCaseRevision.objects.create(api_case_id=case_id, revision_no=2,
            payload={'api_case_detailed': []}, checksum='AUTO_OTHER_REVISION')
        before = ModuleCoverageCase.objects.get(id=coverage_id).execution_result
        self.assertEqual(Service.sync_api_case_execution_result(case_id, 1, different.id), 0)
        bound = ModuleCoverageCase.objects.get(id=coverage_id)
        self.assertEqual(bound.api_case_revision_id, revision_id)
        self.assertEqual(bound.execution_result, before)
