# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏

from mangoautomation.models import ElementModel, ElementResultModel
from mangotools.models import MysqlConingModel
from pydantic import BaseModel


class UiPublicModel(BaseModel):
    type: int
    key: str
    value: str


class RecordingModel(BaseModel):
    url_list: list[dict]


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
    page_step_details_data: list | None = None
    page_step_details_name: str | None = None
    condition_value: dict | None = None


class PageStepsModel(BaseModel):
    id: int
    case_steps_id: int | None = None
    name: str
    project_product: int
    project_product_name: str
    module_name: str
    type: int
    url: str
    switch_step_open_url: bool
    error_retry: int | None = None
    element_list: list[ElementModel] | ElementModel = []
    environment_config: EnvironmentConfigModel
    public_data_list: list[UiPublicModel] = []
    case_data: list[StepsDataModel] = []
    flow_data: dict | None = None


class CaseModel(BaseModel):
    send_user: str
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


class PageStepsResultModel(BaseModel):
    id: int
    name: str
    type: int
    project_product_id: int
    project_product_name: str
    case_step_details_id: int | None = None
    test_time: str | None = None
    stop_time: str | None = None

    cache_data: dict
    test_object: str

    status: int
    error_message: str | None = None
    element_result_list: list[ElementResultModel] = []


class UiCaseResultModel(BaseModel):
    id: int
    name: str
    project_product_id: int
    project_product_name: str
    module_name: str
    test_time: str | None = None
    stop_time: str | None = None
    test_env: int
    status: int
    error_message: str | None = None
    video_path: str | None = None
    steps: list[PageStepsResultModel] = []
