# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-08-31 下午8:41
# @Author : 毛鹏
from pydantic import BaseModel

from src.enums.gui_enum import InputEnum


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
    orange: str


class LeftMenuModel(BaseModel):
    btn_icon: str
    btn_id: str
    btn_text: str
    btn_tooltip: str
    show_top: bool
    is_active: bool
    is_active: bool
    submenus: list['LeftMenuModel'] = []


class TitleBarMenusModel(BaseModel):
    btn_icon: str
    btn_id: str
    btn_tooltip: str
    is_active: bool


class MenusModel(BaseModel):
    left_menus: list[LeftMenuModel]
    title_bar_menus: list[TitleBarMenusModel]


class TitleDataModel(BaseModel):
    title: str
    placeholder: str
    key: str
    input: None = None
    # input: MangoLineEdit | None = None


class FormDataModel(BaseModel):
    title: str
    placeholder: str
    key: str
    input: None = None
    # input: MangoLineEdit | None = None
    text: str | None = None
    type: InputEnum
    select: dict | list[dict] | None = None
    subordinate: str | None = None


class TableColumnModel(BaseModel):
    key: str
    name: str
    item: str


class TableMenuItemModel(BaseModel):
    name: str
    action: str
    son: list['TableMenuItemModel'] = []


class FieldListModel(BaseModel):
    key: str
    name: str


class CascaderModel(BaseModel):
    value: int
    label: str
    children: list['CascaderModel'] = []


if __name__ == '__main__':
    data = [CascaderModel(**i) for i in [{'value': 3, 'label': '演示项目',
                                          'children': [{'value': 13, 'label': '测试项目百度', 'children': []},
                                                       {'value': 12, 'label': '多少度', 'children': []},
                                                       {'value': 11, 'label': 'arco（组件库）',
                                                        'children': [{'value': 35, 'label': '气泡确认框'},
                                                                     {'value': 34, 'label': '通知提醒框'},
                                                                     {'value': 33, 'label': '对话框'},
                                                                     {'value': 32, 'label': '全局提示'},
                                                                     {'value': 31, 'label': '上传'},
                                                                     {'value': 30, 'label': '树选择'},
                                                                     {'value': 29, 'label': '数据穿梭框'},
                                                                     {'value': 28, 'label': '时间选择器'},
                                                                     {'value': 27, 'label': '文本域'},
                                                                     {'value': 26, 'label': '开关'},
                                                                     {'value': 25, 'label': '滑动输入条'},
                                                                     {'value': 24, 'label': '选择器'},
                                                                     {'value': 23, 'label': '评分'},
                                                                     {'value': 22, 'label': '单选框'},
                                                                     {'value': 21, 'label': '标签输入框'},
                                                                     {'value': 20, 'label': '验证码输入框'},
                                                                     {'value': 19, 'label': '数字输入框'},
                                                                     {'value': 18, 'label': '输入框'},
                                                                     {'value': 17, 'label': '表单'},
                                                                     {'value': 16, 'label': '日期选择器'},
                                                                     {'value': 15, 'label': '颜色选择器'},
                                                                     {'value': 14, 'label': '复选框'},
                                                                     {'value': 13, 'label': '级联选择'},
                                                                     {'value': 12, 'label': '自动补全'},
                                                                     {'value': 11, 'label': '首页title'}]},
                                                       {'value': 3, 'label': '百度',
                                                        'children': [{'value': 3, 'label': '首页'}]},
                                                       {'value': 2, 'label': '微信',
                                                        'children': [{'value': 2, 'label': '首页'}]},
                                                       {'value': 1, 'label': '玩安卓',
                                                        'children': [{'value': 1, 'label': '首页'}]}]}]]
    print(data)
