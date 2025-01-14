# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-05-23 15:04
# @Author : 毛鹏
# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-04-24 10:43
# @Author : 毛鹏
import asyncio
import ctypes
import os
import string
import traceback
from typing import Optional
from urllib import parse

from mangokit import Mango
from playwright._impl._errors import Error
from playwright.async_api import async_playwright, Page, BrowserContext, Browser, Playwright
from playwright.async_api._generated import Request
from playwright.async_api._generated import Route

from src.enums.api_enum import ClientEnum, MethodEnum, ApiTypeEnum
from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import BrowserTypeEnum
from src.exceptions import *
from src.models.api_model import ApiInfoModel
from src.models.ui_model import EquipmentModel
from src.network.web_socket.socket_api_enum import ApiSocketEnum
from src.network.web_socket.websocket_client import WebSocketClient
from src.settings import settings
from src.tools import project_dir
from src.tools.decorator.error_handle import async_error_handle

"""
python -m uiautomator2 init
python -m weditor

"""


class NewBrowser:

    def __init__(self, web_config: EquipmentModel = None):
        self.lock = asyncio.Lock()
        self.config = web_config
        self.browser_path = ['chrome.exe', 'msedge.exe', 'firefox.exe', '苹果', '360se.exe']
        self.browser: Optional[None | Browser] = None
        self.playwright: Optional[None | Playwright] = None

    async def new_web_page(self, count=0) -> tuple[BrowserContext, Page]:
        if self.config is None:
            raise UiError(*ERROR_MSG_0042)
        if self.browser is None:
            async with self.lock:
                if self.browser is None:
                    self.browser = await self.new_browser()
                    await asyncio.sleep(1)
        try:
            context = await self.new_context()
            page = await self.new_page(context)
            return context, page
        except Exception as error:
            self.browser = None
            trace = traceback.format_exc()
            log.error(f'创建浏览器时报错：{trace}')
            Mango.s(self.new_web_page, error, trace, config=self.config.model_dump_json())
            if count >= 3:
                raise UiError(*ERROR_MSG_0057)
            else:
                await self.new_web_page(count=count + 1)

    async def new_browser(self) -> Browser:
        self.playwright = await async_playwright().start()
        if self.config.web_type \
                == BrowserTypeEnum.CHROMIUM.value or self.config.web_type == BrowserTypeEnum.EDGE.value:
            browser = self.playwright.chromium
        elif self.config.web_type == BrowserTypeEnum.FIREFOX.value:
            browser = self.playwright.firefox
        elif self.config.web_type == BrowserTypeEnum.WEBKIT.value:
            browser = self.playwright.webkit
        else:
            raise UiError(*ERROR_MSG_0008)
        try:
            self.config \
                .web_path = self.config \
                .web_path if self.config \
                .web_path else self.__search_path()

            if self.config.web_max:
                return await browser.launch(
                    headless=self.config.web_headers == StatusEnum.SUCCESS.value,
                    executable_path=self.config.web_path,
                    args=['--start-maximized']
                )
            else:
                return await browser.launch(
                    headless=self.config.web_headers == StatusEnum.SUCCESS.value,
                    executable_path=self.config.web_path
                )
        except Error:
            raise UiError(*ERROR_MSG_0009, value=(self.config.web_path,))

    async def new_context(self) -> BrowserContext:
        args_dict = {
            'no_viewport': True,
        }

        if self.config.web_recording:
            args_dict['record_video_dir'] = f'{project_dir.videos()}'

        if self.config.web_h5:
            del args_dict['no_viewport']
            args_dict.update(self.playwright.devices[self.config.web_h5])
        return await self.browser.new_context(**args_dict)

    async def new_page(self, context: BrowserContext) -> Page:
        try:
            page = await context.new_page()
            if self.config.is_header_intercept:
                await page.route("**/*", self.__intercept_request)  # 应用拦截函数到页面的所有请求
            return page
        except Error:
            raise UiError(*ERROR_MSG_0009, value=(self.config.web_path,))

    async def close(self):
        if self.config:
            if self.browser:
                await self.browser.close()

    def __search_path(self, ):
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if ctypes.windll.kernel32.GetDriveTypeW(drive) == 3:
                drives.append(drive)
        for i in drives:
            for root, dirs, files in os.walk(i):
                if self.browser_path[self.config.web_type] in files:
                    return os.path.join(root, self.browser_path[self.config.web_type])

        raise UiError(*ERROR_MSG_0055)

    async def __intercept_request(self, route: Route, request: Request):
        """
        定义拦截请求的函数
        会有性能问题，因为所有的接口都会被添加进来,需要优化取请求头的路径，或者是增加条件
        @param route:
        @param request:
        @return:
        """
        if self.config.host_list is None:
            await route.continue_()  # 继续请求，不做修改
            return
        if request.resource_type in ("document", "xhr", "fetch"):
            for host_dict in self.config.host_list:
                if host_dict.get('value') in request.url:
                    await self.__send_recording_api(request, host_dict.get('project_product_id'))
        await route.continue_()  # 继续请求，不做修改

    @classmethod
    @async_error_handle()
    async def __send_recording_api(cls, request: Request, project_product: int):
        parsed_url = parse.urlsplit(request.url)

        try:
            json_data = request.post_data_json
        except Error:
            json_data = None
        data = {key: value[0] for key, value in
                parse.parse_qs(request.post_data).items()} if json_data is None else None
        params = {key: value[0] for key, value in
                  parse.parse_qs(parsed_url.query).items()} if parsed_url.query else None
        api_info = ApiInfoModel(
            project_product=project_product,
            username=settings.USERNAME,
            type=ApiTypeEnum.batch.value,
            name=parsed_url.path,
            client=ClientEnum.WEB.value,
            url=parsed_url.path,
            method=MethodEnum.get_key(request.method),
            params=None if params == {} else params,
            data=None if data == {} else data,
            json_data=None if json_data == {} else json_data
        )
        await WebSocketClient().async_send(
            msg="发送录制接口",
            func_name=ApiSocketEnum.RECORDING_API.value,
            func_args=api_info
        )


async def test_main():
    r = NewBrowser()
    for i in range(10):
        context1, page1 = await r.new_web_page()
        await page1.goto('https://www.baidu.com/')


if __name__ == '__main__':
    asyncio.run(test_main())
