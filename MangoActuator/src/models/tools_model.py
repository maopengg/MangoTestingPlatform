# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-20 14:19
# @Author : 毛鹏
from pydantic import BaseModel


class MysqlConingModel(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str | None


class EmailNoticeModel(BaseModel):
    send_user: str
    email_host: str
    stamp_key: str
    send_list: list


class TestReportModel(BaseModel):
    test_suite_id: int
    project_id: int
    project_name: str
    test_environment: str
    case_sum: int
    success: int
    success_rate: float
    warning: int
    fail: int
    execution_duration: int
    test_time: str


class Font(BaseModel):
    family: str
    title_size: int
    text_size: int


class LeftMenuSize(BaseModel):
    minimum: int
    maximum: int


class ColumnSize(BaseModel):
    minimum: int
    maximum: int


class AppConfig(BaseModel):
    app_name: str
    version: str
    copyright: str
    year: int
    theme_name: str
    custom_title_bar: bool
    startup_size: list[int]
    minimum_size: list[int]
    lef_menu_size: LeftMenuSize
    left_menu_content_margins: int
    left_column_size: ColumnSize
    right_column_size: ColumnSize
    time_animation: int
    font: Font


class ThemeConfig(BaseModel):
    theme_name: str
    dark_one: str
    dark_two: str
    dark_three: str
    dark_four: str
    bg_one: str
    bg_two: str
    bg_three: str
    icon_color: str
    icon_hover: str
    icon_pressed: str
    icon_active: str
    context_color: str
    context_hover: str
    context_pressed: str
    text_title: str
    text_foreground: str
    text_description: str
    text_active: str
    white: str
    pink: str
    green: str
    red: str
    yellow: str
    blue: str
