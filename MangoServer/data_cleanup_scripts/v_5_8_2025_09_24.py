# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-24 11:36
# @Author : 毛鹏
import uuid

from src.auto_test.auto_ui.models import PageStepsDetailed, PageSteps

node_types = {0: '元素操作',
              1: '断言操作',
              2: 'SQL操作',
              3: '自定义变量',
              4: '条件判断'}


def page_steps_detailed():
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


def main_5_8():
    print("开始执行页面步骤数据迁移...")
    print("将表格格式的步骤数据转换为vue-flow格式")
    print("-" * 50)

    try:
        page_steps_detailed()
        print("\n✅ 数据迁移成功完成！")
    except Exception as e:
        print(f"\n❌ 数据迁移失败: {str(e)}")
        raise e
