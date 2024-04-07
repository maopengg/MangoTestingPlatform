# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
import ctypes
import os
import string
from urllib import parse

from playwright._impl._api_types import Error
from playwright.async_api import async_playwright, Page, BrowserContext, Browser
from playwright.async_api._generated import Request
from playwright.async_api._generated import Route

from enums.api_enum import ClientEnum, MethodEnum, ApiTypeEnum
from enums.socket_api_enum import ApiSocketEnum
from enums.tools_enum import CacheKeyEnum
from enums.ui_enum import BrowserTypeEnum
from exceptions.ui_exception import BrowserPathError
from models.socket_model.api_model import ApiInfoModel
from models.socket_model.ui_model import WEBConfigModel
from service.socket_client import ClientWebSocket
from tools.data_processor.sql_cache import SqlCache
from tools.log_collector import log
from tools.message.error_msg import ERROR_MSG_0008, ERROR_MSG_0009


class NewBrowser:

    def __init__(self, web_config: WEBConfigModel):
        self.web_config = web_config
        self.browser_path = ['chrome.exe', 'msedge.exe', 'firefox.exe', '苹果', '360se.exe']

    async def new_browser(self) -> Browser:
        playwright = await async_playwright().start()
        if self.web_config.browser_type == BrowserTypeEnum.CHROMIUM.value or \
                self.web_config.browser_type == BrowserTypeEnum.EDGE.value:
            browser = playwright.chromium
        elif self.web_config.browser_type == BrowserTypeEnum.FIREFOX.value:
            browser = playwright.firefox
        elif self.web_config.browser_type == BrowserTypeEnum.WEBKIT.value:
            browser = playwright.webkit
        else:
            raise BrowserPathError(*ERROR_MSG_0008)
        try:
            self.web_config.browser_path = self.web_config.browser_path if self.web_config.browser_path else self.__search_path()
            if SqlCache.get_sql_cache(CacheKeyEnum.BROWSER_IS_MAXIMIZE.value):
                return await browser.launch(headless=self.web_config.is_headless == 1,
                                            executable_path=self.web_config.browser_path,
                                            args=['--start-maximized'])
            else:
                return await browser.launch(headless=self.web_config.is_headless == 1,
                                            executable_path=self.web_config.browser_path)
        except Error as error:
            raise BrowserPathError(*ERROR_MSG_0009, error=error)

    async def new_context(self, browser: Browser) -> BrowserContext:
        return await browser.new_context(no_viewport=True)

    async def new_page(self, context: BrowserContext) -> Page:
        page = await context.new_page()
        if self.web_config.is_header_intercept:
            await page.route("**/*", self.__intercept_request)  # 应用拦截函数到页面的所有请求
        return page

    def __search_path(self, ):
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if ctypes.windll.kernel32.GetDriveTypeW(drive) == 3:
                drives.append(drive)
        for i in drives:
            for root, dirs, files in os.walk(i):
                if self.browser_path[self.web_config.browser_type] in files:
                    return os.path.join(root, self.browser_path[self.web_config.browser_type])

    async def __intercept_request(self, route: Route, request: Request):
        """
        定义拦截请求的函数
        会有性能问题，因为所有的接口都会被添加进来,需要优化取请求头的路径，或者是增加条件
        @param route:
        @param request:
        @return:
        """
        if self.web_config.host is None:
            await route.continue_()  # 继续请求，不做修改
            return
        if self.web_config.host in request.url:  # 检查请求的URL是否包含目标路径
            if request.resource_type == "document" or request.resource_type == "xhr" or request.resource_type == "fetch":
                await self.send_recording_api(request)
        await route.continue_()  # 继续请求，不做修改

    async def send_recording_api(self, request: Request):
        if self.web_config.project is None:
            log.error('错误逻辑')
            return
        parsed_url = parse.urlsplit(request.url)

        try:
            json_data = request.post_data_json
        except Error:
            json_data = None

        data = {key: value[0] for key, value in
                parse.parse_qs(request.post_data).items()} if json_data is None else None
        params = {key: value[0] for key, value in
                  parse.parse_qs(parsed_url.query).items()} if parsed_url.query else None
        try:
            api_info = ApiInfoModel(
                project=self.web_config.project,
                type=ApiTypeEnum.batch.value,
                name=parsed_url.path,
                client=ClientEnum.WEB.value,
                url=parsed_url.path,
                method=MethodEnum.get_key(request.method),
                params=None if params == {} else params,
                data=None if data == {} else data,
                json_data=json_data
            )
            await ClientWebSocket.async_send(msg="发送录制接口", func_name=ApiSocketEnum.RECORDING_API.value,
                                             func_args=api_info)
        except Exception as e:
            log.info(f'json_data:{json_data}\t'
                             f'data:{data}\t'
                             f'params:{params}\t'
                             f'报错信息：{e}\t')
