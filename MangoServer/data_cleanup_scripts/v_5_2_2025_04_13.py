# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-24 11:36
# @Author : 毛鹏

from mangokit.models import MethodModel
from src.auto_test.auto_ui.models import PageStepsDetailed


def page_steps_detailed():
    for i in PageStepsDetailed.objects.all():
        ope_value_list = []
        if isinstance(i.ope_value, dict):
            for key, value in i.ope_value.items():
                if key == 'locating' or key == 'actual':
                    ope_value_list.append(MethodModel(f=key, v=value, d=False).model_dump())
                else:
                    ope_value_list.append(MethodModel(f=key, v=value, d=True).model_dump())

            i.ope_value = ope_value_list
            i.save()


def main_5_5():
    page_steps_detailed()
