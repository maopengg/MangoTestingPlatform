# -*- coding: utf-8 -*-
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.customization import ObtainTestData
from src.services.ui.page_steps import PageSteps
from src.services.ui.test_page_steps import TestPageSteps


class PageStepsUrlPolicyTest(unittest.TestCase):

    @staticmethod
    def _page_steps(progress_mode: str, switch_step_open_url: bool):
        page_steps = PageSteps.__new__(PageSteps)
        page_steps.progress_mode = progress_mode
        page_steps.page_steps_model = SimpleNamespace(
            switch_step_open_url=switch_step_open_url,
        )
        return page_steps

    def test_case_uses_the_configured_switch(self):
        enabled = self._page_steps(PageSteps.PROGRESS_MODE_CASE, True)
        disabled = self._page_steps(PageSteps.PROGRESS_MODE_CASE, False)

        self.assertTrue(enabled._should_force_step_url())
        self.assertFalse(disabled._should_force_step_url())

    def test_page_step_debug_never_forces_the_configured_url(self):
        page_steps = self._page_steps(PageSteps.PROGRESS_MODE_PAGE_STEP_DEBUG, True)

        self.assertFalse(page_steps._should_force_step_url())

    @staticmethod
    def _page_steps_with_url(url: str):
        page_steps = PageSteps.__new__(PageSteps)
        page_steps.page_steps_model = SimpleNamespace(
            url=url,
            environment_config=SimpleNamespace(test_object_value='https://service-b.example.com/'),
        )
        page_steps.base_data = SimpleNamespace(test_data=ObtainTestData(), url=None)
        page_steps.test_object = ''
        return page_steps

    def test_step_url_uses_replaced_query_parameters(self):
        page_steps = self._page_steps_with_url(
            '/cooperation/detail?cooperationId=${{订单id}}&from=home',
        )
        page_steps.base_data.test_data.set_cache('订单id', '1161533936686334316')

        target_url = page_steps._resolve_step_url()

        self.assertEqual(
            target_url,
            'https://service-b.example.com/cooperation/detail'
            '?cooperationId=1161533936686334316&from=home',
        )
        self.assertEqual(page_steps.test_object, target_url)

    def test_step_target_uses_current_case_variable_mapping(self):
        page_steps = self._page_steps_with_url('/api/contracts')
        page_steps.page_steps_model.environment_config.test_object_value = ''
        page_steps.page_steps_model.environment_config.target_config = {
            'default': 'https://common.example.com',
            'selector': '租户id',
            'mapping': {'1002': 'https://tenant-b.example.com', '1003': 'https://tenant-c.example.com'},
        }
        page_steps.base_data.test_data.set_cache('租户id', '1002')
        self.assertEqual(page_steps._resolve_step_url(), 'https://tenant-b.example.com/api/contracts')
        page_steps.base_data.test_data.set_cache('租户id', '1003')
        self.assertEqual(page_steps._resolve_step_url(), 'https://tenant-c.example.com/api/contracts')

    def test_missing_target_selector_uses_default_address(self):
        page_steps = self._page_steps_with_url('/api/contracts?x=${{missing}}')
        page_steps.page_steps_model.environment_config.test_object_value = ''
        page_steps.page_steps_model.environment_config.target_config = {
            'default': 'https://common.example.com',
            'selector': '租户id', 'mapping': {'1002': 'https://tenant-b.example.com'},
        }
        self.assertEqual(page_steps._resolve_step_url(), 'https://common.example.com/api/contracts')

    def test_step_url_drops_query_when_cache_replacement_fails(self):
        page_steps = self._page_steps_with_url(
            '/cooperation/detail?cooperationId=${{订单id}}&from=home',
        )

        target_url = page_steps._resolve_step_url()

        self.assertEqual(target_url, 'https://service-b.example.com/cooperation/detail')
        self.assertEqual(page_steps.test_object, target_url)


class ElementCheckStatusTest(unittest.TestCase):

    @staticmethod
    def _service():
        return TestPageSteps(None, None)

    def test_risk_locator_takes_precedence(self):
        self.assertEqual(
            self._service()._validity_status([
                {'status': 'valid'},
                {'status': 'risk'},
            ]),
            'risk',
        )

    def test_unique_locator_is_valid(self):
        self.assertEqual(self._service()._validity_status([{'status': 'valid'}]), 'valid')


class PageStepDebugSessionTest(unittest.TestCase):

    def test_same_project_and_environment_reuse_debug_base_data(self):
        service = TestPageSteps(None, None)
        original_base_data = service._debug_base_data
        original_scope = service._debug_session_scope
        debug_base_data = SimpleNamespace()
        runtime = SimpleNamespace()
        data = SimpleNamespace(project_product=10, test_env=2)

        try:
            service._debug_session_scope = None
            with patch(
                    'src.services.ui.test_page_steps.AutomationSessionManager.create_base_data',
                    return_value=debug_base_data,
            ) as create_base_data, patch(
                    'src.services.ui.test_page_steps.AutomationSessionManager.web_runtime',
                    return_value=runtime,
            ):
                asyncio.run(service._use_debug_session(data))
                asyncio.run(service._use_debug_session(data))

            create_base_data.assert_called_once_with(2)
            self.assertIs(service.base_data, debug_base_data)
            self.assertIs(service._debug_base_data, debug_base_data)
        finally:
            service._debug_base_data = original_base_data
            service._debug_session_scope = original_scope
            service.base_data = original_base_data


if __name__ == '__main__':
    unittest.main()
