# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:09
# @Author : 毛鹏
from .config import Config
from .page import Page
from .page_element import Element
from .page_steps import PageSteps
from .page_steps_detailed import PageStepsDetailed
from .public import Public
from .ui_case import Case
from .ui_case_steps_detailed import CaseStepsDetailed


class UiApi:
    case = Case
    case_steps_detailed = CaseStepsDetailed
    config = Config
    element = Element
    page = Page
    page_steps = PageSteps
    page_steps_detailed = PageStepsDetailed
    public = Public
