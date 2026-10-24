import asyncio
import importlib.util
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.ui.page_steps import PageSteps

HAS_APPIUM = importlib.util.find_spec("appium") is not None
if HAS_APPIUM:
    from src.services.runtime.session.ios_session import IOSDevicePool
else:
    IOSDevicePool = None


@unittest.skipUnless(HAS_APPIUM, "当前环境未安装 iOS/Appium 可选依赖")
class IOSDevicePoolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        IOSDevicePool._leases.clear()

    async def test_acquire_creates_and_binds_xcuitest_runtime(self):
        driver = SimpleNamespace(session_id='ios-session')
        runtime = SimpleNamespace(connect=MagicMock(return_value=driver))
        base_data = SimpleNamespace()

        def bind_ios(bound_runtime, bound_driver, bundle_id):
            base_data.ios = bound_driver
            base_data.bundle_id = bundle_id
            return base_data

        base_data.bind_ios = MagicMock(side_effect=bind_ios)
        capabilities = {
            'platformName': 'iOS',
            'appium:automationName': 'XCUITest',
            'appium:deviceName': 'iPhone 16',
            'appium:bundleId': 'com.example.demo',
        }

        with patch(
            'src.services.runtime.session.ios_session.IOSDriverFactory.create_runtime',
            return_value=runtime,
        ) as create_runtime:
            result = await IOSDevicePool.acquire(
                base_data,
                'http://127.0.0.1:4723',
                capabilities,
                owner='case-1',
            )

        create_runtime.assert_called_once_with('http://127.0.0.1:4723', capabilities)
        base_data.bind_ios.assert_called_once_with(runtime, driver, 'com.example.demo')
        self.assertIs(result, base_data.ios)
        self.assertEqual(base_data._ios_equipment, 'iPhone 16')

    async def test_acquire_failure_releases_new_device_lease(self):
        runtime = SimpleNamespace(connect=MagicMock(side_effect=RuntimeError('WDA failed')))
        base_data = SimpleNamespace(bind_ios=MagicMock())
        capabilities = {
            'appium:deviceName': 'iPhone 16',
            'appium:bundleId': 'com.example.demo',
        }

        with patch(
            'src.services.runtime.session.ios_session.IOSDriverFactory.create_runtime',
            return_value=runtime,
        ):
            with self.assertRaisesRegex(RuntimeError, 'WDA failed'):
                await IOSDevicePool.acquire(
                    base_data,
                    'http://127.0.0.1:4723',
                    capabilities,
                    owner='case-failed',
                )

        self.assertNotIn('iPhone 16', IOSDevicePool._leases)

    async def test_same_owner_concurrent_acquire_reuses_driver(self):
        driver = SimpleNamespace(session_id='ios-session')
        runtime = SimpleNamespace(driver=None)

        def connect():
            runtime.driver = driver
            return driver

        runtime.connect = MagicMock(side_effect=connect)
        capabilities = {
            'appium:deviceName': 'iPhone 16',
            'appium:bundleId': 'com.example.demo',
        }

        def make_base_data():
            base_data = SimpleNamespace()

            def bind_ios(bound_runtime, bound_driver, bundle_id):
                base_data.ios = bound_driver
                base_data.bundle_id = bundle_id

            base_data.bind_ios = MagicMock(side_effect=bind_ios)
            return base_data

        with patch(
            'src.services.runtime.session.ios_session.IOSDriverFactory.create_runtime',
            return_value=runtime,
        ):
            first, second = await asyncio.gather(
                IOSDevicePool.acquire(
                    make_base_data(),
                    'http://127.0.0.1:4723',
                    capabilities,
                    owner='case-1',
                ),
                IOSDevicePool.acquire(
                    make_base_data(),
                    'http://127.0.0.1:4723',
                    capabilities,
                    owner='case-1',
                ),
            )

        self.assertIs(first, driver)
        self.assertIs(second, driver)
        self.assertEqual(runtime.connect.call_count, 2)


class IOSPageStepsInitTests(unittest.IsolatedAsyncioTestCase):
    async def test_ios_init_builds_xcuitest_capabilities_from_executor_config(self):
        page_steps = PageSteps.__new__(PageSteps)
        page_steps.base_data = SimpleNamespace(bundle_id=None)
        page_steps.page_steps_model = SimpleNamespace(
            environment_config=SimpleNamespace(test_object_value='com.example.demo'),
        )
        page_steps.test_object = ''

        with (
            patch('src.services.ui.page_steps.SetConfig.get_ios_device_name', return_value='iPhone 16'),
            patch('src.services.ui.page_steps.SetConfig.get_ios_udid', return_value='simulator-udid'),
            patch('src.services.ui.page_steps.SetConfig.get_ios_platform_version', return_value='18.0'),
            patch('src.services.ui.page_steps.SetConfig.get_ios_xcode_org_id', return_value=''),
            patch('src.services.ui.page_steps.SetConfig.get_ios_wda_bundle_id', return_value=''),
            patch('src.services.ui.page_steps.SetConfig.get_ios_appium_url', return_value='http://127.0.0.1:4723'),
            patch(
                'src.services.ui.page_steps.AutomationSessionManager.acquire_ios',
                new_callable=AsyncMock,
            ) as acquire_ios,
        ):
            await page_steps.ios_init()

        self.assertEqual(page_steps.base_data.bundle_id, 'com.example.demo')
        self.assertEqual(page_steps.test_object, 'com.example.demo')
        capabilities = acquire_ios.await_args.args[2]
        self.assertEqual(capabilities['platformName'], 'iOS')
        self.assertEqual(capabilities['appium:automationName'], 'XCUITest')
        self.assertEqual(capabilities['appium:udid'], 'simulator-udid')
        self.assertEqual(capabilities['appium:bundleId'], 'com.example.demo')


if __name__ == '__main__':
    unittest.main()
