<template>
  <div class="flow-page">
    <div class="flow-header">
      <div class="title">{{ title }}</div>
      <div class="actions">
        <a-button type="primary" status="success" size="small" @click="runFlow">运行</a-button>
        <a-button type="primary" size="small" @click="saveFlow">保存</a-button>
      </div>
    </div>

    <div class="flow-body">
      <!-- 左侧：15% 节点类型面板 -->
      <div class="palette">
        <a-card title="操作类型" :bordered="false">
          <div class="palette-list">
            <div
              v-for="item in paletteItems"
              :key="item.type"
              class="palette-item"
              draggable="true"
              @dragstart="onDragStart($event, item.type)"
            >
              <span class="dot" :style="{ backgroundColor: item.color }"></span>
              <span>{{ item.label }}</span>
            </div>
          </div>
        </a-card>
      </div>

      <!-- 中间：65% 画布（原生实现） -->
      <div ref="canvasRef" class="canvas" @drop="onDrop" @dragover="onDragOver">
        <!-- SVG 边渲染 -->
        <svg class="edges" xmlns="http://www.w3.org/2000/svg">
          <g>
            <line
              v-for="edge in edges"
              :key="edge.id"
              :x1="getConnectorPosition(edge.source).x"
              :y1="getConnectorPosition(edge.source).y"
              :x2="getConnectorPosition(edge.target).x"
              :y2="getConnectorPosition(edge.target).y"
              stroke="#999"
              stroke-width="2"
              stroke-dasharray="5,3"
            />
          </g>
          <!-- 不再需要箭头定义 -->
        </svg>

        <!-- 节点渲染 -->
        <div
          v-for="node in nodes"
          :key="node.id"
          class="node"
          :class="{
            active: selectedNode && selectedNode.id === node.id,
            linking: linkStartConnector && linkStartConnector.nodeId === node.id,
          }"
          :style="{
            left: node.position.x + 'px',
            top: node.position.y + 'px',
            borderColor: getColor(node.data.type),
          }"
          @mousedown.stop="onNodeMouseDown($event, node)"
          @dragstart.prevent
        >
          <!-- 删除按钮 -->
          <div class="delete-button" @click.stop="deleteNode(node)">×</div>
          <!-- 上方连接点 -->
          <div class="connector-top">
            <div
              class="connector-point"
              @mouseup.stop="onConnectorMouseUp($event, node, 'top')"
            ></div>
          </div>

          <div class="node-title">{{ node.data.label }}</div>
          <div class="node-type">{{ node.data.type }}</div>

          <!-- 下方连接点 -->
          <div class="connector-bottom">
            <div
              class="connector-point"
              @mouseup.stop="onConnectorMouseUp($event, node, 'bottom')"
            ></div>
          </div>
        </div>
      </div>

      <!-- 右侧：20% JSON 展示 -->
      <div class="details">
        <a-card title="详情" :bordered="false">
          <div v-if="selectedNode" class="json-box">
            <pre>{{ formattedSelected }}</pre>
          </div>
          <div v-else class="json-box placeholder"> 选择一个节点，在此查看 JSON 配置</div>
        </a-card>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
  import { Message } from '@arco-design/web-vue'

  type Position = { x: number; y: number }
  type NodeData = { type: string; label: string; config: Record<string, any> }
  type UINode = { id: string; position: Position; data: NodeData }
  type ConnectorPosition = 'top' | 'bottom'
  type Connector = { nodeId: string; position: ConnectorPosition }
  type UIEdge = { id: string; source: Connector; target: Connector }

  const title = ref('测试 Flow')

  // 画布 DOM
  const canvasRef = ref<HTMLElement | null>(null)

  // 画布数据
  const nodes = ref<UINode[]>([])
  const edges = ref<UIEdge[]>([])

  const selectedNode = ref<UINode | null>(null)

  // 拖拽移动状态
  const draggingId = ref<string | null>(null)
  const dragOffset = ref<Position>({ x: 0, y: 0 })
  const wasDragging = ref(false)

  // 连线状态：点击一次设为起点
  const linkStartConnector = ref<Connector | null>(null)

  // 左侧可拖拽的操作类型
  const paletteItems = ref([
    { type: 'element', label: '元素操作', color: '#52c41a' },
    { type: 'ass', label: '断言操作', color: '#1677ff' },
    { type: 'sql', label: 'SQL操作', color: '#fa8c16' },
    { type: 'if', label: '条件判断', color: '#722ed1' },
    { type: 'custom', label: '自定义变量', color: '#eb2f96' },
  ])

  const colorMap: Record<string, string> = {
    start: '#52c41a',
    http: '#1677ff',
    mysql: '#fa8c16',
    if: '#eb2f96',
    delay: '#722ed1',
    end: '#f5222d',
  }
  const getColor = (type: string) => colorMap[type] || '#1677ff'

  // 判断节点类型
  const isDecisionNode = (type: string) => type === 'if'

  // 获取节点的连接数
  const getNodeConnections = (nodeId: string) => {
    const inputs = edges.value.filter((edge) => edge.target.nodeId === nodeId)
    const outputs = edges.value.filter((edge) => edge.source.nodeId === nodeId)
    return { inputs, outputs }
  }

  // drag start：把类型放到 dataTransfer
  const onDragStart = (event: DragEvent, type: string) => {
    event.dataTransfer?.setData('application/mango-flow', type)
    event.dataTransfer!.effectAllowed = 'move'
  }

  // 允许放置
  const onDragOver = (event: DragEvent) => {
    event.preventDefault()
    event.dataTransfer!.dropEffect = 'move'
  }

  // 计算鼠标在画布内坐标
  const getCanvasPosition = (clientX: number, clientY: number): Position => {
    const el = canvasRef.value!
    const rect = el.getBoundingClientRect()
    return { x: clientX - rect.left, y: clientY - rect.top }
  }

  // 放置到画布：创建节点
  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    const type = event.dataTransfer?.getData('application/mango-flow')
    if (!type) return

    const position = getCanvasPosition(event.clientX, event.clientY)
    const id = `${type}-${Date.now()}`

    const newNode: UINode = {
      id,
      position,
      data: {
        type,
        label: `${type} 节点`,
        config: {},
      },
    }
    nodes.value = nodes.value.concat(newNode)
  }

  // 节点鼠标按下：开始拖拽
  const onNodeMouseDown = (e: MouseEvent, node: UINode) => {
    if (e.button !== 0) return
    e.preventDefault()
    const start = getCanvasPosition(e.clientX, e.clientY)
    draggingId.value = node.id
    dragOffset.value = { x: start.x - node.position.x, y: start.y - node.position.y }
    wasDragging.value = false
    selectedNode.value = node
  }

  // 鼠标移动：更新拖拽节点坐标
  const onMouseMove = (e: MouseEvent) => {
    if (!draggingId.value) return
    const pos = getCanvasPosition(e.clientX, e.clientY)
    const idx = nodes.value.findIndex((n) => n.id === draggingId.value)
    if (idx !== -1) {
      const next = { ...nodes.value[idx] }
      next.position = { x: pos.x - dragOffset.value.x, y: pos.y - dragOffset.value.y }
      if (
        Math.abs(next.position.x - nodes.value[idx].position.x) > 0 ||
        Math.abs(next.position.y - nodes.value[idx].position.y) > 0
      ) {
        wasDragging.value = true
      }
      nodes.value = nodes.value.slice(0, idx).concat(next, nodes.value.slice(idx + 1))
    }
  }

  // 鼠标抬起：结束拖拽
  const onMouseUp = () => {
    draggingId.value = null
    dragOffset.value = { x: 0, y: 0 }
  }

  onMounted(() => {
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  })

  // 连接点鼠标抬起：处理连线
  const onConnectorMouseUp = (e: MouseEvent, node: UINode, position: ConnectorPosition) => {
    e.stopPropagation()

    // 无论是否被判定为点击，都先结束拖拽，防止因事件冒泡被阻止导致粘连
    draggingId.value = null
    dragOffset.value = { x: 0, y: 0 }

    if (wasDragging.value) {
      wasDragging.value = false
      return
    }

    const currentConnector: Connector = { nodeId: node.id, position }

    if (!linkStartConnector.value) {
      // 设置起点
      linkStartConnector.value = currentConnector
    } else if (
      linkStartConnector.value.nodeId === node.id &&
      linkStartConnector.value.position === position
    ) {
      // 点击同一个连接点，取消连线
      linkStartConnector.value = null
    } else {
      // 检查连接限制
      const startNode = nodes.value.find((n) => n.id === linkStartConnector.value!.nodeId)
      const endNode = node

      // 判断节点可以有多个连接，普通节点只能上方输入下方输出
      const isStartDecision = startNode ? isDecisionNode(startNode.data.type) : false
      const isEndDecision = isDecisionNode(endNode.data.type)

      // 获取起点和终点节点的当前连接情况
      const startConnections = getNodeConnections(linkStartConnector.value.nodeId)
      const endConnections = getNodeConnections(endNode.id)

      // 检查连接是否有效
      let isValidConnection = false
      let errorMessage = ''

      if (isStartDecision && isEndDecision) {
        // 判断节点之间可以任意连接
        isValidConnection = true
      } else if (isStartDecision) {
        // 起点是判断节点，终点是普通节点
        // 普通节点的上方只能有一个输入
        if (position === 'top' && endConnections.inputs.length > 0) {
          isValidConnection = false
          errorMessage = '普通节点最多只能有一个输入连接'
        } else if (position === 'bottom') {
          isValidConnection = false
          errorMessage = '普通节点只能从上方接收连接'
        } else {
          isValidConnection = true
        }
      } else if (isEndDecision) {
        // 起点是普通节点，终点是判断节点
        // 普通节点的下方只能有一个输出
        if (linkStartConnector.value.position === 'bottom' && startConnections.outputs.length > 0) {
          isValidConnection = false
          errorMessage = '普通节点最多只能有一个输出连接'
        } else if (linkStartConnector.value.position === 'top') {
          isValidConnection = false
          errorMessage = '普通节点只能从下方发出连接'
        } else {
          isValidConnection = true
        }
      } else {
        // 普通节点之间的连接
        // 起点必须是下方连接点，终点必须是上方连接点
        // 且起点最多一个输出，终点最多一个输入
        if (linkStartConnector.value.position !== 'bottom' || position !== 'top') {
          isValidConnection = false
          errorMessage = '普通节点只能从上方接收连接，从下方发出连接'
        } else if (startConnections.outputs.length > 0) {
          isValidConnection = false
          errorMessage = '普通节点最多只能有一个输出连接'
        } else if (endConnections.inputs.length > 0) {
          isValidConnection = false
          errorMessage = '普通节点最多只能有一个输入连接'
        } else {
          isValidConnection = true
        }
      }

      if (isValidConnection) {
        // 创建连线
        const edge: UIEdge = {
          id: `e-${Date.now()}`,
          source: linkStartConnector.value,
          target: currentConnector,
        }
        edges.value = edges.value.concat(edge)
      } else {
        Message.warning(`连接无效：${errorMessage || '连接不符合规则'}`)
      }

      linkStartConnector.value = null
    }
  }

  // 用于计算连接点坐标（供 SVG 使用）
  const getConnectorPosition = (connector: Connector): Position => {
    const node = nodes.value.find((n) => n.id === connector.nodeId)
    if (!node) return { x: 0, y: 0 }

    const nodeWidth = 140
    const nodeHeight = 56

    // 基础位置（节点左上角）
    const baseX = node.position.x
    const baseY = node.position.y

    // 根据连接点位置计算坐标
    switch (connector.position) {
      case 'top':
        return { x: baseX + nodeWidth / 2, y: baseY }
      case 'bottom':
        return { x: baseX + nodeWidth / 2, y: baseY + nodeHeight }
      default:
        return { x: baseX + nodeWidth / 2, y: baseY + nodeHeight / 2 }
    }
  }

  const formattedSelected = computed(() => {
    return selectedNode.value
      ? JSON.stringify(
          {
            id: selectedNode.value.id,
            position: selectedNode.value.position,
            data: selectedNode.value.data,
          },
          null,
          2
        )
      : ''
  })

  // 运行：提示成功
  const runFlow = () => {
    Message.success('运行成功')
  }

  // 保存：打印整体数据结构（节点与边）
  const saveFlow = () => {
    const payload = {
      nodes: nodes.value,
      edges: edges.value,
    }
    // 打印到控制台
    // eslint-disable-next-line no-console
    console.log('Flow payload:', payload)
    Message.success('已保存（控制台查看数据结构）')
  }

  // 删除节点及相关连线
  const deleteNode = (node: UINode) => {
    // 删除与该节点相关的所有边
    edges.value = edges.value.filter(
      (edge) => edge.source.nodeId !== node.id && edge.target.nodeId !== node.id
    )

    // 如果正在连线且起点是该节点，取消连线状态
    if (linkStartConnector.value && linkStartConnector.value.nodeId === node.id) {
      linkStartConnector.value = null
    }

    // 如果选中的是该节点，取消选中
    if (selectedNode.value && selectedNode.value.id === node.id) {
      selectedNode.value = null
    }

    // 删除节点
    nodes.value = nodes.value.filter((n) => n.id !== node.id)

    Message.success('节点已删除')
  }
</script>

<style scoped>
  .flow-page {
    display: flex;
    flex-direction: column;
    height: 100vh;
    box-sizing: border-box;
    padding: 12px;
    gap: 12px;
  }

  .flow-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .title {
    font-size: 16px;
    font-weight: 600;
  }

  .actions {
    display: flex;
    gap: 8px;
  }

  .flow-body {
    flex: 1;
    display: flex;
    gap: 12px;
    min-height: 0;
  }

  .palette {
    width: 15%;
    min-width: 180px;
    max-width: 280px;
    height: 100%;
    overflow: auto;
  }

  .palette-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .palette-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border: 1px dashed var(--color-border-2, #e5e6eb);
    border-radius: 6px;
    cursor: grab;
    user-select: none;
    background: var(--color-bg-1, #fff);
  }

  .palette-item:active {
    cursor: grabbing;
  }

  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
  }

  .canvas {
    position: relative;
    flex: 1;
    height: 100%;
    min-width: 0;
    border: 1px solid var(--color-border-2, #e5e6eb);
    border-radius: 8px;
    overflow: hidden;
    background-image: linear-gradient(90deg, rgba(0, 0, 0, 0.04) 1px, transparent 0),
      linear-gradient(rgba(0, 0, 0, 0.04) 1px, transparent 0);
    background-size: 20px 20px;
  }

  .edges {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }

  .node {
    position: absolute;
    background: #fff;
    padding: 8px 10px;
    border: 2px solid #1677ff;
    border-radius: 8px;
    min-width: 140px;
    min-height: 56px;
    cursor: grab;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    user-select: none;
  }

  .node:active {
    cursor: grabbing;
  }

  .node.active {
    box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.2);
  }

  .node.linking {
    outline: 2px dashed #1677ff;
  }

  .delete-button {
    position: absolute;
    top: -8px;
    right: -8px;
    width: 16px;
    height: 16px;
    background-color: #f5222d;
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;
    z-index: 20;
  }

  .node:hover .delete-button {
    opacity: 1;
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
    top: -5px;
  }

  .connector-bottom {
    bottom: -5px;
  }

  .connector-point {
    width: 10px;
    height: 10px;
    background-color: #fff;
    border: 2px solid #1677ff;
    border-radius: 50%;
    cursor: pointer;
    z-index: 10;
  }

  .connector-point:hover {
    background-color: #1677ff;
  }

  .node-title {
    font-weight: 600;
    margin-bottom: 4px;
  }

  .node-type {
    font-size: 12px;
    color: #666;
  }

  .details {
    width: 20%;
    min-width: 220px;
    max-width: 420px;
    height: 100%;
    overflow: auto;
  }

  .json-box {
    height: calc(100vh - 160px);
    overflow: auto;
    background: var(--color-fill-1, #fafafa);
    padding: 10px;
    border-radius: 6px;
    border: 1px solid var(--color-border-2, #e5e6eb);
  }

  .json-box pre {
    margin: 0;
    font-size: 12px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .placeholder {
    color: var(--color-text-3, #999);
  }
</style>
