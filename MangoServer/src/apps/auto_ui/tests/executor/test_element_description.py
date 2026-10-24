from django.test import SimpleTestCase

from src.apps.auto_ui.services.element_description import (
    build_element_description,
    normalize_element_guidance,
)


class UiElementDescriptionTest(SimpleTestCase):
    def test_legacy_combined_description_is_split_before_executor_dispatch(self):
        positive, exclusion = normalize_element_guidance(
            None,
            '左侧弹出的字段选择菜单中的“收支类型”，不是右侧模板字段列表中的“收支类型”。',
        )

        self.assertEqual(positive, '左侧弹出的字段选择菜单中的“收支类型”')
        self.assertEqual(exclusion, '右侧模板字段列表中的“收支类型”')

    def test_structured_fields_are_combined_for_executor(self):
        description = build_element_description(
            name='订单类型名称输入框',
            category='创建弹窗',
            location_description='基础信息区域，附近有“父级类型”',
            surrounding_text='列表搜索框',
        )

        self.assertEqual(
            description,
            '元素名称：订单类型名称输入框\n'
            '元素分类：创建弹窗\n'
            '元素位置与周边文字：基础信息区域，附近有“父级类型”\n'
            '排除项：列表搜索框',
        )

    def test_legacy_prompt_remains_available(self):
        description = build_element_description(
            name='提交按钮',
            category='未分类',
            legacy_prompt='确认弹窗底部右侧',
        )

        self.assertEqual(description, '确认弹窗底部右侧')
