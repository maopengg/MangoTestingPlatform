# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-04-24 10:43
# @Author : 毛鹏
# import asyncio
# import ctypes
# import os
# import string
# from typing import Optional
# from urllib import parse
#
# import uiautomator2 as us
# from adbutils import AdbTimeout
# from playwright._impl._api_types import Error
# from playwright.async_api import async_playwright, Page, BrowserContext, Browser, Playwright
# from playwright.async_api._generated import Request
# from playwright.async_api._generated import Route
#
# import service_conn
# from enums.api_enum import ClientEnum, MethodEnum, ApiTypeEnum
# from enums.socket_api_enum import ApiSocketEnum
# from enums.tools_enum import CacheKeyEnum, StatusEnum
# from enums.ui_enum import BrowserTypeEnum
# from exceptions.ui_exception import BrowserPathError, NewObjectError
# from models.socket_model.api_model import ApiInfoModel
# from models.socket_model.ui_model import AndroidConfigModel
# from models.socket_model.ui_model import WEBConfigModel
# from service_conn.socket_conn.client_socket import WebSocketClient
# from tools.data_processor.sql_cache import SqlCache
# from tools.desktop.signal_send import SignalSend
# from tools.log_collector import log
# from tools.message.error_msg import ERROR_MSG_0008, ERROR_MSG_0009, ERROR_MSG_0042, ERROR_MSG_0045, ERROR_MSG_0047
# from tools.public_methods import async_global_exception
#
# """
# python -m uiautomator2 init
# python -m weditor
#
# """
#
#
from src.services.ui.bases.android.new_android import NewAndroid
from src.services.ui.bases.web.new_browser import NewBrowser


class DriverObject(NewBrowser, NewAndroid):
    pass
#     def __init__(self, web_config: WEBConfigModel = None, android_config: AndroidConfigModel = None):
#         self.lock = asyncio.Lock()
#
#         self.android_config = android_config
#
#         self.web_config = web_config
#         self.browser_path = ['chrome.exe', 'msedge.exe', 'firefox.exe', '苹果', '360se.exe']
#         self.browser: Optional[None | Browser] = None
#         self.playwright: Optional[None | Playwright] = None
#
#     def new_android(self):
#         SignalSend.notice_signal_c('正在创建安卓设备')
#         if self.android_config is None:
#             raise NewObjectError(*ERROR_MSG_0042)
#         android = us.connect(self.android_config.equipment)
#
#         try:
#             SignalSend.notice_signal_c(f"设备启动成功！产品名称：{android.info.get('productName')}")
#         except RuntimeError:
#             SignalSend.notice_signal_c(ERROR_MSG_0045[1].format(self.android_config.equipment))
#             raise NewObjectError(*ERROR_MSG_0045, value=(self.android_config.equipment,))
#         except (AdbTimeout, TimeoutError):
#             SignalSend.notice_signal_c(ERROR_MSG_0047[1].format(self.android_config.equipment))
#             raise NewObjectError(*ERROR_MSG_0047, value=(self.android_config.equipment,))
#         else:
#             android.implicitly_wait(10)
#             return android
#
#     async def new_web_page(self) -> tuple[BrowserContext, Page]:
#         if self.web_config is None:
#             raise NewObjectError(*ERROR_MSG_0042)
#         if self.browser is None:
#             async with self.lock:
#                 if self.browser is None:
#                     self.browser = await self.new_browser()
#         SignalSend.notice_signal_c('正在创建浏览器窗口')
#         context = await self.new_context()
#         page = await self.new_page(context)
#         return context, page
#
#     async def new_browser(self) -> Browser:
#         SignalSend.notice_signal_c('正在启动浏览器')
#         self.playwright = await async_playwright().start()
#         if self.web_config.browser_type \
#                 == BrowserTypeEnum.CHROMIUM.value or self.web_config.browser_type == BrowserTypeEnum.EDGE.value:
#             self.browser = self.playwright.chromium
#         elif self.web_config.browser_type == BrowserTypeEnum.FIREFOX.value:
#             self.browser = self.playwright.firefox
#         elif self.web_config.browser_type == BrowserTypeEnum.WEBKIT.value:
#             self.browser = self.playwright.webkit
#         else:
#             raise BrowserPathError(*ERROR_MSG_0008)
#         try:
#             self.web_config \
#                 .browser_path = self.web_config \
#                 .browser_path if self.web_config \
#                 .browser_path else self.__search_path()
#
#             if SqlCache.get_sql_cache(CacheKeyEnum.BROWSER_IS_MAXIMIZE.value):
#                 return await self.browser.launch(
#                     headless=self.web_config.is_headless == StatusEnum.SUCCESS.value,
#                     executable_path=self.web_config.browser_path,
#                     args=['--start-maximized']
#                 )
#             else:
#                 return await self.browser.launch(
#                     headless=self.web_config.is_headless == StatusEnum.SUCCESS.value,
#                     executable_path=self.web_config.browser_path
#                 )
#         except Error:
#             raise BrowserPathError(*ERROR_MSG_0009, value=(self.web_config.browser_path,))
#
#     async def new_context(self) -> BrowserContext:
#         if self.web_config.device:
#             return await self.browser \
#                 .new_context(**self.playwright.devices[self.web_config.device])
#         else:
#             return await self.browser.new_context(no_viewport=True)
#
#     async def new_page(self, context: BrowserContext) -> Page:
#         page = await context.new_page()
#         if self.web_config.is_header_intercept:
#             await page.route("**/*", self.__intercept_request)  # 应用拦截函数到页面的所有请求
#         return page
#
#     async def close(self):
#         if self.web_config:
#             if self.browser:
#                 await self.browser.close()
#         if self.android_config:
#             pass
#
#     def __search_path(self, ):
#         drives = []
#         for letter in string.ascii_uppercase:
#             drive = f"{letter}:\\"
#             if ctypes.windll.kernel32.GetDriveTypeW(drive) == 3:
#                 drives.append(drive)
#         for i in drives:
#             for root, dirs, files in os.walk(i):
#                 if self.browser_path[self.web_config.browser_type] in files:
#                     return os.path.join(root, self.browser_path[self.web_config.browser_type])
#
#     async def __intercept_request(self, route: Route, request: Request):
#         """
#         定义拦截请求的函数
#         会有性能问题，因为所有的接口都会被添加进来,需要优化取请求头的路径，或者是增加条件
#         @param route:
#         @param request:
#         @return:
#         """
#         if self.web_config.host is None:
#             await route.continue_()  # 继续请求，不做修改
#             return
#         if self.web_config.host in request.url:  # 检查请求的URL是否包含目标路径
#             if request.resource_type == "document" or request.resource_type == "xhr" or request.resource_type == "fetch":
#                 await self.__send_recording_api(request)
#         await route.continue_()  # 继续请求，不做修改
#
#     async def __send_recording_api(self, request: Request):
#         if self.web_config.project_product_id is None:
#             log.error('错误逻辑')
#             return
#         parsed_url = parse.urlsplit(request.url)
#
#         try:
#             json_data = request.post_data_json
#         except Error:
#             json_data = None
#
#         data = {key: value[0] for key, value in
#                 parse.parse_qs(request.post_data).items()} if json_data is None else None
#         params = {key: value[0] for key, value in
#                   parse.parse_qs(parsed_url.query).items()} if parsed_url.query else None
#         try:
#             api_info = ApiInfoModel(
#                 project=self.web_config.project_product_id,
#                 username=service_conn.USERNAME,
#                 type=ApiTypeEnum.batch.value,
#                 name=parsed_url.path,
#                 client=ClientEnum.WEB.value,
#                 url=parsed_url.path,
#                 method=MethodEnum.get_key(request.method),
#                 params=None if params == {} else params,
#                 data=None if data == {} else data,
#                 json_data=json_data
#             )
#             await WebSocketClient().async_send(
#                 msg="发送录制接口",
#                 func_name=ApiSocketEnum.RECORDING_API.value,
#                 func_args=api_info
#             )
#         except Exception as error:
#             await async_global_exception(
#                 '__send_recording_api',
#                 error
#             )
#
#
