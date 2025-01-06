import json
import os

from mango_ui import AppConfig, MenusModel

from src.tools import InitPath

# ****************************************** DEBUG ****************************************** #
IS_DEBUG = False

# ************************************** 是否弹出首页弹窗 ************************************** #
IS_WINDOW = False

# ***************************************** 内存阈值 ***************************************** #

MEMORY_THRESHOLD = 100  # 控制内存高于多少就不可以执行用例，防止崩溃
LOOP_MIX = 10  # 最大检查内存次数

# ************************************* 找不到元素循环次数 ************************************* #

FAILED_RETRY_TIME = 10  # 秒
RETRY_WAITING_TIME = 0.2  # 每隔多少秒重新一次

# **************************************** 下面不用管 **************************************** #

IP = None
PORT = None
USERNAME = None
PASSWORD = None

with open(os.path.join(InitPath.get_root_path(), 'src', 'settings', 'settings.json'), "r", encoding='utf-8') as f:
    STYLE = AppConfig(**json.loads(f.read()))

with open(os.path.join(InitPath.get_root_path(), 'src', 'settings', 'menus.json'), "r", encoding='utf-8') as f:
    MENUS = MenusModel(**json.loads(f.read()))
