# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏
from pydantic import BaseModel

from models.tools_model import MysqlConingModel


class UiPublicModel(BaseModel):
    create_time: str
    update_time: str
    project: int
    type: int
    name: str
    key: str
    value: str
    status: int


class WEBConfigModel(BaseModel):
    """ web启动配置 """
    browser_type: int
    browser_port: str | None
    browser_path: str | None
    is_headless: int | None
    is_header_intercept: bool = False
    host: str | None = None
    project: int | None = None


class AndroidConfigModel(BaseModel):
    equipment: str


class RunConfigModel(BaseModel):
    db_c_status: bool
    db_rud_status: bool
    mysql_config: MysqlConingModel | None = None
    public_data_list: list[UiPublicModel] | None = None


class ElementModel(BaseModel):
    id: int
    type: int
    name: str | None
    loc: str | None
    exp: int | None
    sleep: int | None
    sub: int | None
    ope_type: str | None
    ope_value: dict | None
    is_iframe: int | None
    ass_type: str | None
    ass_value: dict | None
    key_list: list | None = None
    sql: str | None = None
    key: str | None = None
    value: str | None = None


class StepsDataModel(BaseModel):
    type: int | None = None
    page_step_details_id: int
    page_step_details_data: dict
    page_step_details_name: str | None = None


class PageStepsModel(BaseModel):
    id: int | None = None
    name: str
    case_step_details_id: int | None
    project: int
    test_object_value: str
    url: str
    type: int
    case_data: list[StepsDataModel] = []
    element_list: list[ElementModel] = []
    equipment_config: AndroidConfigModel | WEBConfigModel
    # public_data_list: list[UiPublicModel] | None = None
    # mysql_config: MysqlConingModel | None = None
    run_config: RunConfigModel | None = None


class CaseModel(BaseModel):
    id: int
    project: int
    module_name: str
    name: str
    is_batch: int
    case_people: str
    case_list: list[PageStepsModel]
    front_custom: list
    front_sql: list
    posterior_sql: list
    run_config: RunConfigModel


class ElementResultModel(BaseModel):
    page_step_id: int | None = None
    test_suite_id: int | None = None
    case_id: int | None = None
    case_step_details_id: int | None = None

    ele_name: str | None = None
    ele_quantity: int
    error_message: str | None = None
    picture_path: str | None = None
    status: int

    loc: str | None = None
    exp: int | None = None
    sleep: int | None = None
    sub: int | None = None

    ope_type: str | None = None
    ope_value: dict | str | None = None
    ass_type: str | None = None
    ass_value: dict | None = None
    expect: str | None = None
    actual: str | None = None


class PageStepsResultModel(BaseModel):
    test_suite_id: int | None
    case_id: int | None
    case_step_details_id: int | None
    page_step_id: int | None = None

    page_step_name: str

    status: int
    error_message: str | None
    element_result_list: list[ElementResultModel]


class CaseResultModel(BaseModel):
    test_suite_id: int
    case_id: int

    is_batch: int
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
    concurrent: int | None = None
