# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏

from typing import Any

from mangotools.models import MysqlConingModel, MethodModel
from pydantic import BaseModel


class Position(BaseModel):
    x: int
    y: int


class Connector(BaseModel):
    node_id: str
    position: str  # 只有 'top' | 'bottom' 两个类型，根据step_sort的排序来分上下


class UINode(BaseModel):
    id: str
    position: Position
    type: int
    label: str
    config: dict


class UIEdge(BaseModel):
    id: str
    source: Connector
    target: Connector


class FlowData(BaseModel):
    nodes: list[UINode]
    edges: list[UIEdge]  # 支持两种边格式


class ElementListModel(BaseModel):
    exp: int | None
    loc: str | None


class ElementModel(BaseModel):
    id: int
    type: int
    name: str | None
    elements: list[ElementListModel] = []
    sleep: int | None
    sub: int | None
    is_iframe: int | None
    ope_key: str | None
    ope_value: list[MethodModel] | None
    key_list: list | None = None
    sql: str | None = None
    key: str | None = None
    value: str | None = None
    if_actual: str | None = None


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
    page_step_details_data: dict
    page_step_details_name: str | None = None


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
    element_list: list[ElementModel] = []
    environment_config: EnvironmentConfigModel
    public_data_list: list[UiPublicModel] = []
    case_data: list[StepsDataModel] = []
    flow_data: FlowData | None


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
    test_object: str  # url或者软件包

    status: int
    error_message: str | None = None
    element_result_list: Any


class UiCaseResultModel(BaseModel):
    id: int
    name: str
    project_product_id: int
    project_product_name: str
    module_name: str
    test_env: int
    status: int
    test_time: str | None = None
    stop_time: str | None = None
    error_message: str | None = None
    video_path: str | None = None
    steps: list[PageStepsResultModel]
