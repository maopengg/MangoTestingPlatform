# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏
from pydantic import BaseModel

from mangokit import MysqlConingModel


class EquipmentModel(BaseModel):
    type: int
    web_max: bool | None = None
    web_recording: bool | None = None
    web_parallel: int | None = None
    web_type: int | None = None
    web_h5: str | None = None
    web_path: str | None = None
    web_headers: bool | None = None
    and_equipment: str | None = None
    host_list: list[dict] | None = None
    is_header_intercept: bool | None = None


class UiPublicModel(BaseModel):
    type: int
    key: str
    value: str


class EnvironmentConfigModel(BaseModel):
    id: int
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
    is_iframe: int | None
    ope_key: str | None
    ope_value: dict | None
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
    id: int
    name: str
    project_product: int
    module_name: str
    type: int
    url: str
    element_list: list[ElementModel] = []
    equipment_config: EquipmentModel
    environment_config: EnvironmentConfigModel

    public_data_list: list[UiPublicModel] = []
    case_step_details_id: int | None = None
    case_data: list[StepsDataModel] = []


class CaseModel(BaseModel):
    test_suite_details: int | None
    test_suite_id: int | None
    id: int
    name: str
    project_product: int
    project_product_name: str
    module_name: str
    test_env: int
    case_people: str
    front_custom: list
    front_sql: list
    posterior_sql: list
    steps: list[PageStepsModel]
    public_data_list: list[UiPublicModel] = []


class ElementResultModel(BaseModel):
    id: int
    name: str
    loc: str | None = None
    exp: int | None = None
    sleep: int | None = None
    sub: int | None = None

    type: int
    ope_key: str | None = None
    ope_value: dict | str | None = None
    expect: str | None = None
    actual: str | None = None
    sql: str | None = None
    key_list: str | None = None
    key: str | None = None
    value: str | None = None

    status: int
    ele_quantity: int
    error_message: str | None = None
    picture_path: str | None = None


class PageStepsResultModel(BaseModel):
    id: int
    name: str
    type: int
    project_product_id: int
    project_product_name: int
    case_steps_detail_id: int | None = None

    cache_data: dict
    test_object: dict  # url或者软件包
    equipment: dict  # 设备名称或者浏览器类型

    status: int
    error_message: str | None = None
    element_result_list: list[ElementResultModel]


class UiCaseResultModel(BaseModel):
    id: int
    name: str
    project_product_id: int
    project_product_name: int
    module_name: str
    test_env: int
    status: int
    error_message: str | None = None
    video_path: str | None = None
    page_steps_result: list[PageStepsResultModel]