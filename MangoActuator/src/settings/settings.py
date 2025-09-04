import json
import os

from src.tools import project_dir

# ****************************************** 是否公开给其他人使用 ****************************************** #
IS_OPEN = False
# ****************************************** DEBUG ****************************************** #
IS_DEBUG = False
# ************************************** 是否弹出首页弹窗 ************************************** #
IS_WINDOW = True

# ******************************* 是否发送error日志协助芒果修复问题 ******************************* #
IS_SEND_MAIL = True

# **************************************** 下面不用管 **************************************** #
try:
    with open('src/settings/settings.json', "r", encoding='utf-8') as f:
        SETTINGS: dict = json.load(f)
    with open('src/settings/menus_2.json', "r", encoding='utf-8') as f:
        MENUS: dict = json.load(f)
except FileNotFoundError:
    with open(project_dir.resource_path('src/settings/settings.json'), "r", encoding='utf-8') as f:
        SETTINGS: dict = json.load(f)
    with open(project_dir.resource_path('src/settings/menus_2.json'), "r", encoding='utf-8') as f:
        MENUS: dict = json.load(f)
MEMORY_THRESHOLD = 100  # 控制内存高于多少就不可以执行用例，防止崩溃
LOOP_MIX = 10  # 最大检查内存次数
# **************************************** 上面不用管 **************************************** #
