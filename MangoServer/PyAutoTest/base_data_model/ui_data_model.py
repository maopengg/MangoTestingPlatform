# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏
from pydantic import BaseModel


class InputValueModel(BaseModel):
    locating: str
    input_value: str | None

    @classmethod
    def create_empty(cls) -> "InputValueModel":
        return cls(locating=str, input_value=None)


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

    @classmethod
    def create_empty(cls) -> "ElementModel":
        return cls(
            ope_type="",
            ass_type=None,
            ope_value=InputValueModel.create_empty(),
            ass_value=None,
            ele_name_a="",
            ele_name_b=None,
            ele_page_name="",
            ele_exp=None,
            ele_loc="",
            ele_loc_b=None,
            ele_sleep=None,
            ele_sub=None,
            ope_value_key=None,
        )


class CaseModel(BaseModel):
    case_id: int
    case_name: str
    local_port: str
    browser_path: str
    type: int
    case_url: str
    browser_type: int
    equipment: str
    package: str
    case_data: list[ElementModel]

    @classmethod
    def create_empty(cls) -> "CaseModel":
        return cls(case_id=0, case_name="", local_port="", browser_path="", type=0, case_url="",
                   browser_type=0, equipment="", package="", case_data=[])


class CaseGroupModel(BaseModel):
    group_name: str
    case_group: list[CaseModel]


class CaseGroupListModel(BaseModel):
    list: list[CaseGroupModel]


class CaseResult(BaseModel):
    # 元素的名称
    ele_name_a: str
    ele_name_b: str
    # 元素个数
    ele_quantity: str
    # 测试结果
    state: bool
    # 用例组ID
    case_group_id: str
    # 测试对象
    test_obj_id: str
    # 提示语
    msg: str
    # 错误截图路径
    picture_path: str

    @classmethod
    def create_empty(cls):
        return cls(ele_name_a="", ele_name_b="", ele_quantity="", state="", case_group_id="", test_obj_id="", msg="",
                   picture_path="")


class OneCaseResult(BaseModel):
    test_result: bool
    ele_res_list: list[CaseResult]

    @classmethod
    def create_empty(cls):
        return cls(test_result=False, ele_res_list=[])
