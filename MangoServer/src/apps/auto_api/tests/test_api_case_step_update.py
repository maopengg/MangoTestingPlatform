from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import API_VERSION_API_INFO_REVISION_NOT_FOUND, AutoApiError
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.apps.auto_api.api.views.api_case_detailed import ApiCaseDetailedCRUD


class ApiCaseStepUpdateTests(SimpleTestCase):
    def setUp(self):
        self.step = SimpleNamespace(
            id=10, case_id=1, api_info_id=20, pinned_api_info_revision_id=30,
            execution_config={}, save=Mock(),
        )

    def run_update(self, api_info_id=40, revision_id=50):
        return ApiCaseStepService.update_step(
            10, api_info_id=api_info_id, pinned_api_info_revision_id=revision_id,
            execution_config={'is_recovery': True}, operator_id=4,
        )

    @patch('src.apps.auto_api.services.api_case.step.ApiCaseAggregateMutationService.mutate')
    @patch('src.apps.auto_api.services.api_case.step.ApiCaseDetailed.objects')
    @patch.object(ApiCaseStepService, 'resolve_api_runtime')
    def test_update_binding_and_timing_together_without_replacing_scenarios(self, resolve, objects, mutate):
        objects.filter.return_value.first.return_value = self.step
        objects.select_for_update.return_value.get.return_value = self.step
        mutate.side_effect = lambda case_id, **kw: kw['operation'](None)
        resolve.return_value = (object(), 50)
        self.run_update()
        self.assertEqual((self.step.api_info_id, self.step.pinned_api_info_revision_id), (40, 50))
        self.assertEqual(self.step.execution_config, {'is_recovery': True})
        self.assertEqual(self.step.update_user_id, 4)
        self.step.save.assert_called_once()
        resolve.assert_called_once_with(40, pinned_api_info_revision_id=50, allow_draft=False)
        self.assertEqual(mutate.call_args.args, (1,))

    @patch('src.apps.auto_api.services.api_case.step.ApiCaseAggregateMutationService.mutate')
    @patch('src.apps.auto_api.services.api_case.step.ApiCaseDetailed.objects')
    @patch.object(ApiCaseStepService, 'resolve_api_runtime')
    def test_invalid_revision_does_not_partially_save_timing_or_binding(self, resolve, objects, mutate):
        objects.filter.return_value.first.return_value = self.step
        objects.select_for_update.return_value.get.return_value = self.step
        mutate.side_effect = lambda case_id, **kw: kw['operation'](None)
        resolve.side_effect = AutoApiError(API_VERSION_API_INFO_REVISION_NOT_FOUND)
        with self.assertRaises(AutoApiError):
            self.run_update()
        self.step.save.assert_not_called()
        self.assertEqual(self.step.api_info_id, 20)
        self.assertEqual(self.step.execution_config, {})

    @patch('src.apps.auto_api.services.api_case.step.ApiCaseAggregateMutationService.mutate')
    @patch('src.apps.auto_api.services.api_case.step.ApiCaseDetailed.objects')
    @patch.object(ApiCaseStepService, 'resolve_api_runtime')
    def test_unchanged_binding_keeps_its_pinned_revision(self, resolve, objects, mutate):
        objects.filter.return_value.first.return_value = self.step
        objects.select_for_update.return_value.get.return_value = self.step
        mutate.side_effect = lambda case_id, **kw: kw['operation'](None)
        self.run_update(20, 30)
        resolve.assert_not_called()
        self.assertEqual(self.step.pinned_api_info_revision_id, 30)


class ApiCaseStepUpdateScopeTests(SimpleTestCase):
    @patch.object(ApiCaseStepService, 'update_step')
    @patch.object(ApiCaseDetailedCRUD, 'serializer')
    @patch.object(ApiCaseDetailedCRUD, 'get_operator_id', return_value=4)
    @patch.object(ApiCaseDetailedCRUD, 'has_instance_data_scope_permission')
    @patch('src.apps.auto_api.api.views.api_case_detailed.ApiCaseDetailed.objects')
    def test_edit_checks_both_case_and_new_interface_scope(self, objects, scope, operator, serializer, update):
        case = SimpleNamespace(id=1)
        api_info = SimpleNamespace(id=40)
        objects.select_related.return_value.get.return_value = SimpleNamespace(id=10, case=case)
        serializer.return_value.validated_data = {
            'api_info': api_info, 'pinned_api_info_revision': SimpleNamespace(id=50),
            'execution_config': {'is_recovery': True},
        }
        request = SimpleNamespace(data={'id': 10, 'api_info': 40, 'execution_config': {'is_recovery': True}})
        view = ApiCaseDetailedCRUD()
        for allowed in ([False], [True, False]):
            scope.reset_mock()
            scope.side_effect = allowed
            view.put(request)
            update.assert_not_called()
        scope.reset_mock()
        scope.side_effect = [True, True]
        update.return_value = {'step_id': 10}
        view.put(request)
        self.assertEqual([call.args[1] for call in scope.call_args_list], [case, api_info])
        update.assert_called_once_with(
            10, api_info_id=40, pinned_api_info_revision_id=50,
            execution_config={'is_recovery': True}, operator_id=4,
        )
