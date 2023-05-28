# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏
import json

from pydantic import BaseModel


class InputValueModel(BaseModel):
    locating: str
    input_value: str | None


class ElementModel(BaseModel):
    ope_type: str
    ass_type: str | None
    ope_value: InputValueModel
    ass_value: dict | None
    ele_name_a: str
    ele_name_b: str | None
    ele_page_name: str
    ele_exp: int | None
    ele_loc: str
    ele_loc_b: str | None
    ele_sleep: int | None
    ele_sub: int | None
    ope_value_key: str | None


class CaseModel(BaseModel):
    case_id: int
    case_name: str
    local_port: str
    browser_path: str
    type: int
    case_url: str
    browser_type: int
    case_data: list[ElementModel]


class CaseGroupModel(BaseModel):
    group_name: str
    case_group: list[CaseModel]


class CaseResult(BaseModel):
    # 元素的名称
    ele_name_a: str
    ele_name_b: str
    # 元素个数
    ele_quantity: str
    # 测试结果
    state: str
    # 用例组ID
    case_group_id: str
    # 测试对象
    test_obj_id: str
    # 提示语
    msg: str
    # 错误截图路径
    picture_path: str


if __name__ == '__main__':
    with open(r'E:\GitCode\MangoTestingPlatform\MangoActuator\tests\test.json', 'r', encoding='utf-8') as f:
        json_dict = json.load(f)
        case_group_list = json_dict['case_group']
        case_group_obj = CaseGroupModel(group_name=json_dict['group_name'], case_group=case_group_list)
        print(case_group_obj.case_group[0].case_data[0].ope_value.input_value)
