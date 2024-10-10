import json
import os

from mango_ui import AppConfig, MenusModel

from src.tools import InitPath

IS_DEBUG = True
MEMORY_THRESHOLD = 80
LOOP_MIX = 10

IP = '填写IP'
PORT = '8000'
USERNAME = ''
PASSWORD = ''

with open(os.path.join(InitPath.get_root_path(), 'src', 'settings', 'settings.json'), "r", encoding='utf-8') as f:
    STYLE = AppConfig(**json.loads(f.read()))

with open(os.path.join(InitPath.get_root_path(), 'src', 'settings', 'menus.json'), "r", encoding='utf-8') as f:
    MENUS = MenusModel(**json.loads(f.read()))

