# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:09
# @Author : 毛鹏
from .case import Case
from .case_result import CaseResult
from .case_steps_detailed import CaseStepsDetailed
from .config import Config
from .ele_result import EleResult
from .element import Element
from .page import Page
from .page_steps import PageSteps
from .page_steps_detailed import PageStepsDetailed
from .page_steps_result import PageStepsResult
from .public import Public


class Ui(Case, EleResult, Element, CaseResult, Page, PageSteps, PageStepsDetailed, CaseStepsDetailed, PageStepsResult,
         Public, Config):
    pass
