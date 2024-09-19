import json
import os
from typing import Optional

from src.models.gui_model import MenusModel, AppConfig, ThemeConfig, CascaderModel
from src.tools import InitPath

IS_DEBUG = False
MEMORY_THRESHOLD = 80
LOOP_MIX = 10

IP = '填写IP'
PORT = '8000'
USERNAME = ''
PASSWORD = ''
base_dict: Optional[list[CascaderModel] | None] = None

with open(os.path.join(InitPath.get_root_path(), 'src', 'settings', 'settings.json'), "r", encoding='utf-8') as f:
    STYLE = AppConfig(**json.loads(f.read()))

with open(os.path.join(InitPath.get_root_path(), 'src', 'settings', f'{STYLE.theme_name}.json'), "r",
          encoding='utf-8') as f:
    THEME = ThemeConfig(**json.loads(f.read()))

with open(os.path.join(InitPath.get_root_path(), 'src', 'settings', 'menus.json'), "r", encoding='utf-8') as f:
    MENUS = MenusModel(**json.loads(f.read()))
