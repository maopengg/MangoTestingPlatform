# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-24 11:36
# @Author : 毛鹏
import json
import uuid

from mangotools.mangos import get_execution_order_with_config_ids

from src.auto_test.auto_system.models import CacheData
from src.auto_test.auto_ui.models import PageStepsDetailed, PageSteps, UiCaseStepsDetailed
from src.enums.ui_enum import ElementOperationEnum
from src.models.ui_model import *

node_types = {0: '元素操作',
              1: '断言操作',
              2: 'SQL操作',
              3: '自定义变量',
              4: '条件判断'}


def get_parameter_by_value(data, target_value):
    def search_recursive(items):
        for item in items:
            # 如果当前节点有value且匹配目标值，并且有parameter，则返回
            if item.get('value') == target_value and 'parameter' in item:
                return item['parameter']

            # 如果有children，递归搜索
            if 'children' in item:
                result = search_recursive(item['children'])
                if result is not None:
                    return result

            # 检查children中的子项
            if 'children' in item:
                for child in item['children']:
                    if child.get('value') == target_value and 'parameter' in child:
                        return child['parameter']

        return None

    return search_recursive(data)


def page_steps():
    page_steps_obj = PageSteps.objects.all()
    updated_count = 0

    for page_step in page_steps_obj:
        nodes = []
        edges = []

        # 获取该页面步骤下的所有详情步骤，按step_sort排序
        step_details = PageStepsDetailed.objects.filter(page_step=page_step.id).order_by('step_sort')

        if not step_details.exists():
            continue

        # 生成节点
        node_spacing_y = 120  # 节点间垂直间距
        start_x = 300  # 起始X坐标
        start_y = 100  # 起始Y坐标

        previous_node_id = None

        for index, step_detail in enumerate(step_details):
            node_id = f'{step_detail.type}-{uuid.uuid4()}'

            # 计算节点位置：垂直排列
            node_position = Position(
                x=start_x,
                y=start_y + (index * node_spacing_y)
            )

            # 创建节点
            node = UINode(
                id=node_id,
                position=node_position,
                type=step_detail.type,
                label=node_types.get(step_detail.type, '未知操作'),
                config={'id': step_detail.id}
            )
            nodes.append(node)

            # 创建边：连接当前节点与前一个节点
            if previous_node_id is not None:
                # 第一种边格式：使用node_id
                edge_id = f'e-{uuid.uuid4()}'
                edge = UIEdge(
                    id=edge_id,
                    source=Connector(
                        node_id=previous_node_id,
                        position='bottom'
                    ),
                    target=Connector(
                        node_id=node_id,
                        position='top'
                    )
                )
                edges.append(edge)

            previous_node_id = node_id

        # 将生成的flow数据保存到数据库
        flow_data = FlowData(nodes=nodes, edges=edges)
        page_step.flow_data = flow_data.dict()
        page_step.save()

        updated_count += 1
        print(f"更新页面步骤 {page_step.name} (ID: {page_step.id})，包含 {len(nodes)} 个节点，{len(edges)} 条边")

    print(f"\n数据更新完成！共更新了 {updated_count} 个页面步骤。")


def page_steps_detailed():
    select_value = json.loads(CacheData.objects.get(key='select_value').value)
    for i in PageStepsDetailed.objects.all():
        print(f'开始更新步骤明细：{i.id}')
        if i.ope_key:
            ope_value = get_parameter_by_value(select_value, i.ope_key)
            try:
                if i.ope_value:
                    for e in ope_value:
                        for q in i.ope_value:
                            if e.get('f') == q.get('f'):
                                e['v'] = q['v']
            except TypeError:
                print(321321, i.id, i.page_step.name, i.ope_key, ope_value, i.ope_value)
            i.ope_value = ope_value
            i.save()
        if i.type == ElementOperationEnum.SQL.value:
            i.sql_execute = [{'sql': i.sql, 'key_list': i.key_list}]
            i.save()
        if i.type == ElementOperationEnum.CUSTOM.value:
            i.custom = [{'key': i.key, 'value': i.value}]
            i.save()


def case_steps_detailed():
    for books in UiCaseStepsDetailed.objects.all():
        print(f'开始更新用例明细明细：{books.id}')
        if books.page_step.flow_data == {}:
            continue
        flow_list = get_execution_order_with_config_ids(books.page_step.flow_data)
        case_data_list = []
        for _id in flow_list:
            try:
                steps_detailed = PageStepsDetailed.objects.get(id=_id)
                steps_data_model = StepsDataModel(
                    type=steps_detailed.type,
                    ope_key=steps_detailed.ope_key,
                    page_step_details_id=steps_detailed.id,
                    page_step_details_name=steps_detailed.ele_name.name if steps_detailed.ele_name else None
                )
                page_step_details_data = []
                if steps_detailed.type == ElementOperationEnum.OPE.value or ElementOperationEnum.ASS.value:
                    if steps_detailed.ope_value:
                        page_step_details_data = steps_detailed.ope_value
                    for i in page_step_details_data:
                        for b in books.case_data:
                            data = b.get('page_step_details_data')
                            if isinstance(data, dict):
                                if data.get(i['f']):
                                    i['v'] = data.get(i['f'])
                            elif isinstance(data, list):
                                for d in data:
                                    if d.get('f') == i['f']:
                                        i['v'] = d.get('v')
                elif steps_detailed.type == ElementOperationEnum.SQL.value:
                    page_step_details_data = steps_detailed.sql_execute
                elif steps_detailed.type == ElementOperationEnum.CUSTOM.value:
                    page_step_details_data = steps_detailed.custom
                elif steps_detailed.type == ElementOperationEnum.CONDITION.value:
                    page_step_details_data = [steps_detailed.condition_value]
                elif steps_detailed.type == ElementOperationEnum.PYTHON_CODE.value:
                    page_step_details_data = [{'func': steps_detailed.func}]
                steps_data_model.page_step_details_data = page_step_details_data
                case_data_list.append(steps_data_model.model_dump())
                print(case_data_list)
            except PageStepsDetailed.DoesNotExist:
                print(books.page_step_id)
        books.case_data = case_data_list if case_data_list else None
        books.save()


def main_5_8():
    print("开始执行页面步骤数据迁移...")
    print("-" * 50)

    try:
        page_steps()
        page_steps_detailed()
        case_steps_detailed()
        print("\n数据迁移成功完成！")
    except Exception as e:
        print(f"\n数据迁移失败: {str(e)}")
        raise e
