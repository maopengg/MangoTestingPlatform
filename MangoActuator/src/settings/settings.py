import json
import os
from typing import Optional

from mango_ui.models.models import *
from src.tools import InitPath
from src.tools.other.get_class_methods import GetClassMethod

IS_DEBUG = True
MEMORY_THRESHOLD = 80
LOOP_MIX = 10

IP = '填写IP'
PORT = '8000'
USERNAME = ''
PASSWORD = ''
base_dict: Optional[list[CascaderModel] | None] = None
UI_OPE_METHOD = GetClassMethod().option()

with open(os.path.join(InitPath.get_root_path(), 'src', 'settings', 'settings.json'), "r", encoding='utf-8') as f:
    STYLE = AppConfig(**json.loads(f.read()))

with open(os.path.join(InitPath.get_root_path(), 'src', 'settings', 'menus.json'), "r", encoding='utf-8') as f:
    MENUS = MenusModel(**json.loads(f.read()))


def get_option_value(option: list[dict], item1) -> str:
    for i in option:
        if i.get('children'):
            for e in i.get('children'):
                if e.get('children'):
                    for q in e.get('children'):
                        if q.get('value') == item1:
                            return q.get('label')
                else:
                    if e.get('value') == item1:
                        return e.get('label')
        if i.get('value') == item1:
            return i.get('label')
