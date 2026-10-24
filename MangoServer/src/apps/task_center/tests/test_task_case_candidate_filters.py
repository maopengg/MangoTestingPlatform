from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db.models import Q
from django.test import SimpleTestCase

from src.apps.auto_api.enums.case import ApiCaseScenarioTagEnum
from src.apps.auto_api.models import ApiCase
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_ui.models import UiCase
from src.apps.task_center.api.views.tasks_details import TasksDetailsViews
from src.apps.test_center.enums import TestCaseTypeEnum


class TaskCaseCandidateFilterTests(SimpleTestCase):
    def test_execution_scene_filter_preserves_string_values(self):
        queryset = MagicMock()
        scenes = [
            ApiCaseScenarioTagEnum.TEMPORARY_VALIDATION.value,
            ApiCaseScenarioTagEnum.REGRESSION.value,
        ]
        TasksDetailsViews._filter_json_any(queryset, 'scenario_tags', scenes)
        queryset.filter.assert_called_once_with(
            Q(scenario_tags__contains=[scenes[0]]) | Q(scenario_tags__contains=[scenes[1]])
        )

    def test_empty_execution_scene_filter_keeps_queryset(self):
        queryset = MagicMock()
        self.assertIs(TasksDetailsViews._filter_json_any(queryset, 'scenario_tags', []), queryset)
        queryset.filter.assert_not_called()

    def test_all_case_types_apply_candidate_filters_together(self):
        for case_type, model_name in (
                (TestCaseTypeEnum.UI.value, 'UiCase'),
                (TestCaseTypeEnum.API.value, 'ApiCase'),
                (TestCaseTypeEnum.PYTEST.value, 'PytestCase'),
        ):
            with self.subTest(case_type=case_type):
                queryset = MagicMock()
                queryset.filter.return_value = queryset
                params = {
                    'type': str(case_type),
                    'project_product_id': '10',
                    'case_name': '筛选用例',
                    'levels': '0,1',
                    'scenario_layers': '0,2',
                    'scenario_types': '0,3',
                    'scenario_tags': ApiCaseScenarioTagEnum.TEMPORARY_VALIDATION.value,
                }
                target = 'src.apps.task_center.api.views.tasks_details'
                with (
                    patch(f'{target}.{model_name}.objects') as manager,
                    patch.object(TasksDetailsViews, '_candidate_queryset', return_value=[]),
                    patch.object(TasksDetailsViews, '_serialize_api_case_version_options', return_value=[]),
                ):
                    manager.all.return_value = queryset
                    manager.filter.return_value = queryset
                    response = TasksDetailsViews().get_type_case_name(
                        SimpleNamespace(query_params=params)
                    )
                self.assertEqual(response.data['code'], 200)
                for kwargs in (
                        {'name__contains': '筛选用例'},
                        {'level__in': ['0', '1']},
                        {'scenario_layer__in': ['0', '2']},
                        {'scenario_type__in': ['0', '3']},
                ):
                    queryset.filter.assert_any_call(**kwargs)
                queryset.filter.assert_any_call(Q(
                    scenario_tags__contains=[ApiCaseScenarioTagEnum.TEMPORARY_VALIDATION.value]
                ))

    def test_task_module_filters_preserve_fixed_scope_and_allow_unfixed_scope_search(self):
        for case_type, model_name, product_field in (
                (TestCaseTypeEnum.UI.value, 'UiCase', 'project_product'),
                (TestCaseTypeEnum.API.value, 'ApiCase', 'project_product'),
                (TestCaseTypeEnum.PYTEST.value, 'PytestCase', 'project_product__project_product'),
        ):
            for task_module, requested_module, expected_scope in (
                    (None, '100', [100, 101]),
                    (None, None, None),
                    (900, '100', [900, 901]),
                    (900, None, [900, 901]),
            ):
                with self.subTest(case_type=case_type, task_module=task_module,
                                  requested_module=requested_module):
                    task = SimpleNamespace(
                        execution_scope='manual', case_types=[case_type],
                        project_product_id=10, module_id=task_module,
                    )
                    queryset = MagicMock()
                    queryset.filter.return_value = queryset
                    params = {'type': str(case_type), 'task_id': '216', 'project_product_id': '99'}
                    if requested_module:
                        params['module_id'] = requested_module
                    target = 'src.apps.task_center.api.views.tasks_details'
                    with (
                        patch(f'{target}.Tasks.objects') as tasks,
                        patch(f'{target}.{model_name}.objects') as cases,
                        patch(f'{target}.ProductModuleService.module_scope_ids',
                              side_effect=lambda module_id: [module_id, module_id + 1]),
                        patch.object(TasksDetailsViews, '_candidate_queryset', return_value=[]),
                        patch.object(TasksDetailsViews, '_serialize_api_case_version_options',
                                     return_value=[]),
                    ):
                        tasks.filter.return_value.only.return_value.first.return_value = task
                        cases.all.return_value = queryset
                        cases.filter.return_value = queryset
                        response = TasksDetailsViews().get_type_case_name(
                            SimpleNamespace(query_params=params)
                        )
                    self.assertEqual(response.data['code'], 200)
                    queryset.filter.assert_any_call(**{product_field: 10})
                    if expected_scope:
                        queryset.filter.assert_any_call(module_id__in=expected_scope)
                    else:
                        self.assertFalse(any('module_id__in' in call.kwargs
                                             for call in queryset.filter.call_args_list))

    def test_candidate_queries_only_load_names_and_module_paths(self):
        for model in (ApiCase, UiCase, PytestCase):
            with self.subTest(model=model):
                queryset = TasksDetailsViews._candidate_queryset(model.objects.all())
                selected, _, _ = queryset.query.get_compiler('default').get_select()
                case_fields = {column[0].target.name for column in selected
                               if column[0].target.model is model}
                self.assertEqual(case_fields, {'id', 'name', 'module'})
                module_columns = [column[0] for column in selected
                                  if column[0].target.model is not model]
                self.assertEqual(len(module_columns), 9)
                self.assertEqual({column.target.name for column in module_columns},
                                 {'id', 'name', 'parent'})
