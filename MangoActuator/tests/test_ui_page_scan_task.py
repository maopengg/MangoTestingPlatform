import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.consumer.ui import UI


class UiPageScanTaskTest(unittest.IsolatedAsyncioTestCase):
    async def test_quick_scan_reuses_workspace_page_and_returns_result(self):
        page = MagicMock()
        page.is_closed.return_value = False
        runtime_state = SimpleNamespace(
            page=page,
            operation_lock=asyncio.Lock(),
            selected_scan_region=None,
            selected_scan_region_page=None,
        )
        inspector = MagicMock()
        inspector.scan = AsyncMock(return_value={"elements": [{"text": "提交"}], "scan_mode": "quick"})

        with (
            patch(
                "src.consumer.ui.UiRuntimeRegistry.wait_for",
                new=AsyncMock(return_value=runtime_state),
            ) as wait_for,
            patch(
                "src.consumer.ui.UiLiveWorkspaceManager.touch",
                new=AsyncMock(),
            ) as touch,
            patch("mangoautomation.uidrives.web.WebElementInspector", return_value=inspector),
        ):
            result = await UI.u_page_scan({
                "workspace_id": "workspace-1",
                "workspace_type": "element_workspace",
                "mode": "quick",
            })

        self.assertEqual(result["elements"][0]["text"], "提交")
        wait_for.assert_awaited_once_with("element_workspace", "workspace-1", timeout=15)
        inspector.scan.assert_awaited_once_with(page, "quick")
        touch.assert_awaited_once_with("workspace-1")

    async def test_region_scan_reuses_selected_region_and_can_run_repeatedly(self):
        page = MagicMock()
        page.is_closed.return_value = False
        region = {"tag": "section", "bounding_box": {"x": 1, "y": 2, "width": 3, "height": 4}}
        runtime_state = SimpleNamespace(
            page=page,
            operation_lock=asyncio.Lock(),
            selected_scan_region=region,
            selected_scan_region_page=page,
        )
        inspector = MagicMock()
        inspector.scan = AsyncMock(side_effect=[
            {"elements": [{"text": "第一次"}], "scan_mode": "region"},
            {"elements": [{"text": "第二次"}], "scan_mode": "region"},
        ])

        with (
            patch(
                "src.consumer.ui.UiRuntimeRegistry.wait_for",
                new=AsyncMock(return_value=runtime_state),
            ),
            patch("src.consumer.ui.UiLiveWorkspaceManager.touch", new=AsyncMock()),
            patch("mangoautomation.uidrives.web.WebElementInspector", return_value=inspector),
        ):
            first = await UI.u_page_scan({
                "workspace_id": "workspace-2",
                "workspace_type": "element_workspace",
                "mode": "region",
            })
            second = await UI.u_page_scan({
                "workspace_id": "workspace-2",
                "workspace_type": "element_workspace",
                "mode": "region",
            })

        self.assertEqual(first["elements"][0]["text"], "第一次")
        self.assertEqual(second["elements"][0]["text"], "第二次")
        self.assertEqual(inspector.scan.await_count, 2)
        inspector.scan.assert_awaited_with(page, "region", region=region)


if __name__ == "__main__":
    unittest.main()
