import json


def find_start_node(nodes, edges):
    """找到开始节点（没有入边的节点）"""
    target_nodes = set(edge['target']['node_id'] for edge in edges)
    start_nodes = [node for node in nodes if node['id'] not in target_nodes]
    return start_nodes[0] if start_nodes else None


def build_flow_graph(edges):
    """构建流程图的有向图结构"""
    graph = {}
    for edge in edges:
        source = edge['source']['node_id']
        target = edge['target']['node_id']
        if source not in graph:
            graph[source] = []
        graph[source].append(target)
    return graph


def get_node_by_id(nodes, node_id):
    """根据节点ID获取节点信息"""
    for node in nodes:
        if node['id'] == node_id:
            return node
    return None


def traverse_flow_sequential(nodes, edges):
    """顺序遍历流程图"""
    # 找到开始节点
    start_node = find_start_node(nodes, edges)
    if not start_node:
        print("未找到开始节点")
        return []

    # 构建图结构
    graph = build_flow_graph(edges)

    # 顺序遍历（广度优先）
    execution_order = []
    queue = [start_node['id']]
    visited = set()

    while queue:
        current_node_id = queue.pop(0)
        if current_node_id in visited:
            continue

        visited.add(current_node_id)
        current_node = get_node_by_id(nodes, current_node_id)
        execution_order.append(current_node)

        # 将子节点加入队列（保持顺序）
        if current_node_id in graph:
            for child_id in graph[current_node_id]:
                if child_id not in visited:
                    queue.append(child_id)

    return execution_order


def print_execution_order(execution_order):
    """打印执行顺序"""
    print("流程图执行顺序：")
    print("-" * 50)
    for i, node in enumerate(execution_order, 1):
        node_type_map = {
            0: "元素操作",
            4: "条件判断",
            5: "Python代码"
        }
        node_type = node_type_map.get(node['type'], f"未知类型({node['type']})")
        print(f"{i}. [{node_type}] {node['label']} (ID: {node['id']})")


# 你的数据
data = {
    "nodes": [
        {
            "id": "0-357c5ddf-f6a0-490b-b6ff-a04ef46788ba",
            "position": {"x": 48, "y": 21},
            "type": 0,
            "label": "元素操作",
            "config": {"id": 46}
        },
        {
            "id": "4-1758877208935",
            "position": {"x": 194, "y": 145},
            "type": 4,
            "label": "条件判断",
            "config": {"id": 48}
        },
        {
            "id": "0-1758877232846",
            "position": {"x": 85, "y": 281},
            "type": 0,
            "label": "元素操作",
            "config": {"id": 47}
        },
        {
            "id": "0-1758877263998",
            "position": {"x": 310, "y": 285},
            "type": 0,
            "label": "元素操作",
            "config": {"id": 49}
        },
        {
            "id": "4-1758877299623",
            "position": {"x": 454, "y": 419},
            "type": 4,
            "label": "条件判断",
            "config": {"id": 50}
        },
        {
            "id": "0-1758877325145",
            "position": {"x": 387, "y": 527},
            "type": 0,
            "label": "元素操作",
            "config": {"id": 51}
        },
        {
            "id": "0-1758877331837",
            "position": {"x": 566, "y": 532},
            "type": 0,
            "label": "元素操作",
            "config": {"id": 53}
        },
        {
            "id": "5-1758877496624",
            "position": {"x": 390, "y": 631},
            "type": 5,
            "label": "python代码",
            "config": {"id": 54}
        }
    ],
    "edges": [
        {
            "id": "e-1758877212250",
            "source": {"node_id": "0-357c5ddf-f6a0-490b-b6ff-a04ef46788ba", "position": "bottom"},
            "target": {"node_id": "4-1758877208935", "position": "top"}
        },
        {
            "id": "e-1758877236759",
            "source": {"node_id": "4-1758877208935", "position": "bottom"},
            "target": {"node_id": "0-1758877232846", "position": "top"}
        },
        {
            "id": "e-1758877269365",
            "source": {"node_id": "4-1758877208935", "position": "bottom"},
            "target": {"node_id": "0-1758877263998", "position": "top"}
        },
        {
            "id": "e-1758877302216",
            "source": {"node_id": "0-1758877263998", "position": "bottom"},
            "target": {"node_id": "4-1758877299623", "position": "top"}
        },
        {
            "id": "e-1758877327722",
            "source": {"node_id": "4-1758877299623", "position": "bottom"},
            "target": {"node_id": "0-1758877325145", "position": "top"}
        },
        {
            "id": "e-1758877336648",
            "source": {"node_id": "4-1758877299623", "position": "bottom"},
            "target": {"node_id": "0-1758877331837", "position": "top"}
        },
        {
            "id": "e-1758877500256",
            "source": {"node_id": "0-1758877325145", "position": "bottom"},
            "target": {"node_id": "5-1758877496624", "position": "top"}
        }
    ]
}

# 执行顺序遍历
execution_order = traverse_flow_sequential(data['nodes'], data['edges'])

# 打印结果
print_execution_order(execution_order)
