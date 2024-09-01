import json

from src.models.gui_model import MenusModel, AppConfig, ThemeConfig
from src.tools import InitPath

IS_DEBUG = False
MEMORY_THRESHOLD = 80
LOOP_MIX = 10

IP = '填写IP'
PORT = '8000'
USERNAME = ''
PASSWORD = ''

with open(rf'{InitPath.project_root_directory}\src\settings\settings.json', "r", encoding='utf-8') as f:
    STYLE = AppConfig(**json.loads(f.read()))

with open(rf'{InitPath.project_root_directory}\src\settings\{STYLE.theme_name}.json', "r", encoding='utf-8') as f:
    THEME = ThemeConfig(**json.loads(f.read()))
with open(rf'{InitPath.project_root_directory}\src\settings\menus.json', "r", encoding='utf-8') as f:
    MENUS = MenusModel(**json.loads(f.read()))
