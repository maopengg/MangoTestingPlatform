# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-02-19 15:05
# @Author : 毛鹏
import json

import requests
import time
from sqlalchemy import text, create_engine
from sqlalchemy.engine.base import Engine

PRO_MYSQL_IP = 'zdtool.mysql.polardb.zhangbei.rds.aliyuncs.com'
PRO_MYSQL_PORT = 3306
PRO_MYSQL_USERNAME = 'zdtool_test'
PRO_MYSQL_PASSWORD = 'Zdtool2024+'
PRO_MYSQL_DATABASE = 'z_desk_efficiency'
connection_string = f"mysql+pymysql://{PRO_MYSQL_USERNAME}:{PRO_MYSQL_PASSWORD}@{PRO_MYSQL_IP}:{PRO_MYSQL_PORT}/{PRO_MYSQL_DATABASE}"
engine: Engine = create_engine(connection_string)

headers = {
    'Content-Type': 'application/json'
}

# 域名常量
DOMAIN = "https://zdtoolpre.zalldigital.cn/"


class MockTask:
    def __init__(self):
        pass

    def while_task(self, ):
        keys_list = [
            '1', '2', '3', '301', '302', '303', '304', '305', '306', '307', '308',
            '310', '313', '401', '402', '403', '601', '602', '801', '701', '702', '703', '704',
            '705', '706',
        ]
        keys = ','.join(keys_list)
        while True:
            try:
                response = requests.get(
                    f"{DOMAIN}api/z-tool-data/reptile/getNonExecutionTask?businessType={keys}",
                    headers=headers, proxies={'http': None, 'https': None})
                print(f'获取任务：{response.text}')
                response_dict = response.json()
                if response_dict['resData'] is not None:
                    task_id = int(response_dict['resData']['taskId'])
                    request_params = json.loads(response_dict['resData']['businessParam'])
                    data: str = self.get_task_data(response_dict['resData']['businessType'], request_params)
                    if data:
                        self.upload_data(task_id, data, response_dict['resData']['businessType'])
                    time.sleep(0.1)
                else:
                    time.sleep(3)
            except Exception:
                return self.while_task()

    def upload_data(self, task_id: int, data: str, business_type: str):
        """
        模拟上传接口
        :param task_id: 任务的ID
        :param data: 上传的数据
        :param business_type: 业务类型
        :return:
        """
        print(f'上传数据{task_id}：{data}')
        if business_type == 306:
            data = {"taskDetailId": f"{task_id}", "status": 1, "businessData": data}
            response = requests.post(f"{DOMAIN}api/z-tool-data/ad-market/task/uploadTaskResult",
                                     headers=headers, data=json.dumps(data), proxies={'http': None, 'https': None})
        else:
            data = {"taskId": f"{task_id}", "status": 1, "businessData": data}
            response = requests.post(f"{DOMAIN}api/z-tool-data/reptile/uploadData",
                                     headers=headers, data=json.dumps(data), proxies={'http': None, 'https': None})
        print(f'上传数据结果{task_id}：{response.text}')
        return response.json()

    def get_task_data(self, business_type, request_params: dict | None = None) -> str | None:
        one_row = None

        sql = f"""
              SELECT response_data
              FROM addata_market_spider_fetcher_data_detail
              WHERE request_id = (SELECT id
                                  FROM addata_market_spider_fetcher_request_detail
                                  WHERE type = "{business_type}"
                                    AND `status` = 1
                                  ORDER BY id DESC LIMIT 1);
              """
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            row = result.fetchone()
            if row:
                one_row = json.loads(row[0])
        if business_type == 801:
            if len(one_row) >= 1:
                return json.dumps(one_row[:len(request_params['keyword_list'])], ensure_ascii=False)
            return None
        else:
            return json.dumps(one_row, ensure_ascii=False)


if __name__ == '__main__':
    print("开始运行模拟任务...")
    mock_task = MockTask()
    mock_task.while_task()
    print("模拟任务运行结束")