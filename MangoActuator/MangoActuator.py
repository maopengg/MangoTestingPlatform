# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import asyncio
#

from client.client_socket import ClientWebSocket
from utlis.nuw_logs import NewLog


def run():
    print("================执行端正在启动================")
    client = ClientWebSocket()
    loop = asyncio.new_event_loop()  # 创建新的事件循环
    asyncio.set_event_loop(loop)  # 设置新的事件循环为当前事件循环
    loop.run_until_complete(client.client_run())  # 运行事件循环


if __name__ == '__main__':
    # pyinstaller -F -c .\MangoActuator.py
    NewLog()
    run()
    # print(__file__)
    # print(os.path.dirname(sys.executable))
    # with open('tests/debug_case.json', 'r') as f:
    #     test_cases_json = json.load(f)
    #     print(test_cases_json)
    # import subprocess
    #
    # subprocess.run(["pytest", "tests/"])
    # time.sleep(5)
