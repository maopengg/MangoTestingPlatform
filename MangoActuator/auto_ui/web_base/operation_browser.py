# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏

from auto_ui.web_base.playwright_base import PlaywrightBase


class PlaywrightOperationBrowser(PlaywrightBase):
    """浏览器操作类"""

    async def wait_for_timeout(self, sleep: int):
        await self.page.wait_for_timeout(sleep)

    async def goto(self, url: str):
        """打开url"""
        await self.page.goto(url, timeout=50000)

    async def screenshot(self, path: str, full_page=True):
        """整个页面截图"""
        await self.page.screenshot(path=path, full_page=full_page)

    async def ele_screenshot(self, selector: str, path: str):
        """元素截图"""
        await self.page.locator(selector).screenshot(path=path)

    async def alert(self):
        """设置弹窗不予处理"""
        self.page.on("dialog", lambda dialog: dialog.accept())

    async def download(self, save_path):
        # Start waiting for the download
        async with self.page.expect_download() as download_info:
            # Perform the action that initiates download
            await self.page.get_by_text("Download file").click()
        download = await download_info.value
        # Wait for the download process to complete
        print(await download.path())
        # Save downloaded file somewhere
        await download.save_as(save_path)
