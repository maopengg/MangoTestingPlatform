# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏
from mangokit.models import MysqlConingModel, ElementResultModel, ElementModel
from pydantic import BaseModel


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
    win_path: str | None = None
    win_title: str | None = None
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


class StepsDataModel(BaseModel):
    type: int
    ope_key: str | None = None
    page_step_details_id: int
    page_step_details_data: dict
    page_step_details_name: str | None = None


class PageStepsModel(BaseModel):
    id: int
    name: str
    project_product: int
    project_product_name: str
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
    parametrize: list[dict] | list
    steps: list[PageStepsModel]
    public_data_list: list[UiPublicModel] = []
    switch_step_open_url: bool = True


class PageStepsResultModel(BaseModel):
    id: int
    name: str
    type: int
    project_product_id: int
    project_product_name: str
    case_step_details_id: int | None = None

    cache_data: dict
    test_object: str
    equipment: EquipmentModel  # 设备名称或者浏览器类型

    status: int
    error_message: str | None = None
    element_result_list: list[ElementResultModel] = []


class UiCaseResultModel(BaseModel):
    id: int
    name: str
    project_product_id: int
    project_product_name: str
    module_name: str
    test_env: int
    status: int
    error_message: str | None = None
    video_path: str | None = None
    steps: list[PageStepsResultModel] = []


class GetTaskModel(BaseModel):
    username: str
