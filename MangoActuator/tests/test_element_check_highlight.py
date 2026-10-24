import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from mangoautomation.enums import ElementOperationEnum
from mangoautomation.models import (
    ElementListModel,
    ElementListResultModel,
    ElementModel,
    ElementResultModel,
)
from mangotools.enums import StatusEnum

from src.services.ui.test_page_steps import TestPageSteps


class ElementCheckHighlightTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _service():
        service = object.__new__(TestPageSteps)
        service.base_data = SimpleNamespace(
            test_data=SimpleNamespace(replace=lambda value: value),
        )
        return service

    async def test_first_matched_locator_is_highlighted(self):
        locator = SimpleNamespace(
            is_visible=AsyncMock(return_value=True),
            is_enabled=AsyncMock(return_value=True),
            is_editable=AsyncMock(return_value=True),
            bounding_box=AsyncMock(return_value={'x': 1, 'y': 2, 'width': 3, 'height': 4}),
            evaluate_all=AsyncMock(),
        )
        element_device = SimpleNamespace(
            web_find_element=AsyncMock(return_value=(locator, 1, '提交')),
        )
        element_model = SimpleNamespace(
            name='提交',
            type=0,
            elements=[SimpleNamespace(exp=2, loc='get_by_text("提交")', sub=None, is_iframe=0)],
        )

        rows = await self._service()._inspect_locator_groups(element_device, element_model)

        locator.evaluate_all.assert_awaited_once()
        self.assertEqual(
            locator.evaluate_all.await_args.args[1]['label'],
            'get_by_text("提交")',
        )
        self.assertTrue(rows[0]['highlighted'])
        self.assertEqual(rows[0]['highlighted_count'], 1)

    async def test_input_deep_check_rejects_invisible_locator_and_keeps_visible_editable_group(self):
        invisible = SimpleNamespace(
            is_visible=AsyncMock(return_value=False),
            is_enabled=AsyncMock(return_value=True),
            is_editable=AsyncMock(return_value=True),
            bounding_box=AsyncMock(return_value=None),
            evaluate_all=AsyncMock(),
        )
        visible = SimpleNamespace(
            is_visible=AsyncMock(return_value=True),
            is_enabled=AsyncMock(return_value=True),
            is_editable=AsyncMock(return_value=True),
            bounding_box=AsyncMock(return_value={'x': 1, 'y': 2, 'width': 3, 'height': 4}),
            evaluate_all=AsyncMock(),
        )
        element_device = SimpleNamespace(
            web_find_element=AsyncMock(side_effect=[
                (invisible, 1, '相同文本'),
                (visible, 1, '相同文本'),
            ]),
        )
        element_model = ElementModel(
            id=15,
            element_id=15,
            type=ElementOperationEnum.OPE,
            name='输入框',
            sleep=None,
            ope_key='w_input',
            elements=[
                ElementListModel(exp=2, loc='locator("#kw")', slot=1),
                ElementListModel(exp=0, loc='//textarea[@id="chat-textarea"]', slot=2),
            ],
        )

        rows = await self._service()._inspect_locator_groups(element_device, element_model)

        self.assertEqual(rows[0]['status'], 'invalid')
        self.assertIn('要求元素可见', rows[0]['error_message'])
        self.assertEqual(rows[1]['status'], 'valid')

    async def test_deep_check_heals_failed_group_and_requires_every_group(self):
        service = self._service()
        service._locator_items_same_target = AsyncMock(return_value=True)
        service.base_data.page = SimpleNamespace(
            url='https://example.test',
            title=AsyncMock(return_value='示例页面'),
            viewport_size={'width': 1440, 'height': 900},
        )
        element_model = ElementModel(
            id=15,
            element_id=15,
            type=ElementOperationEnum.OPE,
            name='提交',
            sleep=None,
            ope_key='w_click',
            elements=[
                ElementListModel(exp=2, loc='get_by_text("提交")'),
                ElementListModel(exp=0, loc='//button[@name="missing"]'),
            ],
        )
        healed_result = ElementResultModel(
            id=15,
            name='提交',
            sleep=None,
            type=ElementOperationEnum.OPE.value,
            status=1,
            elements=[
                ElementListResultModel(
                    exp=2,
                    loc='get_by_role("button", name="提交")',
                    is_iframe=0,
                    ele_quantity=1,
                    element_text='提交',
                    visible=True,
                    enabled=True,
                )
            ],
            locator_engine={
                'used_source': 'ai_accessibility',
                'used_ai': True,
                'temporary_heal_used': True,
            },
        )
        element_device = SimpleNamespace(element_main=AsyncMock(return_value=healed_result))
        groups = [
            {
                'group': 1,
                'exp': 2,
                'loc': 'get_by_text("提交")',
                'sub': None,
                'is_iframe': 0,
                'count': 1,
                'element_text': '提交',
                'status': 'valid',
                'duration_ms': 5,
            },
            {
                'group': 2,
                'exp': 0,
                'loc': '//button[@name="missing"]',
                'sub': None,
                'is_iframe': 0,
                'count': 0,
                'status': 'invalid',
                'error_message': '未匹配到元素',
                'duration_ms': 6,
            },
        ]

        result = await service._deep_check_locator_groups(element_device, element_model, groups)

        self.assertEqual(result.status, 1)
        self.assertEqual([item['status'] for item in groups], ['valid', 'healed'])
        self.assertEqual(result.locator_engine['passed_group_count'], 2)
        self.assertEqual(result.locator_engine['healed_groups'], [2])
        probe_model = element_device.element_main.await_args.args[0]
        self.assertEqual(probe_model.ope_key, 'w_get_text')
        self.assertEqual(len(probe_model.elements), 1)

    async def test_deep_check_uses_visible_actionable_group_as_anchor(self):
        service = self._service()
        service.base_data.page = SimpleNamespace(
            url='https://www.baidu.com/',
            title=AsyncMock(return_value='百度一下，你就知道'),
            viewport_size={'width': 1440, 'height': 900},
        )
        element_model = ElementModel(
            id=15,
            element_id=15,
            type=ElementOperationEnum.OPE,
            name='输入框',
            sleep=None,
            ope_key='w_input',
            elements=[
                ElementListModel(exp=2, loc='locator("#kw")', slot=1),
                ElementListModel(exp=0, loc='//textarea[@id="chat-textarea"]', slot=2),
                ElementListModel(
                    exp=9,
                    loc='[data-mango-deep-check-empty-slot="3"]',
                    slot=3,
                    is_placeholder=True,
                ),
            ],
        )
        groups = [
            {
                'group': 1, 'exp': 2, 'loc': 'locator("#kw")', 'sub': None,
                'is_iframe': 0, 'count': 1, 'status': 'invalid',
                'visible': False, 'enabled': True, 'editable': True,
                'error_message': '当前操作要求元素可见',
            },
            {
                'group': 2, 'exp': 0, 'loc': '//textarea[@id="chat-textarea"]',
                'sub': None, 'is_iframe': 0, 'count': 1, 'status': 'valid',
                'visible': True, 'enabled': True, 'editable': True,
                'bounding_box': {'x': 337.5, 'y': 226.5, 'width': 770, 'height': 28},
            },
            {
                'group': 3, 'exp': 9,
                'loc': '[data-mango-deep-check-empty-slot="3"]', 'sub': None,
                'is_iframe': 0, 'is_placeholder': True, 'count': 0, 'status': 'empty',
                'error_message': '该定位组未配置，将尝试自动补全',
            },
        ]
        suggestions = [
            {'exp': 2, 'loc': 'get_by_role("textbox")'},
            {'exp': 9, 'loc': 'textarea[name="word"]'},
        ]
        service._anchor_locator_suggestions = AsyncMock(return_value=suggestions)

        async def runtime_for_locator(_device, _model, locator_item):
            return ElementListResultModel(
                exp=locator_item.exp,
                loc=locator_item.loc,
                sub=locator_item.sub,
                is_iframe=0,
                ele_quantity=1,
                element_text='伊朗谈重开霍尔木兹海峡的前提',
                visible=True,
                enabled=True,
                editable=True,
                bounding_box={'x': 337.5, 'y': 226.5, 'width': 770, 'height': 28},
            )

        async def same_target(_device, anchor_item, candidate_item):
            self.assertEqual(anchor_item.loc, '//textarea[@id="chat-textarea"]')
            return candidate_item.loc != 'locator("#kw")'

        service._runtime_element_for_locator = AsyncMock(side_effect=runtime_for_locator)
        service._locator_items_same_target = AsyncMock(side_effect=same_target)
        element_device = SimpleNamespace(element_main=AsyncMock())

        result = await service._deep_check_locator_groups(
            element_device, element_model, groups,
        )

        self.assertEqual(result.status, 1)
        self.assertEqual([item['status'] for item in groups], ['healed', 'valid', 'healed'])
        self.assertEqual(result.locator_engine['healed_groups'], [1, 3])
        self.assertEqual(
            [item['slot'] for item in result.locator_engine['locator_updates']],
            [1, 3],
        )
        element_device.element_main.assert_not_awaited()

    async def test_deep_check_promotes_configured_locator_when_retry_matches_late(self):
        service = self._service()
        service.base_data.page = SimpleNamespace(
            url='https://example.test',
            title=AsyncMock(return_value='异步页面'),
            viewport_size={'width': 1440, 'height': 900},
        )
        service._anchor_locator_suggestions = AsyncMock(return_value=[])
        configured_locator = 'get_by_text("异步选项", exact=True).nth(1)'
        element_model = ElementModel(
            id=15,
            element_id=15,
            type=ElementOperationEnum.OPE,
            name='异步选项',
            sleep=None,
            ope_key='w_get_text',
            elements=[ElementListModel(exp=2, loc=configured_locator, slot=1)],
        )
        late_success = ElementResultModel(
            id=15,
            name='异步选项',
            sleep=None,
            type=ElementOperationEnum.OPE.value,
            status=StatusEnum.SUCCESS.value,
            elements=[ElementListResultModel(
                exp=2,
                loc=configured_locator,
                is_iframe=0,
                ele_quantity=1,
                element_text='异步选项',
                visible=True,
                enabled=True,
                locate_duration_ms=5000,
            )],
            locator_engine={
                'used_source': 'fixed_locator',
                'used_ai': False,
                'temporary_heal_used': False,
            },
        )
        element_device = SimpleNamespace(element_main=AsyncMock(return_value=late_success))
        groups = [{
            'group': 1,
            'exp': 2,
            'loc': configured_locator,
            'sub': None,
            'is_iframe': 0,
            'count': 0,
            'status': 'invalid',
            'error_message': '未匹配到元素',
            'duration_ms': 20,
        }]

        result = await service._deep_check_locator_groups(
            element_device, element_model, groups,
        )

        self.assertEqual(result.status, StatusEnum.SUCCESS.value)
        self.assertEqual(groups[0]['status'], 'valid')
        self.assertEqual(groups[0]['count'], 1)
        self.assertTrue(groups[0]['late_match'])
        self.assertFalse(groups[0]['healed'])
        self.assertEqual(result.locator_engine['failed_groups'], [])
        self.assertEqual(result.locator_engine['locator_updates'], [])

    async def test_deep_check_fills_empty_group_with_same_target_locator(self):
        service = self._service()
        service._locator_items_same_target = AsyncMock(return_value=True)
        service.base_data.page = SimpleNamespace(
            url='https://example.test',
            title=AsyncMock(return_value='示例页面'),
            viewport_size={'width': 1440, 'height': 900},
        )
        element_model = ElementModel(
            id=15,
            element_id=15,
            type=ElementOperationEnum.OPE,
            name='提交',
            sleep=None,
            ope_key='w_click',
            elements=[
                ElementListModel(exp=2, loc='get_by_text("提交")', slot=1),
                ElementListModel(
                    exp=9,
                    loc='[data-mango-deep-check-empty-slot="2"]',
                    slot=2,
                    is_placeholder=True,
                ),
            ],
        )
        healed_result = ElementResultModel(
            id=15,
            name='提交',
            sleep=None,
            type=ElementOperationEnum.OPE.value,
            status=1,
            elements=[ElementListResultModel(
                exp=0,
                loc='//button[normalize-space()="提交"]',
                is_iframe=0,
                ele_quantity=1,
                element_text='提交',
            )],
            locator_engine={
                'used_source': 'ai_accessibility',
                'used_ai': True,
                'temporary_heal_used': True,
            },
        )
        element_device = SimpleNamespace(element_main=AsyncMock(return_value=healed_result))
        groups = [
            {
                'group': 1, 'exp': 2, 'loc': 'get_by_text("提交")', 'sub': None,
                'is_iframe': 0, 'count': 1, 'status': 'valid', 'duration_ms': 5,
            },
            {
                'group': 2, 'exp': 9, 'loc': '[data-mango-deep-check-empty-slot="2"]',
                'sub': None, 'is_iframe': 0, 'is_placeholder': True, 'count': 0,
                'status': 'empty', 'error_message': '该定位组未配置，将尝试自动补全',
                'duration_ms': 0,
            },
        ]

        result = await service._deep_check_locator_groups(element_device, element_model, groups)

        self.assertEqual(result.status, 1)
        self.assertEqual(groups[1]['status'], 'healed')
        self.assertTrue(groups[1]['same_target'])
        self.assertEqual(groups[1]['loc'], '//button[normalize-space()="提交"]')
        self.assertFalse(groups[1]['is_placeholder'])
        self.assertEqual(result.locator_engine['locator_updates'][0]['slot'], 2)
        self.assertEqual(
            result.locator_engine['locator_updates'][0]['loc'],
            '//button[normalize-space()="提交"]',
        )

    async def test_deep_check_fails_when_one_group_cannot_be_healed(self):
        service = self._service()
        service.base_data.page = SimpleNamespace(
            url='https://example.test',
            title=AsyncMock(return_value='示例页面'),
            viewport_size={'width': 1440, 'height': 900},
        )
        element_model = ElementModel(
            id=15,
            element_id=15,
            type=ElementOperationEnum.OPE,
            name='提交',
            sleep=None,
            ope_key='w_click',
            elements=[ElementListModel(exp=0, loc='//button[@name="missing"]')],
        )
        failed_result = ElementResultModel(
            id=15,
            name='提交',
            sleep=None,
            type=ElementOperationEnum.OPE.value,
            status=0,
            error_message='候选耗尽',
        )
        element_device = SimpleNamespace(element_main=AsyncMock(return_value=failed_result))
        groups = [{
            'group': 1,
            'exp': 0,
            'loc': '//button[@name="missing"]',
            'sub': None,
            'is_iframe': 0,
            'count': 0,
            'status': 'invalid',
            'error_message': '未匹配到元素',
            'duration_ms': 6,
        }]

        result = await service._deep_check_locator_groups(element_device, element_model, groups)

        self.assertEqual(result.status, 0)
        self.assertEqual(result.locator_engine['failed_groups'], [1])
        self.assertIn('第1组', result.error_message)

    async def test_deep_check_screenshot_rehighlights_final_target_and_keeps_overlay(self):
        service = self._service()
        page = SimpleNamespace(
            frames=[SimpleNamespace()],
            is_closed=lambda: False,
            screenshot=AsyncMock(),
        )
        service.base_data.page = page
        locator = SimpleNamespace(
            first=SimpleNamespace(scroll_into_view_if_needed=AsyncMock()),
        )
        element_device = SimpleNamespace(
            web_find_element=AsyncMock(return_value=(locator, 1, '提交')),
        )
        element_model = SimpleNamespace(id=15, name='提交', type=0)
        selected_result = ElementResultModel(
            id=15,
            name='提交',
            type=0,
            status=1,
            locator_engine={},
        )
        groups = [
            {
                'group': 1, 'exp': 2, 'loc': 'get_by_text("提交")', 'sub': None,
                'is_iframe': 0, 'count': 1, 'status': 'valid', 'visible': True,
            },
            {
                'group': 2, 'exp': 0, 'loc': '//button[text()="提交"]', 'sub': None,
                'is_iframe': 0, 'count': 1, 'status': 'healed', 'visible': True,
            },
        ]

        with patch(
            'src.services.ui.test_page_steps.WebElementHighlighter.clear_async',
            new=AsyncMock(return_value=1),
        ) as clear_highlight, patch(
            'src.services.ui.test_page_steps.WebElementHighlighter.highlight_async',
            new=AsyncMock(return_value=1),
        ) as highlight, patch(
            'src.services.ui.test_page_steps.project_dir.screenshot',
            return_value='/tmp',
        ):
            await service._capture_deep_check_screenshot(
                element_device, element_model, groups, selected_result,
            )

        self.assertTrue(selected_result.picture_name.startswith('深度检测截图-提交-'))
        self.assertTrue(selected_result.picture_path.endswith('.jpg'))
        self.assertTrue(selected_result.locator_engine['screenshot_captured'])
        self.assertEqual(selected_result.locator_engine['screenshot_groups'], [1, 2])
        self.assertEqual(highlight.await_args.args[1], '提交 · 定位组 1/2')
        self.assertEqual(clear_highlight.await_count, 1)
        locator.first.scroll_into_view_if_needed.assert_awaited_once_with(timeout=3000)
        page.screenshot.assert_awaited_once()
        self.assertFalse(page.screenshot.await_args.kwargs['full_page'])
        self.assertEqual(page.screenshot.await_args.kwargs['timeout'], 5000)
        self.assertEqual(page.screenshot.await_args.kwargs['animations'], 'disabled')

    async def test_deep_check_screenshot_failure_does_not_change_check_status(self):
        service = self._service()
        page = SimpleNamespace(
            frames=[],
            is_closed=lambda: False,
            screenshot=AsyncMock(side_effect=RuntimeError('磁盘不可写')),
        )
        service.base_data.page = page
        element_device = SimpleNamespace(
            web_find_element=AsyncMock(return_value=(SimpleNamespace(
                first=SimpleNamespace(scroll_into_view_if_needed=AsyncMock()),
            ), 1, '提交')),
        )
        selected_result = ElementResultModel(id=15, name='提交', type=0, status=1)

        with patch(
            'src.services.ui.test_page_steps.WebElementHighlighter.clear_async',
            new=AsyncMock(return_value=0),
        ), patch(
            'src.services.ui.test_page_steps.WebElementHighlighter.highlight_async',
            new=AsyncMock(return_value=1),
        ), patch(
            'src.services.ui.test_page_steps.project_dir.screenshot',
            return_value='/tmp',
        ):
            await service._capture_deep_check_screenshot(
                element_device,
                SimpleNamespace(id=15, name='提交', type=0),
                [{
                    'group': 1, 'exp': 2, 'loc': 'get_by_text("提交")', 'sub': None,
                    'is_iframe': 0, 'count': 1, 'status': 'valid', 'visible': True,
                }],
                selected_result,
            )

        self.assertEqual(selected_result.status, 1)
        self.assertFalse(selected_result.locator_engine['screenshot_captured'])
        self.assertIn('磁盘不可写', selected_result.locator_engine['screenshot_error'])
        page.screenshot.assert_awaited_once()

    async def test_deep_check_screenshot_retries_timeout_and_succeeds(self):
        service = self._service()
        page = SimpleNamespace(
            frames=[SimpleNamespace()],
            is_closed=lambda: False,
            screenshot=AsyncMock(side_effect=[TimeoutError('Page.screenshot timeout'), None]),
        )
        service.base_data.page = page
        locator = SimpleNamespace(
            first=SimpleNamespace(scroll_into_view_if_needed=AsyncMock()),
        )
        element_device = SimpleNamespace(
            web_find_element=AsyncMock(return_value=(locator, 1, '删除')),
        )
        selected_result = ElementResultModel(id=16, name='删除', type=0, status=1)

        with patch(
            'src.services.ui.test_page_steps.WebElementHighlighter.clear_async',
            new=AsyncMock(return_value=0),
        ), patch(
            'src.services.ui.test_page_steps.WebElementHighlighter.highlight_async',
            new=AsyncMock(return_value=1),
        ), patch(
            'src.services.ui.test_page_steps.project_dir.screenshot',
            return_value='/tmp',
        ), patch(
            'src.services.ui.test_page_steps.asyncio.sleep',
            new=AsyncMock(),
        ):
            await service._capture_deep_check_screenshot(
                element_device,
                SimpleNamespace(id=16, name='删除', type=0),
                [{
                    'group': 1, 'exp': 2, 'loc': 'get_by_text("删除")', 'sub': None,
                    'is_iframe': 0, 'count': 1, 'status': 'valid', 'visible': True,
                }],
                selected_result,
            )

        self.assertEqual(page.screenshot.await_count, 2)
        self.assertTrue(selected_result.locator_engine['screenshot_captured'])
        self.assertNotIn('screenshot_error', selected_result.locator_engine)

    def test_deep_check_screenshot_timeout_message_is_simplified(self):
        message = TestPageSteps._deep_check_screenshot_error_text(
            TimeoutError(
                'Page.screenshot: Timeout 5000ms exceeded.\n'
                'Call log:\n- taking page screenshot\n- waiting for fonts to load'
            )
        )

        self.assertEqual(
            message,
            '页面截图连续2次超时（单次上限5秒），定位结果不受影响',
        )
        self.assertNotIn('Call log', message)


if __name__ == '__main__':
    unittest.main()
