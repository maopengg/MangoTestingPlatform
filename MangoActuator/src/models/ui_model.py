# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏
from pydantic import BaseModel

from src.models.tools_model import MysqlConingModel


class UiPublicModel(BaseModel):
    type: int
    key: str
    value: str


class WEBConfigModel(BaseModel):
    """ web启动配置 """
    browser_type: int
    browser_port: str | None = None
    browser_path: str | None = None
    is_headless: int | None = None
    is_header_intercept: bool = False
    device: str | None = None
    host_list: list[dict] | None = None


class AndroidConfigModel(BaseModel):
    equipment: str


class EnvironmentConfigModel(BaseModel):
    test_object_value: str
    db_c_status: bool
    db_rud_status: bool
    mysql_config: MysqlConingModel | None = None


class ElementModel(BaseModel):
    id: int
    type: int
    name: str | None
    loc: str | None
    exp: int | None
    sleep: int | None
    sub: int | None
    ope_key: str | None
    ope_value: dict | None
    is_iframe: int | None
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
    project_product: int
    type: int
    url: str
    case_data: list[StepsDataModel] = []
    element_list: list[ElementModel] = []
    equipment_config: AndroidConfigModel | WEBConfigModel
    environment_config: EnvironmentConfigModel
    public_data_list: list[UiPublicModel] = []


class CaseModel(BaseModel):
    test_suite_id: int
    id: int
    project_product: int
    module_name: str
    name: str
    case_people: str
    front_custom: list
    front_sql: list
    posterior_sql: list
    steps: list[PageStepsModel]
    public_data_list: list[UiPublicModel] = []


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

    type: int
    ope_key: str | None = None
    ope_value: dict | str | None = None
    ass_value: dict | None = None
    expect: str | None = None
    actual: str | None = None
    sql: str | None = None
    key_list: str | None = None
    key: str | None = None
    value: str | None = None


class PageStepsResultModel(BaseModel):
    test_suite_id: int | None = None
    case_id: int | None = None
    case_step_details_id: int | None = None
    page_step_id: int | None = None
    page_step_name: str
    status: int
    error_message: str | None = None
    element_result_list: list[ElementResultModel]


class CaseResultModel(BaseModel):
    test_suite_id: int
    case_id: int
    case_name: str
    module_name: str
    case_people: str
    test_obj: str | None = None
    status: int
    error_message: str | None = None
    page_steps_result_list: list[PageStepsResultModel]
    video_path: str | None = None
