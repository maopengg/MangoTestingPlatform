# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-24 11:36
# @Author : 毛鹏
import json
import re

from src.auto_test.auto_api.models import ApiCase, ApiCaseDetailed, ApiInfo, ApiPublic
from src.auto_test.auto_ui.models import PageElement, PageStepsDetailed, UiCase, UiCaseStepsDetailed


def replace_json_field(field):
    if isinstance(field, str):
        return re.sub(r'\$\{(.*?)\}', r'${{\1}}', field)
    elif isinstance(field, list):
        # 如果字段是列表，直接处理每个元素
        return [replace_json_field(item) for item in field]  # 使用列表推导式处理每个元素
    elif isinstance(field, dict):
        # 如果字段是字典，递归处理每个键值对
        return {key: replace_json_field(value) for key, value in field.items()}
    return None


def api_case():
    for i in ApiCase.objects.all():
        i.front_custom = replace_json_field(i.front_custom)
        i.front_sql = replace_json_field(i.front_sql)
        i.front_headers = replace_json_field(i.front_headers)
        i.posterior_sql = replace_json_field(i.posterior_sql)
        i.save()


def api_case_detailed():
    for i in ApiCaseDetailed.objects.all():
        i.url = replace_json_field(i.url)
        i.header = replace_json_field(i.header)
        i.params = replace_json_field(i.params)
        i.data = replace_json_field(i.data)
        i.json = replace_json_field(i.json)
        i.file = replace_json_field(i.file)
        i.front_sql = replace_json_field(i.front_sql)
        i.ass_sql = replace_json_field(i.ass_sql)
        i.ass_response_whole = replace_json_field(i.ass_response_whole)
        i.ass_response_value = replace_json_field(i.ass_response_value)
        i.posterior_sql = replace_json_field(i.posterior_sql)
        i.posterior_response = replace_json_field(i.posterior_response)
        i.save()


def api_info():
    for i in ApiInfo.objects.all():
        i.url = replace_json_field(i.url)
        i.header = replace_json_field(i.header)
        i.params = replace_json_field(i.params)
        i.data = replace_json_field(i.data)
        i.json = replace_json_field(i.json)
        i.file = replace_json_field(i.file)
        i.save()


def api_public():
    for i in ApiPublic.objects.all():
        i.value = replace_json_field(i.value)
        i.save()


def page_element():
    for i in PageElement.objects.all():
        i.loc = replace_json_field(i.loc)
        i.save()


def page_steps_detailed():
    for i in PageStepsDetailed.objects.all():
        i.ope_value = replace_json_field(i.ope_value)
        i.save()


def ui_case():
    for i in UiCase.objects.all():
        i.front_custom = replace_json_field(i.front_custom)
        i.front_sql = replace_json_field(i.front_sql)
        i.posterior_sql = replace_json_field(i.posterior_sql)
        i.save()


def ui_case_steps_detailed():
    for i in UiCaseStepsDetailed.objects.all():
        i.case_data = replace_json_field(i.case_data)
        i.case_cache_data = replace_json_field(i.case_cache_data)
        i.case_cache_ass = replace_json_field(i.case_cache_ass)
        i.save()


def main_4_7():
    api_case()
    api_case_detailed()
    api_info()
    api_public()
    page_element()
    page_steps_detailed()
    ui_case()
    ui_case_steps_detailed()
