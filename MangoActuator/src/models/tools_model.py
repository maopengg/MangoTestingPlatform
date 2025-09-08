# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-08 15:48
# @Author : 毛鹏

from pydantic import BaseModel

from src.enums.gui_enum import TipsTypeEnum
from src.enums.tools_enum import MessageEnum


class MessageModel(BaseModel):
    type: MessageEnum
    msg: str | int
    level: TipsTypeEnum | None = None
