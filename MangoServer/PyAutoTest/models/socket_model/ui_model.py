# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏
from pydantic import BaseModel

from PyAutoTest.models.tools_model import MysqlConingModel


class UiPublicModel(BaseModel):
    create_time: str
    update_time: str
    project: int
    type: int
    name: str
    key: str
    value: str
    status: int


class ElementModel(BaseModel):
    id: int
    type: int
    ele_name_a: str | None
    ele_name_b: str | None
    ele_loc_a: str | None
    locator: str | None

    ele_loc_b: str | None
    ele_exp: int | None
    ele_sleep: int | None
    ele_sub: int | None
    ope_type: str | None
    ope_value: dict | None
    is_iframe: int | None
    ass_type: str | None
    ass_value: dict | None


class WEBConfigModel(BaseModel):
    """ web启动配置 """
    browser_type: int
    browser_port: str | None
    browser_path: str | None
    is_headless: int | None
    is_header_intercept: bool = False
    host: str | None = None
    project_id: int | None = None


class AndroidConfigModel(BaseModel):
    equipment: str
    package_name: str


class PageStepsModel(BaseModel):
    id: int
    name: str
    case_step_details_id: int | None
    project_id: int
    host: str
    url: str
    type: int
    element_list: list[ElementModel] = []
    equipment_config: AndroidConfigModel | WEBConfigModel
    public_data_list: list[UiPublicModel] | None = None
    mysql_config: MysqlConingModel | None = None


class CaseModel(BaseModel):
    id: int
    name: str
    is_batch: int
    project_id: int
    module_name: str
    case_people: str
    case_data: list[list[dict] | list]
    case_list: list[PageStepsModel]
    public_data_list: list[UiPublicModel] | None
    mysql_config: MysqlConingModel | None


class ElementResultModel(BaseModel):
    test_suite_id: int | None
    case_id: int | None
    page_step_id: int | None

    ele_name_a: str | None
    ele_name_b: str | None
    ele_quantity: int
    error_message: str | None
    picture_path: str | None
    status: int

    loc: str | None
    exp: int | None
    sleep: int | None
    sub: int | None

    ope_type: str | None
    ope_value: dict | str | None
    ass_type: str | None
    ass_value: dict | None
    expect: str | None
    actual: str | None


class PageStepsResultModel(BaseModel):
    test_suite_id: int | None
    case_id: int | None
    case_step_details_id: int | None
    page_step_id: int
    page_step_name: str

    status: int
    error_message: str | None
    element_result_list: list[ElementResultModel]


class CaseResultModel(BaseModel):
    test_suite_id: int
    is_batch: int
    case_id: int
    case_name: str
    module_name: str
    case_people: str
    test_obj: str
    status: int
    error_message: str | None
    page_steps_result_list: list[PageStepsResultModel]


class TestSuiteModel(BaseModel):
    id: int
    type: int
    project: int
    test_object: int
    run_status: int
    is_notice: int | None
    status: int | None
    error_message: str | None
    case_list: list[CaseModel] | None = None
