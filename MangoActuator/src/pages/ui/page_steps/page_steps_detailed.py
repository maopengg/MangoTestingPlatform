# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
import asyncio
import json

from mango_ui import *

from src.enums.ui_enum import DriveTypeEnum
from src.models.api_model import ResponseModel
from src.models.ui_model import PageStepsModel, ElementResultModel, PageObject
from src.models.user_model import UserModel
from src.services.ui.service.page_steps import PageSteps
from src.tools.get_class_methods import GetClassMethod
from .page_steps_detailed_dict import *
from ...parent.sub import SubPage


class PageStepsDetailedPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent,
                         field_list=field_list,
                         form_data=form_data,
                         right_data=right_data)
        self.id_key = 'page_step'
        self.superior_page = 'page_steps'
        self.get = HTTP.get_page_steps_detailed
        self.post = HTTP.post_page_steps_detailed
        self.put = HTTP.put_page_steps_detailed
        self._delete = HTTP.delete_page_steps_detailed
        self.h_layout = QHBoxLayout()
        self.table_column = [TableColumnModel(**i) for i in table_column]
        self.table_menu = [TableMenuItemModel(**i) for i in table_menu]
        self.table_widget = TableList(self.table_column, self.table_menu, )
        self.table_widget.pagination.click.connect(self.pagination_clicked)
        self.table_widget.clicked.connect(self.callback)
        self.h_layout.addWidget(self.table_widget, 6)
        self.v_layout = QVBoxLayout()
        self.v_layout.addWidget(MangoLabel('调试元素信息展示'))
        self.scroll_area = MangoScrollArea()

        self.v_layout.addWidget(self.scroll_area)
        self.h_layout.addLayout(self.v_layout, 4)
        self.layout.addLayout(self.h_layout)

        self.eoe_type = None
        self.select_data = None

    def update_card(self, ele_model: ElementResultModel):
        layout = QGridLayout()
        card = MangoCard(layout)
        labels = [
            f"元素名称: {ele_model.ele_name}",
            f"元素数量: {ele_model.ele_quantity}",
            f"测试结果: {'成功' if ele_model.status else '失败'}",
        ]

        if ele_model.type == ElementOperationEnum.OPE.value:
            labels.append(f"操作类型: {ele_model.ope_key}")
        elif ele_model.type == ElementOperationEnum.ASS.value:
            labels.append(f"断言类型: {ele_model.ope_key}")
            labels.append(f"预期值: {ele_model.expect}")
            labels.append(f"实际值: {ele_model.actual}")
        elif ele_model.type == ElementOperationEnum.SQL.value:
            labels.append(f"sql_key: {ele_model.key_list}")
            labels.append(f"sql语句: {ele_model.sql}")
        elif ele_model.type == ElementOperationEnum.CUSTOM.value:
            labels.append(f"参数key: {ele_model.key}")
            labels.append(f"参数value: {ele_model.value}")

        labels.append(f"元素表达式: {ele_model.loc}")
        if ele_model.status == StatusEnum.FAIL.value:
            labels.append(f"失败提示：{ele_model.error_message}")
            labels.append(f"失败截图: {ele_model.picture_path}")

        # 添加3行3列的数据
        for row in range(3):
            for col in range(3):
                index = row * 3 + col
                try:
                    layout.addWidget(MangoLabel(labels[index]), row, col)  # 将标签添加到布局中
                except IndexError:
                    pass
        self.scroll_area.layout.addWidget(card)

    def debug(self):
        user_info = UserModel()
        response_model: ResponseModel = HTTP.ui_steps_run(user_info.selected_environment, self.data.get("id"), 0)
        response_message(self, response_model)
        if PageObject.page_steps is None:
            PageObject.page_steps = PageSteps()
            PageObject.page_steps.progress.connect(self.update_card)
        data = PageStepsModel(**response_model.data)
        # if settings.IS_DEBUG:
        #     with open(fr'{InitPath.logs_dir}\test.json', 'w', encoding='utf-8') as f:
        #         f.write(data.model_dump_json(indent=2))
        asyncio.run_coroutine_threadsafe(
            PageObject.page_steps.page_steps_mian(data), self.parent.loop)

    def save_callback(self, data):
        data['step_sort'] = len(self.table_widget.table_widget.data)
        data['ope_value'] = json.loads(data.get('ope_value')) if data.get('ope_value') else None
        response_model: ResponseModel = self.post(data)
        response_message(self, response_model)

    def form_data_callback(self, obj: FormDataModel):
        select = obj.select(self.data['page']['id']).data
        return [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in select]

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        if data.subordinate == 'ope_key':
            auto_type = self.data.get('project_product').get('auto_type')
            self.eoe_type = data.value
            if data.value == ElementOperationEnum.OPE.value:
                if auto_type == DriveTypeEnum.WEB.value:
                    self.select_data = [CascaderModel(**i) for i in GetClassMethod().get_web()]
                elif auto_type == DriveTypeEnum.ANDROID.value:
                    self.select_data = [CascaderModel(**i) for i in GetClassMethod().get_android()]
                else:
                    self.select_data = [CascaderModel(**i) for i in GetClassMethod().get_web()]
                if data.subordinate_input_object:
                    data.subordinate_input_object.set_select(self.select_data, True)
                return self.select_data
            elif data.value == ElementOperationEnum.ASS.value:
                if auto_type == DriveTypeEnum.WEB.value:
                    self.select_data = [CascaderModel(**i) for i in GetClassMethod().get_web_ass()]
                elif auto_type == DriveTypeEnum.ANDROID.value:
                    self.select_data = [CascaderModel(**i) for i in GetClassMethod().get_android_ass()]
                else:
                    self.select_data = [CascaderModel(**i) for i in GetClassMethod().get_public_ass()]
                for i in GetClassMethod().get_public_ass():
                    self.select_data.append(CascaderModel(**i))
                if data.subordinate_input_object:
                    data.subordinate_input_object.set_select(self.select_data, True)
                return self.select_data
            else:
                if data.subordinate_input_object:
                    data.subordinate_input_object.set_text('请忽略此选项')
        elif data.subordinate == 'ope_value':
            data.subordinate_input_object \
                .set_value(json.dumps(self.find_parameter_by_value(self.select_data, data.value)))

    @classmethod
    def find_parameter_by_value(cls, data: list[CascaderModel], target_value):
        for item in data:
            if item.value == target_value:
                return item.parameter
            if item.children:
                result = cls.find_parameter_by_value(item.children, target_value)
                if result is not None:
                    return result
        return None  # 如果没有找到
