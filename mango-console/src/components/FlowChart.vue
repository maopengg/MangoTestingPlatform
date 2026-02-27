<template>
  <div class="flow-container">
    <!-- 左侧操作面板 -->
    <div class="left-panel">
      <a-card title="操作面板" :bordered="false">
        <!-- 拖拽面板 -->
        <div class="drag-panel">
          <div class="node-types">
            <div
              v-for="nodeType in nodeTypes"
              :key="nodeType.type"
              class="node-type-item"
              draggable="true"
              @dragstart="onDragStart($event, nodeType.type.toString())"
            >
              <span class="color-dot" :style="{ backgroundColor: nodeType.color }"></span>
              {{ nodeType.label }}
            </div>
          </div>
        </div>
      </a-card>
    </div>

    <!-- 中间流程图画布 -->
    <div class="center-panel">
      <div ref="canvasRef" class="flow-canvas" @drop="onDrop" @dragover="onDragOver">
        <!-- SVG 边渲染 -->
        <svg class="edges" xmlns="http://www.w3.org/2000/svg">
          <g>
            <!-- 使用path绘制直角连接线 -->
            <path
              v-for="edge in edges"
              :key="edge.id"
              :d="getRightAnglePath(edge)"
              fill="none"
              stroke="#999"
              stroke-width="2"
              stroke-dasharray="5,3"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <!-- 拖拽连线时的临时线条 -->
            <path
              v-if="isDraggingConnection && linkStartConnector"
              :d="getTempRightAnglePath()"
              fill="none"
              stroke="#999"
              stroke-width="2"
              stroke-dasharray="5,3"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </g>
        </svg>

        <!-- 连接线删除按钮 - 优化渲染 -->
        <template v-if="!readonly">
          <div
            v-for="edge in validEdges"
            :key="`delete-${edge.id}`"
            class="edge-delete-button"
            :style="{
              left: getEdgeMidpoint(edge).x - 8 + 'px',
              top: getEdgeMidpoint(edge).y - 8 + 'px',
            }"
            @click.stop="deleteEdge(edge)"
            @mouseenter="hoveredEdge = edge.id"
            @mouseleave="hoveredEdge = null"
          >
            ×
          </div>
        </template>

        <!-- 节点渲染 -->
        <div
          v-for="node in nodes"
          :key="node.id"
          class="node"
          :class="{
            active: selectedNode && selectedNode.id === node.id,
            linking: linkStartConnector && linkStartConnector.node_id === node.id,
          }"
          :style="{
            left: node.position.x + 'px',
            top: node.position.y + 'px',
            borderColor: getColor(node.type),
          }"
          @mousedown.stop="onNodeMouseDown($event, node)"
          @dragstart.prevent
          @click.stop="onNodeClick(node)"
        >
          <!-- 删除按钮 -->
          <div v-if="!readonly" class="delete-button" @click.stop="deleteNode(node)">×</div>

          <!-- 上方连接点 -->
          <div v-if="!readonly" class="connector-top">
            <div
              class="connector-point"
              @mousedown.stop="onConnectorMouseDown($event, node, 'top')"
              @mouseup.stop="onConnectorMouseUp($event, node, 'top')"
            ></div>
          </div>

          <div class="node-title">{{ node ? getNodeType(node) : '' }}</div>
          <div class="node-content">{{ node.label }}</div>

          <!-- 下方连接点 -->
          <div v-if="!readonly" class="connector-bottom">
            <div
              class="connector-point"
              @mousedown.stop="onConnectorMouseDown($event, node, 'bottom')"
              @mouseup.stop="onConnectorMouseUp($event, node, 'bottom')"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import type {
    Connector,
    ConnectorPosition,
    FlowData,
    Position,
    UIEdge,
    UINode,
  } from '@/types/components'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'

  const useSelectValue = useSelectValueStore()

  // Props
  interface Props {
    flowData?: FlowData
    readonly?: boolean
    allowDrop?: boolean
    tableData: any
    nodeTypes: Array<{ type: number; label: string; color: string }>
  }

  const props = withDefaults(defineProps<Props>(), {
    flowData: () => ({ nodes: [], edges: [] }),
    readonly: false,
    allowDrop: true,
    nodeTypes: () => [],
  })

  // Emits
  const emit = defineEmits<{
    nodeClick: [node: UINode]
    nodeSelect: [node: UINode | null]
    flowChange: [flowData: FlowData]
    edgeDelete: [edge: UIEdge]
    nodeDelete: [node: UINode]
  }>()

  // 画布 DOM
  const canvasRef = ref<HTMLElement | null>(null)

  // 画布数据 - 分离存储
  const nodes = ref<UINode[]>([])
  const edges = ref<UIEdge[]>([])
  const selectedNode = ref<UINode | null>(null)

  // 拖拽移动状态
  const draggingId = ref<string | null>(null)
  const dragOffset = ref<Position>({ x: 0, y: 0 })
  const wasDragging = ref(false)

  // 连线状态
  const linkStartConnector = ref<Connector | null>(null)
  const isDraggingConnection = ref(false)
  const dragConnectionEnd = ref<Position>({ x: 0, y: 0 })
  const hoveredEdge = ref<string | null>(null)

  // 监听props变化，更新内部数据
  watch(
    () => props.flowData,
    (newData) => {
      if (newData && newData.nodes && newData.edges) {
        // 使用 nextTick 确保 DOM 更新完成
        nextTick(() => {
          nodes.value = [...(newData.nodes || [])]
          edges.value = [...(newData.edges || [])]
        })
      }
    },
    { immediate: true, deep: true }
  )

  // 当内部数据变化时，触发事件
  let isInternalUpdate = false
  watch([() => nodes.value.length, () => edges.value.length], () => {
    if (!isInternalUpdate) {
      emit('flowChange', {
        nodes: [...nodes.value],
        edges: [...edges.value],
      })
    }
  })

  function getNodeType(data: UINode) {
    if (!data || !data.config || !props.tableData) {
      return ''
    }

    let result = ''
    props.tableData.forEach((item) => {
      if (item.id === data.config.id) {
        result = item.ele_name?.name
          ? item.ele_name?.name
          : useSelectValue.getSelectLabel(item.ope_key)
          ? useSelectValue.getSelectLabel(item.ope_key)
          : ''
      }
    })
    return result
  }

  // 使用节流函数优化数据变化通知
  let updateTimer: ReturnType<typeof setTimeout> | null = null
  const notifyDataChange = () => {
    if (updateTimer) {
      clearTimeout(updateTimer)
    }
    updateTimer = setTimeout(() => {
      emit('flowChange', {
        nodes: [...nodes.value],
        edges: [...edges.value],
      })
      updateTimer = null
    }, 16) // ~60fps
  }

  const getColor = (type: number) => {
    const nodeType = props.nodeTypes.find((nt: any) => nt.type === type)
    return nodeType ? nodeType.color : '#1677ff'
  }

  // 优化：计算属性缓存有效连接线
  const validEdges = computed(() => {
    return edges.value.filter((edge) => {
      const sourceNode = nodes.value.find((n) => n.id === edge.source.node_id)
      const targetNode = nodes.value.find((n) => n.id === edge.target.node_id)
      return sourceNode && targetNode
    })
  })

  // 判断节点类型
  const isDecisionNode = (type: number) => type === 4

  // 获取节点的连接数
  const getNodeConnections = (nodeId: string) => {
    const inputs = edges.value.filter((edge) => edge.target.node_id === nodeId)
    const outputs = edges.value.filter((edge) => edge.source.node_id === nodeId)
    return { inputs, outputs }
  }

  // 拖拽开始
  const onDragStart = (event: DragEvent, type: string) => {
    event.dataTransfer?.setData('application/mango-flow', type)
    event.dataTransfer!.effectAllowed = 'move'
  }

  // 允许放置
  const onDragOver = (event: DragEvent) => {
    if (!props.allowDrop || props.readonly) return
    event.preventDefault()
    event.dataTransfer!.dropEffect = 'move'
  }

  // 计算鼠标在画布内坐标（考虑滚动偏移）
  const getCanvasPosition = (clientX: number, clientY: number): Position => {
    const el = canvasRef.value!
    const rect = el.getBoundingClientRect()
    return { 
      x: clientX - rect.left + el.scrollLeft, 
      y: clientY - rect.top + el.scrollTop 
    }
  }

  // 限制节点位置在画布范围内
  const constrainPosition = (position: Position): Position => {
    const nodeWidth = 120
    const nodeHeight = 50
    const minX = 10
    const minY = 10
    const maxX = 3000 - nodeWidth - 10  // 画布宽度 - 节点宽度 - 边距
    const maxY = 2000 - nodeHeight - 10  // 画布高度 - 节点高度 - 边距

    return {
      x: Math.max(minX, Math.min(maxX, position.x)),
      y: Math.max(minY, Math.min(maxY, position.y))
    }
  }

  // 放置到画布：创建节点
  const onDrop = (event: DragEvent) => {
    if (!props.allowDrop || props.readonly) return
    event.preventDefault()
    const type = event.dataTransfer?.getData('application/mango-flow')
    if (!type) return

    const position = constrainPosition(getCanvasPosition(event.clientX, event.clientY))
    const id = `${type}-${Date.now()}`
    const nodeType = parseInt(type, 10)
    const nodeTypeInfo = props.nodeTypes.find((nt) => nt.type === nodeType)

    const newNode: UINode = {
      id,
      position,
      type: nodeType,
      label: nodeTypeInfo ? nodeTypeInfo.label : `${type} 节点`,
      config: {},
    }
    nodes.value = nodes.value.concat(newNode)
  }

  // 节点点击事件
  const onNodeClick = (node: UINode) => {
    if (!wasDragging.value) {
      selectedNode.value = node
      emit('nodeClick', node)
      emit('nodeSelect', node)
    }
  }

  // 节点鼠标按下：开始拖拽
  const onNodeMouseDown = (e: MouseEvent, node: UINode) => {
    if (props.readonly || e.button !== 0) return
    e.preventDefault()
    const start = getCanvasPosition(e.clientX, e.clientY)
    draggingId.value = node.id
    dragOffset.value = { x: start.x - node.position.x, y: start.y - node.position.y }
    wasDragging.value = false
  }

  // 节流优化的鼠标移动事件
  let mouseMoveTimer: number | null = null
  const throttledMouseMove = (e: MouseEvent) => {
    if (mouseMoveTimer) return

    mouseMoveTimer = requestAnimationFrame(() => {
      onMouseMove(e)
      mouseMoveTimer = null
    })
  }

  // 鼠标移动：更新拖拽节点坐标和连线位置
  const onMouseMove = (e: MouseEvent) => {
    if (props.readonly) return

    if (draggingId.value) {
      // 节点拖拽逻辑 - 使用requestAnimationFrame优化
      const pos = getCanvasPosition(e.clientX, e.clientY)
      const idx = nodes.value.findIndex((n) => n.id === draggingId.value)
      if (idx !== -1) {
        const currentNode = nodes.value[idx]
        let newX = pos.x - dragOffset.value.x
        let newY = pos.y - dragOffset.value.y

        // 限制节点在画布范围内
        const constrainedPos = constrainPosition({ x: newX, y: newY })
        newX = constrainedPos.x
        newY = constrainedPos.y

        // 只有位置真正改变时才更新
        if (
          Math.abs(newX - currentNode.position.x) > 1 ||
          Math.abs(newY - currentNode.position.y) > 1
        ) {
          wasDragging.value = true
          // 直接修改对象属性，避免创建新数组
          currentNode.position.x = newX
          currentNode.position.y = newY

          // 清理连接点位置缓存
          connectorPositionCache.delete(`${currentNode.id}-top`)
          connectorPositionCache.delete(`${currentNode.id}-bottom`)

          // 通知数据变化
          notifyDataChange()
        }
      }
    }

    if (isDraggingConnection.value) {
      // 连线拖拽逻辑 - 减少更新频率
      const pos = getCanvasPosition(e.clientX, e.clientY)
      dragConnectionEnd.value = pos
    }
  }

  // 鼠标抬起：结束拖拽
  const onMouseUp = () => {
    // 重置拖拽状态
    if (draggingId.value) {
      // 延迟重置wasDragging，确保点击事件能正确判断
      setTimeout(() => {
        wasDragging.value = false
      }, 10)
    }

    draggingId.value = null
    dragOffset.value = { x: 0, y: 0 }

    // 结束连线拖拽
    if (isDraggingConnection.value) {
      isDraggingConnection.value = false
      linkStartConnector.value = null
    }
  }

  onMounted(() => {
    window.addEventListener('mousemove', throttledMouseMove, { passive: true })
    window.addEventListener('mouseup', onMouseUp)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('mousemove', throttledMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
    if (mouseMoveTimer) {
      cancelAnimationFrame(mouseMoveTimer)
    }
    if (updateTimer) {
      clearTimeout(updateTimer)
    }
  })

  // 连接点鼠标按下：开始拖拽连线
  const onConnectorMouseDown = (e: MouseEvent, node: UINode, position: ConnectorPosition) => {
    if (props.readonly) return
    e.stopPropagation()
    e.preventDefault()

    const currentConnector: Connector = { node_id: node.id, position }
    linkStartConnector.value = currentConnector
    isDraggingConnection.value = true

    // 获取初始位置
    const startPos = getConnectorPosition(currentConnector)
    dragConnectionEnd.value = { x: startPos.x, y: startPos.y }
  }

  // 连接点鼠标抬起：处理连线
  const onConnectorMouseUp = (e: MouseEvent, node: UINode, position: ConnectorPosition) => {
    if (props.readonly) return
    e.stopPropagation()

    // 无论是否被判定为点击，都先结束拖拽，防止因事件冒泡被阻止导致粘连
    draggingId.value = null
    dragOffset.value = { x: 0, y: 0 }

    // 如果在拖拽连线状态，尝试创建连接
    if (isDraggingConnection.value && linkStartConnector.value) {
      const currentConnector: Connector = { node_id: node.id, position }

      // 不能连接到自己
      if (
        linkStartConnector.value.node_id !== node.id ||
        linkStartConnector.value.position !== position
      ) {
        if (isValidConnection(linkStartConnector.value, currentConnector)) {
          // 创建连线
          const edge: UIEdge = {
            id: `e-${Date.now()}`,
            source: linkStartConnector.value,
            target: currentConnector,
          }
          edges.value = edges.value.concat(edge)
        }
      }

      // 结束连线状态
      isDraggingConnection.value = false
      linkStartConnector.value = null
      return
    }

    if (wasDragging.value) {
      wasDragging.value = false
      return
    }

    const currentConnector: Connector = { node_id: node.id, position }

    if (!linkStartConnector.value) {
      // 设置起点
      linkStartConnector.value = currentConnector
    } else if (
      linkStartConnector.value.node_id === node.id &&
      linkStartConnector.value.position === position
    ) {
      // 点击同一个连接点，取消连线
      linkStartConnector.value = null
    } else {
      if (isValidConnection(linkStartConnector.value, currentConnector)) {
        // 创建连线
        const edge: UIEdge = {
          id: `e-${Date.now()}`,
          source: linkStartConnector.value,
          target: currentConnector,
        }
        edges.value = edges.value.concat(edge)
      }

      linkStartConnector.value = null
    }
  }

  // 验证连接是否有效
  const isValidConnection = (source: Connector, target: Connector): boolean => {
    const startNode = nodes.value.find((n) => n.id === source.node_id)
    const endNode = nodes.value.find((n) => n.id === target.node_id)
    if (!startNode || !endNode) return false

    const isStartDecision = isDecisionNode(startNode.type)
    const isEndDecision = isDecisionNode(endNode.type)

    // 获取起点和终点节点的当前连接情况
    const startConnections = getNodeConnections(source.node_id)
    const endConnections = getNodeConnections(target.node_id)

    // 检查连接是否有效
    let isValid = false
    let errorMessage = ''

    if (isStartDecision && isEndDecision) {
      // 判断节点之间不允许连接
      errorMessage = '判断类型节点之间不允许连接'
    } else if (isStartDecision) {
      // 起点是判断节点，终点是普通节点
      if (target.position === 'top' && endConnections.inputs.length > 0) {
        errorMessage = '普通节点最多只能有一个输入连接'
      } else if (target.position === 'bottom') {
        errorMessage = '普通节点只能从上方接收连接'
      } else {
        isValid = true
      }
    } else if (isEndDecision) {
      // 起点是普通节点，终点是判断节点
      if (source.position === 'bottom' && startConnections.outputs.length > 0) {
        errorMessage = '普通节点最多只能有一个输出连接'
      } else if (source.position === 'top') {
        errorMessage = '普通节点只能从下方发出连接'
      } else {
        isValid = true
      }
    } else {
      // 普通节点之间的连接
      if (source.position !== 'bottom' || target.position !== 'top') {
        errorMessage = '普通节点只能从上方接收连接，从下方发出连接'
      } else if (startConnections.outputs.length > 0) {
        errorMessage = '普通节点最多只能有一个输出连接'
      } else if (endConnections.inputs.length > 0) {
        errorMessage = '普通节点最多只能有一个输入连接'
      } else {
        isValid = true
      }
    }

    if (!isValid && errorMessage) {
      Message.warning(`连接无效：${errorMessage}`)
    }

    return isValid
  }

  // 优化：缓存连接点位置计算
  const connectorPositionCache = new Map<string, Position>()

  // 用于计算连接点坐标（供 SVG 使用）
  const getConnectorPosition = (connector: Connector): Position => {
    const cacheKey = `${connector.node_id}-${connector.position}`

    // 检查缓存
    if (connectorPositionCache.has(cacheKey)) {
      const cached = connectorPositionCache.get(cacheKey)!
      const node = nodes.value.find((n) => n.id === connector.node_id)
      if (node) {
        // 更新缓存位置
        const nodeWidth = 120
        const nodeHeight = 50
        const baseX = node.position.x
        const baseY = node.position.y

        let result: Position
        switch (connector.position) {
          case 'top':
            result = { x: baseX + nodeWidth / 2, y: baseY }
            break
          case 'bottom':
            result = { x: baseX + nodeWidth / 2, y: baseY + nodeHeight }
            break
          default:
            result = { x: baseX + nodeWidth / 2, y: baseY + nodeHeight / 2 }
        }

        connectorPositionCache.set(cacheKey, result)
        return result
      }
    }

    const node = nodes.value.find((n) => n.id === connector.node_id)
    if (!node) return { x: 0, y: 0 }

    const nodeWidth = 120
    const nodeHeight = 50

    // 基础位置（节点左上角）
    const baseX = node.position.x
    const baseY = node.position.y

    // 根据连接点位置计算坐标
    let result: Position
    switch (connector.position) {
      case 'top':
        result = { x: baseX + nodeWidth / 2, y: baseY }
        break
      case 'bottom':
        result = { x: baseX + nodeWidth / 2, y: baseY + nodeHeight }
        break
      default:
        result = { x: baseX + nodeWidth / 2, y: baseY + nodeHeight / 2 }
    }

    // 更新缓存
    connectorPositionCache.set(cacheKey, result)
    return result
  }

  // 计算90度直角连接线的SVG路径
  const getRightAnglePath = (edge: UIEdge): string => {
    const startPos = getConnectorPosition(edge.source)
    const endPos = getConnectorPosition(edge.target)

    // 计算两个节点X坐标的中间位置
    const midX = (startPos.x + endPos.x) / 2

    // 从起点垂直下降，然后在中间X位置水平移动，最后垂直连接到终点
    return `M ${startPos.x} ${startPos.y}
            L ${startPos.x} ${startPos.y + 20}
            L ${midX} ${startPos.y + 20}
            L ${midX} ${endPos.y - 20}
            L ${endPos.x} ${endPos.y - 20}
            L ${endPos.x} ${endPos.y}`
  }

  // 计算拖拽时临时连接线的SVG路径
  const getTempRightAnglePath = (): string => {
    if (!linkStartConnector.value) return ''

    const startPos = getConnectorPosition(linkStartConnector.value)
    const endPos = dragConnectionEnd.value

    // 计算两个位置X坐标的中间位置
    const midX = (startPos.x + endPos.x) / 2

    // 使用相同的路径算法
    return `M ${startPos.x} ${startPos.y}
            L ${startPos.x} ${startPos.y + 20}
            L ${midX} ${startPos.y + 20}
            L ${midX} ${endPos.y - 20}
            L ${endPos.x} ${endPos.y - 20}
            L ${endPos.x} ${endPos.y}`
  }

  // 计算连接线中点坐标（用于放置删除按钮）
  const getEdgeMidpoint = (edge: UIEdge): Position => {
    const startPos = getConnectorPosition(edge.source)
    const endPos = getConnectorPosition(edge.target)

    // 在中间的垂直线段上放置删除按钮
    const midX = (startPos.x + endPos.x) / 2
    const midY = startPos.y + (endPos.y - startPos.y) / 2

    return {
      x: midX,
      y: midY,
    }
  }

  // 删除连接线
  const deleteEdge = (edge: UIEdge) => {
    if (props.readonly) return
    edges.value = edges.value.filter((e) => e.id !== edge.id)
    emit('edgeDelete', edge)
  }

  // 删除节点及相关连线
  const deleteNode = (node: UINode) => {
    if (props.readonly) return

    // 删除与该节点相关的所有连接线
    edges.value = edges.value.filter(
      (edge) => edge.source.node_id !== node.id && edge.target.node_id !== node.id
    )

    // 如果正在连线且起点是该节点，取消连线状态
    if (linkStartConnector.value && linkStartConnector.value.node_id === node.id) {
      linkStartConnector.value = null
    }

    // 如果选中的是该节点，取消选中
    if (selectedNode.value && selectedNode.value.id === node.id) {
      selectedNode.value = null
      emit('nodeSelect', null)
    }

    // 删除节点
    nodes.value = nodes.value.filter((n) => n.id !== node.id)
    emit('nodeDelete', node)
  }

  // 暴露方法给父组件
  defineExpose({
    clearSelection: () => {
      selectedNode.value = null
      emit('nodeSelect', null)
    },
    selectNode: (nodeId: string) => {
      const node = nodes.value.find((n) => n.id === nodeId)
      if (node) {
        selectedNode.value = node
        emit('nodeSelect', node)
      }
    },
    getFlowData: () => ({
      nodes: [...nodes.value],
      edges: [...edges.value],
    }),
  })
</script>

<style scoped>
  .flow-container {
    display: flex;
    height: 100%;
    width: 100%;
    gap: 12px;
  }

  .left-panel {
    width: 220px;
    height: 100%;
    border: 1px solid #e5e6eb;
    border-radius: 4px;
    background: #fff;
  }

  .center-panel {
    flex: 1;
    height: 100%;
  }

  .drag-panel {
    padding: 0;
  }

  .node-types {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .node-type-item {
    display: flex;
    align-items: center;
    padding: 10px 12px;
    border: 1px solid #e5e6eb;
    border-radius: 4px;
    cursor: grab;
    transition: all 0.2s;
    background: #fff;
    font-size: 13px;
  }

  .node-type-item:hover {
    background: #f2f3f5;
    border-color: #165dff;
  }

  .node-type-item:active {
    cursor: grabbing;
  }

  .color-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 8px;
    flex-shrink: 0;
  }

  .flow-canvas {
    position: relative;
    width: 100%;
    height: 100%;
    border: 1px solid #e5e6eb;
    border-radius: 4px;
    overflow: auto;
    background-color: #fafbfc;
    background-image: 
      radial-gradient(circle, #e5e6eb 1px, transparent 1px);
    background-size: 20px 20px;
    min-height: 600px;
  }

  .flow-canvas::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  .flow-canvas::-webkit-scrollbar-track {
    background: #f7f8fa;
  }

  .flow-canvas::-webkit-scrollbar-thumb {
    background: #c9cdd4;
    border-radius: 4px;
  }

  .flow-canvas::-webkit-scrollbar-thumb:hover {
    background: #a9aeb8;
  }

  .edges {
    position: absolute;
    top: 0;
    left: 0;
    width: 3000px;
    height: 2000px;
    pointer-events: none;
  }

  .node {
    position: absolute;
    background: #fff;
    padding: 8px 10px;
    border: 2px solid #165dff;
    border-radius: 6px;
    width: 120px;
    height: 50px;
    cursor: grab;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    user-select: none;
    transition: all 0.2s;
    overflow: visible;
  }

  .node:hover {
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.12);
    height: auto;
    min-height: 50px;
    z-index: 100;
  }

  .node:active {
    cursor: grabbing;
  }

  .node.active {
    box-shadow: 0 0 0 3px rgba(22, 93, 255, 0.2);
    border-color: #0e42d2;
  }

  .node.linking {
    outline: 2px dashed #165dff;
    outline-offset: 2px;
  }

  .delete-button {
    position: absolute;
    top: -8px;
    right: -8px;
    width: 16px;
    height: 16px;
    background-color: #f53f3f;
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: bold;
    cursor: pointer;
    opacity: 0;
    transition: all 0.2s;
    z-index: 20;
    border: 2px solid white;
  }

  .node:hover .delete-button {
    opacity: 1;
  }

  .delete-button:hover {
    background-color: #cb272d;
    transform: scale(1.1);
  }

  .edge-delete-button {
    position: absolute;
    width: 16px;
    height: 16px;
    background-color: #f53f3f;
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: bold;
    cursor: pointer;
    opacity: 0.9;
    transition: all 0.2s;
    z-index: 30;
    border: 2px solid white;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  .edge-delete-button:hover {
    opacity: 1;
    transform: scale(1.15);
    background-color: #cb272d;
  }

  .connector-top,
  .connector-bottom {
    display: flex;
    justify-content: center;
    width: 100%;
    position: absolute;
    left: 0;
  }

  .connector-top {
    top: -7px;
  }

  .connector-bottom {
    bottom: -7px;
  }

  .connector-point {
    width: 14px;
    height: 14px;
    background-color: #fff;
    border: 3px solid #165dff;
    border-radius: 50%;
    cursor: pointer;
    z-index: 10;
    transition: all 0.2s;
  }

  .connector-point:hover {
    background-color: #165dff;
    transform: scale(1.2);
  }

  .node-title {
    font-weight: 600;
    margin-bottom: 3px;
    color: #1d2129;
    font-size: 13px;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
  }

  .node:hover .node-title {
    display: block;
    -webkit-line-clamp: unset;
    word-break: break-all;
  }

  .node-content {
    font-size: 11px;
    color: #4e5969;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
  }

  .node:hover .node-content {
    display: block;
    -webkit-line-clamp: unset;
    word-break: break-all;
  }
</style>
