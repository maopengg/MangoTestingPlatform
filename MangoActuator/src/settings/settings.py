import json
import os

from mango_ui import AppConfig, MenusModel

from src.tools import project_dir

IS_DEBUG = False
IS_WINDOW = False

MEMORY_THRESHOLD = 100

LOOP_MIX = 10

FAILED_RETRY_TIME = 10
RETRY_WAITING_TIME = 0.2

IP = None
PORT = None
USERNAME = None
PASSWORD = None

with open(os.path.join(project_dir.root_path(), 'src', 'settings', 'settings.json'), "r", encoding='utf-8') as f:
    STYLE = AppConfig(**json.loads(f.read()))

with open(os.path.join(project_dir.root_path(), 'src', 'settings', 'menus.json'), "r", encoding='utf-8') as f:
    MENUS = MenusModel(**json.loads(f.read()))
