import json

from mango_ui import AppConfig, MenusModel

from src.tools import project_dir

# **************************************** 下面不用管 **************************************** #
IP = None
PORT = None
USERNAME = None
PASSWORD = None
with open(project_dir.resource_path('src/settings/settings.json'), "r", encoding='utf-8') as f:
    STYLE = AppConfig(**json.loads(f.read()))
with open(project_dir.resource_path('src/settings/menus.json'), "r", encoding='utf-8') as f:
    MENUS = MenusModel(**json.loads(f.read()))
# **************************************** 上面不用管 **************************************** #

# ****************************************** DEBUG ****************************************** #
IS_DEBUG = False
# ************************************** 是否弹出首页弹窗 ************************************** #
IS_WINDOW = True
# ************************************* 找不到元素循环次数 ************************************* #
FAILED_RETRY_TIME = 10  # 秒
RETRY_WAITING_TIME = 0.2  # 每隔多少秒重新一次
# **************************************** 文件资源路径 **************************************** #
IS_MINIO = False
FILE_PATH = IP  # 配置IP则代表你没有minio，如果有minio则配置mini的IP和端口
# ***************************************** 内存阈值 ***************************************** #
# 现在没有用到这个配置
MEMORY_THRESHOLD = 100  # 控制内存高于多少就不可以执行用例，防止崩溃
LOOP_MIX = 10  # 最大检查内存次数
