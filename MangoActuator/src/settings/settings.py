import json
import platform

from src.tools import project_dir

# ****************************************** 用户信息 ****************************************** #
IP = None
PORT = None
USERNAME = None
PASSWORD = None
# ****************************************** DEBUG ****************************************** #
IS_DEBUG = False
# ************************************** 是否弹出首页弹窗 ************************************** #
IS_WINDOW = True

# ******************************* 是否发送error日志协助芒果修复问题 ******************************* #
IS_SEND_MAIL = True


# **************************************** 文件资源路径 **************************************** #
# 如果是后端开启了minio则配置minio的地址，请携带桶名称作为路径，默认桶名称是：mango-file
# 如果没有开启minio的示例：
def FILE_PATH():
    return f"http://{IP}:9000"


# 开启minio的示例：
# def FILE_PATH():
#     return 'http://127.0.0.1:9000/mango-file'

# **************************************** 下面不用管 **************************************** #
if platform.system() != "Linux":
    from mangoui import AppConfig, MenusModel

    with open(project_dir.resource_path('src/settings/settings.json'), "r", encoding='utf-8') as f:
        STYLE = AppConfig(**json.loads(f.read()))
    with open(project_dir.resource_path('src/settings/menus.json'), "r", encoding='utf-8') as f:
        MENUS = MenusModel(**json.loads(f.read()))

MEMORY_THRESHOLD = 100  # 控制内存高于多少就不可以执行用例，防止崩溃
LOOP_MIX = 10  # 最大检查内存次数
# **************************************** 上面不用管 **************************************** #
