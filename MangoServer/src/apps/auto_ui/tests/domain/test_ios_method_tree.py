from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_ui.enums import DriveTypeEnum
from src.apps.auto_ui.services.page_steps.page_step_detail import PageStepDetailMutationService


class IOSMethodTreeTests(SimpleTestCase):
    METHOD_TREE = [
        {'value': 'web', 'children': [{'value': 'w_click'}]},
        {'value': 'android', 'children': [{'value': 'a_click'}]},
        {'value': 'ios', 'children': [{'value': 'i_click'}]},
        {'value': 'ass_web', 'children': [{'value': 'w_visible'}]},
        {'value': 'ass_android', 'children': [{'value': 'a_visible'}]},
        {'value': 'ass_ios', 'children': [{'value': 'i_assert_visible'}]},
        {'value': '文件断言', 'children': [{'value': 'file_exists'}]},
    ]

    @patch.object(PageStepDetailMutationService, 'cache_method_tree')
    def test_ios_page_only_returns_ios_operations(self, cache_method_tree):
        cache_method_tree.return_value = self.METHOD_TREE

        result = PageStepDetailMutationService.method_tree(
            'operation',
            DriveTypeEnum.IOS.value,
        )

        self.assertEqual(result, [{'value': 'i_click'}])

    @patch.object(PageStepDetailMutationService, 'cache_method_tree')
    def test_ios_assertions_include_ios_and_shared_assertions(self, cache_method_tree):
        cache_method_tree.return_value = self.METHOD_TREE

        result = PageStepDetailMutationService.method_tree(
            'assertion',
            DriveTypeEnum.IOS.value,
        )

        self.assertEqual(
            result,
            [
                {'value': 'i_assert_visible'},
                {'value': '文件断言', 'children': [{'value': 'file_exists'}]},
            ],
        )
