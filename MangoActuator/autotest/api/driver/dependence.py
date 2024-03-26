# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏

from models.socket_model.api_model import RequestModel
from tools.data_processor import DataProcessor
from tools.database_tool.mysql_connect import MysqlConnect
from tools.logging_tool import logger


class Dependence(DataProcessor):

    async def api_ago_dependency(self):
        """
        前置依赖
        @return:
        """

    async def api_after_dependency(self):
        """
        后置处理
        @return:
        """

    async def api_result_ass(self):
        """
        结果断言
        @return:
        """

    async def api_after_empty(self):
        """
        后置数据清除
        @return:
        """

    async def public_login(self, key, request: RequestModel):
        """
        处理登录token
        @return:
        """
        pass
        # session = aiohttp.ClientSession()
        # response = await HTTPRequest.http_post(session=session,
        #                                        url=request.url,
        #                                        headers=request.header,
        #                                        data=eval(
        #                                            self.replace_text(request.body)) if request.body else None)
        # self.set_cache(key, await self.get_json_path_value(await response[0].json(), '$.access_token'))
        # INFO.logger.info(f'公共参数Token设置成功：{self.get_cache(key)}')
        # await session.close()

    async def public_header(self, key, header):
        """
        处理接口请求头
        @param key: 缓存key
        @param header: header
        @return:
        """
        self.set_cache(key, self.replace_text(header))
        logger.info(f'公共参数请求头设置成功：{self.get_cache(key)}')

    async def public_ago_sql(self, key, sql):
        """
        处理前置sql
        @return:
        """
        sql = self.replace_text(sql)
        my: MysqlConnect = MysqlConnect()
        await my.connect(self.get_cache('database_tool'))
        sql_res_list = await my.select(sql)
        k_list = []
        for sql_res_dict in sql_res_list:
            for k, v in sql_res_dict.items():
                self.set_cache(f'{key}_{k}', v)
                k_list.append(k)
        for i in k_list:
            logger.info(f'公共参数sql设置成功：{self.get_cache(f"{key}_{i}")}')

    async def public_customize(self, key, value):
        """
        自定义参数
        @return:
        """
        self.set_cache(key, value)
        logger.info(f'公共参数自定义设置成功：{self.get_cache(key)}')
