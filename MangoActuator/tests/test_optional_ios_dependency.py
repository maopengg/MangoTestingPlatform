import subprocess
import sys
import textwrap
import unittest
from types import SimpleNamespace
from unittest import mock

from src.services.runtime.session.close_utils import RuntimeCloseUtils


class OptionalIOSDependencyTests(unittest.TestCase):
    def test_web_executor_imports_without_ios_module_or_appium(self):
        script = textwrap.dedent(
            """
            import asyncio
            import importlib.abc
            import sys

            class BlockIOSImports(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if fullname == 'src.services.runtime.session.ios_session' or fullname.startswith('appium'):
                        raise ModuleNotFoundError(fullname)
                    return None

            sys.meta_path.insert(0, BlockIOSImports())

            from src.services.runtime.session import AutomationSessionManager, CaseRuntimeSession

            async def verify_friendly_ios_error():
                try:
                    await AutomationSessionManager.acquire_ios(None, '', {}, 'test-owner')
                except RuntimeError as error:
                    assert str(error) == '当前执行器未安装 iOS 自动化组件，请选择 iOS 执行器后再试'
                else:
                    raise AssertionError('缺少 iOS 组件时应返回明确提示')

            asyncio.run(verify_friendly_ios_error())
            assert CaseRuntimeSession is not None
            """
        )

        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=".",
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)


class WebResourceCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_web_session_owner_does_not_trigger_mobile_lease_imports(self):
        base_data = SimpleNamespace(
            page=None,
            context=None,
            database_result_adapter=None,
            _runtime_session_id="web-session",
            setup=mock.Mock(),
        )
        original_import = __import__

        def reject_mobile_session_imports(name, *args, **kwargs):
            if name in {
                "src.services.runtime.session.android_session",
                "src.services.runtime.session.ios_session",
            }:
                raise AssertionError(f"Web 资源关闭不应导入移动端会话：{name}")
            return original_import(name, *args, **kwargs)

        with (
            mock.patch(
                "src.services.runtime.session.close_utils.WebContextRegistry.unregister_base"
            ),
            mock.patch("builtins.__import__", side_effect=reject_mobile_session_imports),
        ):
            await RuntimeCloseUtils.close_page_context(base_data, "Web用例")

        base_data.setup.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
