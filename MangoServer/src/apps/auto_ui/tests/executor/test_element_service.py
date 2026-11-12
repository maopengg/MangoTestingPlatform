from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.services.elements.element_service import PageElementService


class UiElementExecutorServiceTest(SimpleTestCase):
    @patch("src.apps.auto_ui.services.elements.element_service.PageElementCRUD.inside_post")
    @patch("src.apps.auto_ui.services.elements.element_service.PageElement.objects.filter")
    @patch("src.apps.auto_ui.services.elements.element_service.Page.objects.select_for_update")
    @patch("src.apps.auto_ui.services.elements.element_service.transaction.atomic", side_effect=nullcontext)
    def test_description_only_element_can_be_created(
            self, _atomic, select_page, filter_elements, inside_post):
        select_page.return_value.get.return_value = SimpleNamespace(id=6)
        filter_elements.return_value.order_by.return_value.first.return_value = None
        inside_post.return_value = {'id': 20, 'name': '提交按钮'}

        result = PageElementService.create_element(
            page_id=6,
            name=' 提交按钮 ',
            category=' 弹窗 ',
            user_id=4,
            prompt='确认弹窗底部右侧的提交按钮',
        )

        self.assertEqual(result['element_id'], 20)
        self.assertEqual(result['action'], 'create')
        payload = inside_post.call_args.args[0]
        self.assertIsNone(payload['loc'])
        self.assertEqual(payload['name'], '提交按钮')
        self.assertEqual(payload['category'], '弹窗')

    @patch("src.apps.auto_ui.services.elements.element_service.PageElementCRUD.inside_post")
    @patch("src.apps.auto_ui.services.elements.element_service.PageElement.objects.filter")
    @patch("src.apps.auto_ui.services.elements.element_service.Page.objects.select_for_update")
    @patch("src.apps.auto_ui.services.elements.element_service.transaction.atomic", side_effect=nullcontext)
    def test_structured_description_only_element_can_be_created(
            self, _atomic, select_page, filter_elements, inside_post):
        select_page.return_value.get.return_value = SimpleNamespace(id=6)
        filter_elements.return_value.order_by.return_value.first.return_value = None
        inside_post.return_value = {'id': 21, 'name': '提交按钮'}

        result = PageElementService.create_element(
            page_id=6,
            name='提交按钮',
            category='弹窗',
            user_id=4,
            location_description='删除确认弹窗底部，附近有“删除后无法恢复”',
            surrounding_text='列表操作列',
        )

        self.assertEqual(result['element_id'], 21)
        payload = inside_post.call_args.args[0]
        self.assertEqual(payload['location_description'], '删除确认弹窗底部，附近有“删除后无法恢复”')
        self.assertEqual(payload['surrounding_text'], '列表操作列')

    def test_element_without_locator_or_description_is_rejected(self):
        with self.assertRaisesRegex(AutoUiError, '至少填写一项'):
            PageElementService.create_element(
                page_id=6,
                name='提交按钮',
                category='弹窗',
                user_id=4,
            )

    @patch("src.apps.auto_ui.services.elements.element_service.PageElementCRUD.inside_put")
    @patch("src.apps.auto_ui.services.elements.element_service.PageElement.objects.filter")
    @patch("src.apps.auto_ui.services.elements.element_service.Page.objects.select_for_update")
    @patch("src.apps.auto_ui.services.elements.element_service.transaction.atomic", side_effect=nullcontext)
    def test_duplicate_element_identity_is_updated(
            self, _atomic, select_page, filter_elements, inside_put):
        select_page.return_value.get.return_value = SimpleNamespace(id=6)
        filter_elements.return_value.order_by.return_value.first.return_value = SimpleNamespace(id=19)
        inside_put.return_value = {'id': 19, 'name': '提交按钮'}

        result = PageElementService.create_element(
            page_id=6,
            name='提交按钮',
            category='弹窗',
            user_id=4,
            prompt='确认弹窗底部右侧的提交按钮',
        )

        self.assertEqual(result['element_id'], 19)
        self.assertEqual(result['action'], 'update')
        inside_put.assert_called_once()

    @patch("src.apps.auto_ui.services.elements.element_service.PageElement.objects.filter")
    def test_element_identity_prefers_current_exact_match(self, filter_elements):
        queryset = MagicMock()
        filter_elements.return_value = queryset
        queryset.count.return_value = 2
        current = SimpleNamespace(
            id=15,
            page_id=6,
            name="输入框",
            category="搜索区域",
        )
        queryset.filter.return_value.first.return_value = current

        result = PageElementService.resolve_element_identity(
            page_id=6,
            name=" 输入框 ",
            category=" 搜索区域 ",
            current_id=15,
        )

        filter_elements.assert_called_once_with(
            page_id=6,
            name="输入框",
            category="搜索区域",
        )
        self.assertTrue(result["exists"])
        self.assertEqual(result["action"], "update")
        self.assertEqual(result["match_count"], 2)
        self.assertEqual(result["element"]["id"], 15)
        self.assertTrue(result["element"]["is_current"])
        queryset.order_by.assert_not_called()

    @patch("src.apps.auto_ui.services.elements.element_service.PageElement.objects.filter")
    def test_element_identity_returns_create_when_no_exact_match(self, filter_elements):
        queryset = MagicMock()
        filter_elements.return_value = queryset
        queryset.count.return_value = 0
        queryset.order_by.return_value.first.return_value = None

        result = PageElementService.resolve_element_identity(
            page_id=6,
            name="新输入框",
            category="搜索区域",
        )

        self.assertFalse(result["exists"])
        self.assertEqual(result["action"], "create")
        self.assertIsNone(result["element"])

    @patch(
        "src.apps.auto_ui.services.elements.element_service.TestCase"
    )
    @patch.object(
        PageElementService,
        "_workspace_actuator_username",
        return_value="open",
    )
    @patch.object(
        PageElementService,
        "_selected_env",
        return_value=1,
    )
    @patch(
        "src.apps.auto_ui.services.elements.element_service.PageElement.objects.filter"
    )
    @patch(
        "src.apps.auto_ui.services.elements.element_service.uuid.uuid4",
        return_value="check-mango-mock",
    )
    def test_element_check_uses_live_workspace_executor(
            self,
            uuid4,
            filter_elements,
            selected_env,
            workspace_executor,
            test_case,
    ):
        filter_elements.return_value = SimpleNamespace(exists=lambda: True)
        test_case.return_value.check_element.return_value = object()

        result = PageElementService.check_element(
            element_id=15,
            user_id=4,
            username="maopeng",
            test_env_id=1,
            workspace_id="workspace-15",
        )

        test_case.assert_called_once_with(
            4,
            "maopeng",
            1,
            is_send=True,
            actuator_username="open",
        )
        test_case.return_value.check_element.assert_called_once_with(
            15,
            "check-mango-mock",
            "workspace-15",
            "normal",
        )
        self.assertEqual(result["actuator_username"], "open")
        self.assertEqual(result["check_id"], "check-mango-mock")
        self.assertEqual(result["check_mode"], "normal")

    @patch("src.apps.auto_ui.services.elements.element_service.TestCase")
    @patch.object(PageElementService, "_workspace_actuator_username", return_value=None)
    @patch.object(PageElementService, "_selected_env", return_value=1)
    @patch("src.apps.auto_ui.services.elements.element_service.PageElement.objects.filter")
    def test_deep_element_check_is_forwarded_to_executor(
            self,
            filter_elements,
            selected_env,
            workspace_executor,
            test_case,
    ):
        filter_elements.return_value = SimpleNamespace(exists=lambda: True)

        result = PageElementService.check_element(
            element_id=15,
            user_id=4,
            username="maopeng",
            test_env_id=1,
            check_mode="deep",
        )

        test_case.return_value.check_element.assert_called_once_with(
            15,
            result["check_id"],
            None,
            "deep",
        )
        self.assertEqual(result["check_mode"], "deep")

    @patch("src.apps.auto_ui.services.elements.element_service.TestCase")
    @patch.object(PageElementService, "_workspace_actuator_username", return_value=None)
    @patch.object(PageElementService, "_selected_env", return_value=1)
    @patch("src.apps.auto_ui.services.elements.element_service.PageElement.objects.filter")
    def test_deep_element_check_forwards_temporary_variables(
            self,
            filter_elements,
            selected_env,
            workspace_executor,
            test_case,
    ):
        filter_elements.return_value = SimpleNamespace(exists=lambda: True)

        result = PageElementService.check_element(
            element_id=15,
            user_id=4,
            username="maopeng",
            test_env_id=1,
            check_mode="deep",
            runtime_variables={"订单id": "C-100"},
        )

        test_case.return_value.check_element.assert_called_once_with(
            15,
            result["check_id"],
            None,
            "deep",
            runtime_variables={"订单id": "C-100"},
        )

    @patch(
        "src.apps.auto_ui.services.elements.element_service.TestCase"
    )
    @patch(
        "src.apps.auto_ui.services.elements.element_service.PageElement.objects.filter"
    )
    def test_missing_element_is_rejected_before_executor_dispatch(
            self,
            filter_elements,
            test_case,
    ):
        filter_elements.return_value = SimpleNamespace(exists=lambda: False)

        with self.assertRaisesRegex(AutoUiError, "元素不存在"):
            PageElementService.check_element(
                element_id=999,
                user_id=4,
                username="maopeng",
                test_env_id=1,
            )

        test_case.assert_not_called()

    @patch(
        "src.apps.auto_ui.services.live_stream.workspace_service.LiveWorkspaceService.get_workspace"
    )
    def test_element_check_rejects_workspace_owned_by_another_user(
            self,
            get_workspace,
    ):
        get_workspace.return_value = SimpleNamespace(
            username="other-user",
            executor_username="open",
        )

        with self.assertRaises(AutoUiError):
            PageElementService._workspace_actuator_username(
                "workspace-other",
                "maopeng",
            )
