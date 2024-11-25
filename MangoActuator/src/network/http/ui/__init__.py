# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:09
# @Author : 毛鹏
from .ui_case import Case
from .ui_case_steps_detailed import CaseStepsDetailed
from .config import Config
from .page_element import Element
from .page import Page
from .page_steps import PageSteps
from .page_steps_detailed import PageStepsDetailed
from .public import Public


class UiApi(
    Case,
    Element,
    Page,
    PageSteps,
    PageStepsDetailed,
    CaseStepsDetailed,
    Public,
    Config
):
    pass
