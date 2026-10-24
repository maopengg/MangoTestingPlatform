import json

from src.tools import project_dir

# ****************************************** 是否公开给其他人使用 ****************************************** #
IS_OPEN = True
# ****************************************** DEBUG ****************************************** #
IS_DEBUG = False
# **************************************** 下面不用管 **************************************** #
try:
    with open('src/settings/settings.json', "r", encoding='utf-8') as f:
        SETTINGS: dict = json.load(f)
except FileNotFoundError:
    with open(project_dir.resource_path('src/settings/settings.json'), "r", encoding='utf-8') as f:
        SETTINGS: dict = json.load(f)
MEMORY_THRESHOLD = 100  # 控制内存高于多少就不可以执行用例，防止崩溃
LOOP_MIX = 10  # 最大检查内存次数
# **************************************** 上面不用管 **************************************** #
