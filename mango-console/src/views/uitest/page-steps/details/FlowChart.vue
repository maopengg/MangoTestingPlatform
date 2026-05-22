<template>
  <div class="flow-container">
    <div class="left-panel">
      <div class="flow-panel-head">
        <div class="flow-panel-title">操作面板</div>
        <div class="flow-panel-subtitle">拖入节点类型</div>
      </div>
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
    </div>

    <div class="center-panel">
      <div class="flow-panel-head center-panel-head">
        <div>
          <div class="flow-panel-title">流程画布</div>
          <div class="flow-panel-subtitle">从左侧拖入节点，连接执行顺序后保存画布</div>
        </div>
        <div class="flow-stats">
          <span v-if="flowIssueSummary.unsaved" class="flow-stat-issue">
            未保存 {{ flowIssueSummary.unsaved }}
          </span>
          <span v-if="flowIssueSummary.isolated" class="flow-stat-issue">
            未连接 {{ flowIssueSummary.isolated }}
          </span>
          <span v-if="flowIssueSummary.decisionIncomplete" class="flow-stat-issue">
            判断待连 {{ flowIssueSummary.decisionIncomplete }}
          </span>
          <span>节点 {{ flowNodes.length }}</span>
          <span>连线 {{ flowEdges.length }}</span>
          <span>步骤 {{ tableData?.length || 0 }}</span>
        </div>
      </div>
      <div class="flow-canvas" @drop="onDrop" @dragover="onDragOver">
        <div v-if="!flowNodes.length" class="flow-empty">
          <div class="flow-empty-title">从左侧拖入节点开始编排</div>
          <div class="flow-empty-desc">新增节点后先保存配置，再连接步骤顺序并保存画布。</div>
        </div>
        <VueFlow
          :id="flowId"
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          class="ui-step-flow"
          :nodes-draggable="!readonly"
          :nodes-connectable="!readonly"
          :elements-selectable="true"
          :delete-key-code="null"
          :min-zoom="0.25"
          :max-zoom="1.2"
          @connect="onConnect"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @node-drag-stop="onNodeDragStop"
        >
          <template #node-uiStepNode="{ id, data, selected }">
            <a-popover
              position="right"
              :popup-visible="activePopoverNodeId === id"
              content-class="step-node-popover"
            >
              <div
                :class="[
                  'step-node',
                  `step-node-${getNodeStatus(id)}`,
                  { 'step-node-selected': selected },
                ]"
                :style="{ '--node-color': data.color }"
                @mouseenter="startNodePopoverTimer(id)"
                @mousemove="restartNodePopoverTimer(id)"
                @mouseleave="hideNodePopover(id)"
              >
                <Handle
                  id="top"
                  type="target"
                  :position="FlowPosition.Top"
                  :connectable="!readonly"
                  class="step-handle step-handle-top"
                />
                <button
                  v-if="!readonly"
                  class="node-delete"
                  type="button"
                  title="删除节点"
                  @click.stop="deleteNodeById(id)"
                >
                  ×
                </button>
                <div class="node-main">
                  <div class="node-kicker">
                    <span>{{ data.label }}</span>
                    <span class="node-status-text">{{ getNodeStatusText(id) }}</span>
                  </div>
                  <div class="node-title" :title="getNodeTitle(id)">
                    {{ getNodeTitle(id) }}
                  </div>
                  <div class="node-content" :title="getNodeLocator(id)">
                    <span>{{ getNodeOperation(id) }}</span>
                    <span v-if="getNodeLocator(id)" class="node-locator">
                      {{ getNodeLocator(id) }}
                    </span>
                  </div>
                </div>
                <Handle
                  id="bottom"
                  type="source"
                  :position="FlowPosition.Bottom"
                  :connectable="!readonly"
                  class="step-handle step-handle-bottom"
                />
              </div>
              <template #content>
                <div class="node-popover">
                  <div class="node-popover-title">{{ getNodeTitle(id) }}</div>
                  <div
                    v-for="section in getNodeInfoSections(id)"
                    :key="section.title"
                    class="node-popover-section"
                  >
                    <div class="node-popover-section-title">{{ section.title }}</div>
                    <div v-for="row in section.rows" :key="row.label" class="node-popover-row">
                      <span class="node-popover-key">{{ row.label }}</span>
                      <pre
                        v-if="row.multiline"
                        class="node-popover-value node-popover-value-code"
                        >{{ row.value }}</pre
                      >
                      <span v-else class="node-popover-value" :title="row.value">
                        {{ row.value }}
                      </span>
                    </div>
                  </div>
                </div>
              </template>
            </a-popover>
          </template>
          <Background pattern-color="var(--m-border)" :gap="18" />
          <MiniMap pannable zoomable class="flow-minimap" />
          <Controls />
        </VueFlow>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { VueFlow, Handle, Position as FlowPosition, useVueFlow } from '@vue-flow/core'
  import type {
    Connection,
    Edge,
    Node,
    NodeDragEvent,
    NodeMouseEvent,
    EdgeMouseEvent,
  } from '@vue-flow/core'
  import { Background, Controls, MiniMap } from '@vue-flow/additional-components'
  import '@vue-flow/core/dist/style.css'
  import '@vue-flow/core/dist/theme-default.css'
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

  interface Props {
    flowData?: FlowData
    readonly?: boolean
    allowDrop?: boolean
    tableData: any[]
    nodeTypes: Array<{ type: number; label: string; color: string }>
  }

  const props = withDefaults(defineProps<Props>(), {
    flowData: () => ({ nodes: [], edges: [] }),
    readonly: false,
    allowDrop: true,
    tableData: () => [],
    nodeTypes: () => [],
  })

  const emit = defineEmits<{
    nodeClick: [node: UINode]
    nodeSelect: [node: UINode | null]
    flowChange: [flowData: FlowData]
    edgeDelete: [edge: UIEdge]
    nodeDelete: [node: UINode]
  }>()

  const NODE_WIDTH = 184
  const NODE_HEIGHT = 76
  const INITIAL_MAX_ZOOM = 0.85
  const flowId = `ui-step-flow-${Math.random().toString(36).slice(2)}`
  const flowNodes = ref<Node[]>([])
  const flowEdges = ref<Edge[]>([])
  const selectedNodeId = ref('')
  const activePopoverNodeId = ref('')
  const lastEmittedSignature = ref('')
  let popoverTimer: ReturnType<typeof setTimeout> | null = null
  let syncingFromProps = false

  const { fitView, screenToFlowCoordinate } = useVueFlow(flowId)

  const legacyNodes = computed<UINode[]>(() => flowNodes.value.map(toLegacyNode))
  const legacyEdges = computed<UIEdge[]>(() => flowEdges.value.map(toLegacyEdge))
  const legacyFlowData = computed<FlowData>(() => ({
    nodes: legacyNodes.value,
    edges: legacyEdges.value,
  }))
  const flowIssueSummary = computed(() => {
    const unsaved = legacyNodes.value.filter((node) => !node.config?.id).length
    const isolated =
      legacyNodes.value.length <= 1
        ? 0
        : legacyNodes.value.filter((node) => {
            const connections = getNodeConnections(node.id)
            return !connections.inputs.length && !connections.outputs.length
          }).length
    const decisionIncomplete = legacyNodes.value.filter((node) => {
      if (!isDecisionNode(node.type) || !node.config?.id) return false
      return getNodeConnections(node.id).outputs.length === 0
    }).length
    return { unsaved, isolated, decisionIncomplete }
  })

  watch(
    () => props.flowData,
    (newData) => {
      const normalized = normalizeFlowData(newData)
      const incomingSignature = getFlowSignature(normalized)
      if (incomingSignature === lastEmittedSignature.value) {
        return
      }
      syncingFromProps = true
      flowNodes.value = normalized.nodes.map(toVueNode)
      flowEdges.value = normalized.edges
        .map((edge) => toVueEdge(edge, normalized.edges))
        .filter(isValidVueEdge)
      selectedNodeId.value = flowNodes.value.some((node) => node.id === selectedNodeId.value)
        ? selectedNodeId.value
        : ''
      nextTick(() => {
        syncingFromProps = false
        if (flowNodes.value.length) {
          fitView({ padding: 0.35, maxZoom: INITIAL_MAX_ZOOM, duration: 200 })
        }
      })
    },
    { immediate: true, deep: true }
  )

  watch(
    [flowNodes, flowEdges],
    () => {
      if (syncingFromProps) return
      notifyDataChange()
    },
    { deep: true }
  )

  onBeforeUnmount(() => {
    clearNodePopoverTimer()
  })

  function normalizeFlowData(data?: FlowData): FlowData {
    return {
      nodes: Array.isArray(data?.nodes) ? data!.nodes : [],
      edges: Array.isArray(data?.edges) ? data!.edges : [],
    }
  }

  function getFlowSignature(data: FlowData) {
    return JSON.stringify({
      nodes: data.nodes.map((node) => ({
        id: node.id,
        type: node.type,
        label: node.label,
        position: node.position,
        config: node.config || {},
      })),
      edges: data.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
      })),
    })
  }

  function notifyDataChange() {
    const data = legacyFlowData.value
    const signature = getFlowSignature(data)
    lastEmittedSignature.value = signature
    emit('flowChange', data)
  }

  function toVueNode(node: UINode): Node {
    return {
      id: node.id,
      type: 'uiStepNode',
      position: node.position || { x: 0, y: 0 },
      dimensions: { width: NODE_WIDTH, height: NODE_HEIGHT },
      data: {
        uiType: node.type,
        label: node.label,
        config: node.config || {},
        color: getColor(node.type),
      },
    }
  }

  function toLegacyNode(node: Node): UINode {
    return {
      id: node.id,
      position: {
        x: Number(node.position?.x || 0),
        y: Number(node.position?.y || 0),
      },
      type: Number(node.data?.uiType ?? 0),
      label: String(node.data?.label || getNodeTypeLabel(Number(node.data?.uiType ?? 0))),
      config: (node.data?.config || {}) as Record<any, any>,
    }
  }

  function toVueEdge(edge: UIEdge, edgeList = legacyEdges.value): Edge {
    const decisionLabel = getDecisionEdgeLabel(edge, edgeList)
    return {
      id: edge.id,
      source: edge.source.node_id,
      target: edge.target.node_id,
      sourceHandle: edge.source.position || 'bottom',
      targetHandle: edge.target.position || 'top',
      type: 'smoothstep',
      animated: isDecisionNode(getLegacyNode(edge.source.node_id)?.type),
      style: { stroke: 'var(--m-muted)' },
      markerEnd: 'arrowclosed',
      label: decisionLabel,
      labelStyle: { fill: 'var(--m-text-2)', fontSize: 12 },
      labelBgStyle: { fill: 'var(--m-surface)', fillOpacity: 0.9 },
    }
  }

  function toLegacyEdge(edge: Edge): UIEdge {
    return {
      id: edge.id,
      source: {
        node_id: edge.source,
        position: normalizeHandlePosition(edge.sourceHandle, 'bottom'),
      },
      target: {
        node_id: edge.target,
        position: normalizeHandlePosition(edge.targetHandle, 'top'),
      },
    }
  }

  function isValidVueEdge(edge: Edge) {
    return Boolean(
      flowNodes.value.find((node) => node.id === edge.source) &&
        flowNodes.value.find((node) => node.id === edge.target)
    )
  }

  function normalizeHandlePosition(value: any, fallback: ConnectorPosition): ConnectorPosition {
    return value === 'top' || value === 'bottom' ? value : fallback
  }

  function getLegacyNode(nodeId: string) {
    return legacyNodes.value.find((node) => node.id === nodeId)
  }

  function getStepDataByNodeId(nodeId: string) {
    const node = getLegacyNode(nodeId)
    if (!node?.config?.id) return null
    return props.tableData.find((item: any) => item.id === node.config?.id) || null
  }

  function getNodeTitle(nodeId: string) {
    const node = getLegacyNode(nodeId)
    const step = getStepDataByNodeId(nodeId)
    return (
      step?.ele_name?.name ||
      useSelectValue.getSelectLabel(step?.ope_key) ||
      node?.label ||
      '未保存节点'
    )
  }

  function getNodeOperation(nodeId: string) {
    const node = getLegacyNode(nodeId)
    const step = getStepDataByNodeId(nodeId)
    return useSelectValue.getSelectLabel(step?.ope_key) || node?.label || '待配置'
  }

  function getNodeLocator(nodeId: string) {
    const step = getStepDataByNodeId(nodeId)
    return step?.ele_name?.loc || step?.sql || step?.func || ''
  }

  function getNodeInfoSections(nodeId: string) {
    const node = getLegacyNode(nodeId)
    const step = getStepDataByNodeId(nodeId)
    const elementInfo = step?.ele_name || null
    const operationInfo = step
      ? Object.fromEntries(Object.entries(step).filter(([key]) => key !== 'ele_name'))
      : null

    return [
      {
        title: '节点信息',
        rows: toInfoRows({
          node_id: node?.id,
          node_type: node?.type,
          node_type_name: node ? getNodeTypeLabel(node.type) : '',
          status: getNodeStatusText(nodeId),
          label: node?.label,
          position: node?.position,
          config: node?.config,
        }),
      },
      {
        title: '元素信息',
        rows: elementInfo
          ? toInfoRows(elementInfo)
          : [{ label: '暂无元素信息', value: '-', multiline: false }],
      },
      {
        title: '操作信息',
        rows: operationInfo
          ? toInfoRows(operationInfo)
          : [{ label: '暂无操作信息', value: '-', multiline: false }],
      },
    ]
  }

  function toInfoRows(record: Record<string, any>) {
    return Object.entries(record)
      .map(([label, rawValue]) => {
        const cleanedValue = pruneEmptyValue(rawValue)
        if (isEmptyInfoValue(cleanedValue)) return null
        return {
          label,
          value: formatInfoValue(cleanedValue),
          multiline: typeof cleanedValue === 'object' && cleanedValue !== null,
        }
      })
      .filter(Boolean) as Array<{ label: string; value: string; multiline: boolean }>
  }

  function pruneEmptyValue(value: any): any {
    if (isEmptyInfoValue(value)) return null
    if (Array.isArray(value)) {
      const items = value
        .map((item) => pruneEmptyValue(item))
        .filter((item) => !isEmptyInfoValue(item))
      return items.length ? items : null
    }
    if (typeof value === 'object') {
      const entries = Object.entries(value)
        .map(([key, item]) => [key, pruneEmptyValue(item)])
        .filter(([, item]) => !isEmptyInfoValue(item))
      return entries.length ? Object.fromEntries(entries) : null
    }
    return value
  }

  function isEmptyInfoValue(value: any) {
    if (value === null || value === undefined || value === '') return true
    if (Array.isArray(value)) return value.length === 0
    if (typeof value === 'object') return Object.keys(value).length === 0
    return false
  }

  function formatInfoValue(value: any) {
    if (value === undefined) return '-'
    if (value === null) return 'null'
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2)
    }
    return String(value)
  }

  function startNodePopoverTimer(nodeId: string) {
    clearNodePopoverTimer()
    popoverTimer = setTimeout(() => {
      activePopoverNodeId.value = nodeId
    }, 1000)
  }

  function restartNodePopoverTimer(nodeId: string) {
    if (activePopoverNodeId.value === nodeId) return
    startNodePopoverTimer(nodeId)
  }

  function hideNodePopover(nodeId: string) {
    clearNodePopoverTimer()
    if (activePopoverNodeId.value === nodeId) {
      activePopoverNodeId.value = ''
    }
  }

  function clearNodePopoverTimer() {
    if (popoverTimer) {
      clearTimeout(popoverTimer)
      popoverTimer = null
    }
  }

  function getNodeTypeLabel(type: number) {
    return props.nodeTypes.find((item) => item.type === type)?.label || `${type} 节点`
  }

  function getColor(type: number) {
    return props.nodeTypes.find((item) => item.type === type)?.color || 'var(--m-primary)'
  }

  function isDecisionNode(type?: number) {
    return type === 4
  }

  function isExpectDecisionNode(nodeId: string) {
    const node = getLegacyNode(nodeId)
    if (!isDecisionNode(node?.type) || !node?.config?.id) return false
    const step = props.tableData.find((item: any) => item.id === node.config?.id)
    const parameter = useSelectValue.findItemByValue(step?.ope_key)?.parameter || []
    return parameter.some((item: any) => item.f === 'expect')
  }

  function getNodeStatus(nodeId: string) {
    const node = getLegacyNode(nodeId)
    if (!node?.config?.id) return 'unsaved'
    const connections = getNodeConnections(nodeId)
    if (legacyNodes.value.length > 1 && !connections.inputs.length && !connections.outputs.length) {
      return 'isolated'
    }
    if (isDecisionNode(node.type) && connections.outputs.length === 0) {
      return 'warning'
    }
    return 'ready'
  }

  function getNodeStatusText(nodeId: string) {
    const status = getNodeStatus(nodeId)
    if (status === 'unsaved') return '未保存'
    if (status === 'isolated') return '未连接'
    if (status === 'warning') return '待连分支'
    return '已配置'
  }

  function getDecisionEdgeLabel(edge: UIEdge, edgeList = legacyEdges.value) {
    const sourceNode = getLegacyNode(edge.source.node_id)
    if (!isDecisionNode(sourceNode?.type)) return ''
    const outputs = edgeList.filter((item) => item.source.node_id === edge.source.node_id)
    const index = outputs.findIndex((item) => item.id === edge.id)
    if (!isExpectDecisionNode(edge.source.node_id)) {
      if (index === 0) return 'True'
      if (index === 1) return 'False'
    }
    return `分支 ${index + 1}`
  }

  function getNodeConnections(nodeId: string) {
    const inputs = legacyEdges.value.filter((edge) => edge.target.node_id === nodeId)
    const outputs = legacyEdges.value.filter((edge) => edge.source.node_id === nodeId)
    return { inputs, outputs }
  }

  function onDragStart(event: DragEvent, type: string) {
    event.dataTransfer?.setData('application/mango-flow', type)
    event.dataTransfer!.effectAllowed = 'move'
  }

  function onDragOver(event: DragEvent) {
    if (!props.allowDrop || props.readonly) return
    event.preventDefault()
    event.dataTransfer!.dropEffect = 'move'
  }

  function onDrop(event: DragEvent) {
    if (!props.allowDrop || props.readonly) return
    event.preventDefault()
    const type = event.dataTransfer?.getData('application/mango-flow')
    if (!type) return
    const nodeType = parseInt(type, 10)
    const id = `${type}-${Date.now()}`
    const position = screenToFlowCoordinate({ x: event.clientX, y: event.clientY })
    flowNodes.value = flowNodes.value.concat({
      id,
      type: 'uiStepNode',
      position: constrainPosition(position),
      dimensions: { width: NODE_WIDTH, height: NODE_HEIGHT },
      data: {
        uiType: nodeType,
        label: getNodeTypeLabel(nodeType),
        config: {},
        color: getColor(nodeType),
      },
    })
  }

  function constrainPosition(position: Position): Position {
    const minX = 10
    const minY = 10
    const maxX = 3000 - NODE_WIDTH - 10
    const maxY = 2000 - NODE_HEIGHT - 10
    return {
      x: Math.max(minX, Math.min(maxX, position.x)),
      y: Math.max(minY, Math.min(maxY, position.y)),
    }
  }

  function onConnect(connection: Connection) {
    if (props.readonly || !connection.source || !connection.target) return
    const source: Connector = {
      node_id: connection.source,
      position: normalizeHandlePosition(connection.sourceHandle, 'bottom'),
    }
    const target: Connector = {
      node_id: connection.target,
      position: normalizeHandlePosition(connection.targetHandle, 'top'),
    }
    if (!isValidConnection(source, target)) return
    const tempEdge: UIEdge = {
      id: `e-${Date.now()}`,
      source,
      target,
    }
    const edge: Edge = {
      ...toVueEdge(tempEdge),
      label: getDecisionEdgeLabel(tempEdge, legacyEdges.value.concat(tempEdge)),
    }
    flowEdges.value = flowEdges.value.concat(edge)
  }

  function isValidConnection(source: Connector, target: Connector): boolean {
    const startNode = getLegacyNode(source.node_id)
    const endNode = getLegacyNode(target.node_id)
    if (!startNode || !endNode) return false
    if (source.node_id === target.node_id) {
      Message.warning('连接无效：节点不能连接到自己')
      return false
    }
    if (
      legacyEdges.value.some(
        (edge) =>
          edge.source.node_id === source.node_id &&
          edge.source.position === source.position &&
          edge.target.node_id === target.node_id &&
          edge.target.position === target.position
      )
    ) {
      Message.warning('连接无效：当前连接已存在')
      return false
    }

    const isStartDecision = isDecisionNode(startNode.type)
    const isEndDecision = isDecisionNode(endNode.type)
    const startConnections = getNodeConnections(source.node_id)
    const endConnections = getNodeConnections(target.node_id)
    let isValid = false
    let errorMessage = ''

    if (isStartDecision && isEndDecision) {
      errorMessage = '判断类型节点之间不允许连接'
    } else if (isStartDecision) {
      if (!isExpectDecisionNode(source.node_id) && startConnections.outputs.length >= 2) {
        errorMessage = '无期望值判断节点只允许 True / False 两个分支'
      } else if (target.position === 'top' && endConnections.inputs.length > 0) {
        errorMessage = '普通节点最多只能有一个输入连接'
      } else if (target.position === 'bottom') {
        errorMessage = '普通节点只能从上方接收连接'
      } else {
        isValid = true
      }
    } else if (isEndDecision) {
      if (source.position === 'bottom' && startConnections.outputs.length > 0) {
        errorMessage = '普通节点最多只能有一个输出连接'
      } else if (source.position === 'top') {
        errorMessage = '普通节点只能从下方发出连接'
      } else {
        isValid = true
      }
    } else if (source.position !== 'bottom' || target.position !== 'top') {
      errorMessage = '普通节点只能从上方接收连接，从下方发出连接'
    } else if (startConnections.outputs.length > 0) {
      errorMessage = '普通节点最多只能有一个输出连接'
    } else if (endConnections.inputs.length > 0) {
      errorMessage = '普通节点最多只能有一个输入连接'
    } else {
      isValid = true
    }

    if (!isValid && errorMessage) {
      Message.warning(`连接无效：${errorMessage}`)
    }
    return isValid
  }

  function onNodeClick(event: NodeMouseEvent) {
    selectedNodeId.value = event.node.id
    const node = getLegacyNode(event.node.id)
    if (node) {
      emit('nodeClick', node)
      emit('nodeSelect', node)
    }
  }

  function onNodeDragStop(event: NodeDragEvent) {
    const node = flowNodes.value.find((item) => item.id === event.node.id)
    if (node) {
      node.position = constrainPosition(node.position)
      notifyDataChange()
    }
  }

  function onEdgeClick(event: EdgeMouseEvent) {
    if (props.readonly) return
    deleteEdgeById(event.edge.id)
  }

  function deleteEdgeById(edgeId: string) {
    const edge = legacyEdges.value.find((item) => item.id === edgeId)
    flowEdges.value = flowEdges.value.filter((item) => item.id !== edgeId)
    if (edge) {
      emit('edgeDelete', edge)
    }
  }

  function deleteNodeById(nodeId: string) {
    if (props.readonly) return
    const node = getLegacyNode(nodeId)
    if (!node) return
    flowEdges.value = flowEdges.value.filter(
      (edge) => edge.source !== nodeId && edge.target !== nodeId
    )
    flowNodes.value = flowNodes.value.filter((item) => item.id !== nodeId)
    if (selectedNodeId.value === nodeId) {
      selectedNodeId.value = ''
      emit('nodeSelect', null)
    }
    emit('nodeDelete', node)
  }

  function beautifyLayout() {
    if (flowNodes.value.length === 0) return
    const nodes = legacyNodes.value
    const edges = legacyEdges.value
    const startNodes = nodes.filter(
      (node) => !edges.some((edge) => edge.target.node_id === node.id)
    )
    if (startNodes.length === 0 && nodes.length) {
      startNodes.push(nodes[0])
    }
    const startX = 80
    const startY = 80
    const horizontalGap = 260
    const verticalGap = 150
    const processedNodes = new Set<string>()
    const nodeLevels = new Map<string, number>()
    const levelNodes = new Map<number, string[]>()

    const calculateLevel = (nodeId: string, level: number) => {
      if (processedNodes.has(nodeId)) return
      processedNodes.add(nodeId)
      nodeLevels.set(nodeId, level)
      if (!levelNodes.has(level)) {
        levelNodes.set(level, [])
      }
      levelNodes.get(level)!.push(nodeId)
      edges
        .filter((edge) => edge.source.node_id === nodeId)
        .forEach((edge) => calculateLevel(edge.target.node_id, level + 1))
    }

    startNodes.forEach((node) => calculateLevel(node.id, 0))
    nodes
      .filter((node) => !processedNodes.has(node.id))
      .forEach((node) => calculateLevel(node.id, 0))

    const nodePositions = new Map<string, Position>()
    levelNodes.forEach((nodeIds, level) => {
      const y = startY + level * verticalGap
      nodeIds.forEach((nodeId, index) => {
        nodePositions.set(nodeId, { x: startX + index * horizontalGap, y })
      })
    })

    const maxLevel = Math.max(...Array.from(levelNodes.keys()))
    for (let level = maxLevel - 1; level >= 0; level--) {
      const nodeIds = levelNodes.get(level) || []
      nodeIds.forEach((nodeId) => {
        const childPositions = edges
          .filter((edge) => edge.source.node_id === nodeId)
          .map((edge) => nodePositions.get(edge.target.node_id))
          .filter((position) => position !== undefined) as Position[]
        if (!childPositions.length) return
        const minX = Math.min(...childPositions.map((position) => position.x))
        const maxX = Math.max(...childPositions.map((position) => position.x))
        const current = nodePositions.get(nodeId)
        if (current) {
          nodePositions.set(nodeId, { x: (minX + maxX) / 2, y: current.y })
        }
      })
    }

    flowNodes.value = flowNodes.value.map((node) => ({
      ...node,
      position: constrainPosition(nodePositions.get(node.id) || node.position),
    }))
    nextTick(() => fitView({ padding: 0.35, maxZoom: INITIAL_MAX_ZOOM, duration: 200 }))
  }

  defineExpose({
    clearSelection: () => {
      selectedNodeId.value = ''
      emit('nodeSelect', null)
    },
    selectNode: (nodeId: string) => {
      selectedNodeId.value = nodeId
      const node = getLegacyNode(nodeId)
      if (node) {
        emit('nodeSelect', node)
      }
    },
    getFlowData: () => legacyFlowData.value,
    beautifyLayout,
  })
</script>

<style scoped>
  .flow-container {
    display: flex;
    width: 100%;
    height: 100%;
    min-height: 0;
    gap: 12px;
  }

  .left-panel,
  .center-panel {
    display: flex;
    min-height: 0;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    overflow: hidden;
  }

  .left-panel {
    flex: 0 0 220px;
  }

  .center-panel {
    flex: 1;
    min-width: 0;
  }

  .flow-panel-head {
    flex: none;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .center-panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .flow-panel-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .flow-panel-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .flow-stats {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    gap: 8px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .flow-stats span {
    padding: 2px 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-pill);
    background: var(--m-surface-soft);
  }

  .flow-stats .flow-stat-issue {
    color: var(--m-warning);
    border-color: color-mix(in srgb, var(--m-warning) 34%, transparent);
    background: color-mix(in srgb, var(--m-warning) 10%, transparent);
  }

  .drag-panel {
    flex: 1;
    min-height: 0;
    padding: 10px;
    overflow: auto;
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
    color: var(--m-text-2);
    font-size: 13px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    cursor: grab;
    transition: all 0.2s;
  }

  .node-type-item:hover {
    border-color: var(--m-primary-border);
    background: var(--m-primary-soft);
  }

  .node-type-item:active {
    cursor: grabbing;
  }

  .color-dot {
    flex-shrink: 0;
    width: 8px;
    height: 8px;
    margin-right: 8px;
    border-radius: 50%;
  }

  .flow-canvas {
    position: relative;
    flex: 1;
    min-height: 0;
  }

  .flow-empty {
    position: absolute;
    top: 50%;
    left: 50%;
    z-index: 2;
    width: min(320px, calc(100% - 48px));
    padding: 18px 20px;
    text-align: center;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-surface) 88%, transparent);
    transform: translate(-50%, -50%);
    pointer-events: none;
  }

  .flow-empty-title {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
  }

  .flow-empty-desc {
    margin-top: 6px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .ui-step-flow {
    width: 100%;
    height: 100%;
    background: linear-gradient(
        180deg,
        color-mix(in srgb, var(--m-surface) 72%, transparent),
        color-mix(in srgb, var(--m-surface-soft) 85%, transparent)
      ),
      var(--m-surface-soft);
  }

  .step-node {
    position: relative;
    width: 184px;
    min-height: 76px;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-left: 4px solid var(--node-color, var(--m-primary));
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
    cursor: pointer;
    transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
  }

  .step-node:hover {
    border-color: var(--node-color, var(--m-primary));
    transform: translateY(-1px);
  }

  .step-node-selected {
    border-color: var(--node-color, var(--m-primary));
    box-shadow: var(--m-form-focus-shadow);
  }

  .step-node-unsaved {
    border-color: var(--m-warning);
    border-left-color: var(--m-warning);
  }

  .step-node-isolated,
  .step-node-warning {
    border-color: color-mix(in srgb, var(--m-warning) 64%, var(--m-border));
    border-left-color: var(--node-color, var(--m-primary));
  }

  .step-node-ready {
    border-color: color-mix(in srgb, var(--m-success) 22%, var(--m-border));
    border-left-color: var(--node-color, var(--m-primary));
  }

  .node-delete {
    position: absolute;
    top: -8px;
    right: -8px;
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    padding: 0;
    color: var(--m-on-danger);
    font-size: 12px;
    line-height: 1;
    border: 2px solid var(--m-surface);
    border-radius: 50%;
    background: var(--m-danger);
    cursor: pointer;
    opacity: 0;
    transition: all 0.2s;
  }

  .step-node:hover .node-delete {
    opacity: 1;
  }

  .node-main {
    min-width: 0;
  }

  .node-kicker {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 2px;
    overflow: hidden;
    color: var(--m-muted);
    font-size: 11px;
    line-height: 15px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-kicker > span:first-child {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .node-status-text {
    flex: none;
    color: var(--m-muted);
    font-size: 11px;
    font-weight: 500;
  }

  .node-title {
    margin-bottom: 4px;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-content {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 6px;
    overflow: hidden;
    color: var(--m-muted);
    font-size: 11px;
    line-height: 16px;
  }

  .node-content > span:first-child {
    flex: none;
    max-width: 56px;
    overflow: hidden;
    color: var(--node-color, var(--m-primary));
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-locator {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-popover {
    width: 420px;
    max-height: 460px;
    overflow: auto;
  }

  .node-popover-title {
    margin-bottom: 10px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
  }

  .node-popover-section + .node-popover-section {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--m-border);
  }

  .node-popover-section-title {
    margin-bottom: 8px;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 600;
    line-height: 18px;
  }

  .node-popover-row {
    display: grid;
    grid-template-columns: 104px minmax(0, 1fr);
    gap: 8px;
    align-items: start;
    padding: 3px 0;
  }

  .node-popover-key {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-popover-value {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-popover-value-code {
    max-height: 180px;
    margin: 0;
    padding: 8px;
    overflow: auto;
    color: var(--m-code-text);
    font-family: Consolas, 'Courier New', monospace;
    white-space: pre-wrap;
    word-break: break-word;
    border: 1px solid var(--m-code-border);
    border-radius: var(--m-radius-md);
    background: var(--m-code-bg);
  }

  :global(.step-node-popover) {
    max-width: none;
    background: var(--m-surface);
    border: 1px solid var(--m-border);
    box-shadow: var(--m-shadow);
  }

  .step-handle {
    width: 12px;
    height: 12px;
    border: 2px solid var(--m-surface) !important;
    background: var(--node-color, var(--m-primary)) !important;
    box-shadow: 0 0 0 1px var(--node-color, var(--m-primary));
  }

  .step-handle:hover {
    background: var(--node-color, var(--m-primary)) !important;
  }

  .step-handle-top {
    top: -7px;
  }

  .step-handle-bottom {
    bottom: -7px;
  }

  :deep(.vue-flow__edge-path) {
    stroke: var(--m-muted);
    stroke-width: 2;
  }

  :deep(.vue-flow__edge.selected .vue-flow__edge-path),
  :deep(.vue-flow__edge:hover .vue-flow__edge-path) {
    stroke: var(--m-primary);
  }

  :deep(.vue-flow__controls) {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    box-shadow: var(--m-shadow);
    overflow: hidden;
  }

  :deep(.vue-flow__controls-button) {
    color: var(--m-text);
    border-bottom-color: var(--m-border);
    background: var(--m-surface);
  }

  :deep(.vue-flow__controls-button:hover) {
    background: var(--m-surface-soft);
  }

  :deep(.vue-flow__minimap) {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
    overflow: hidden;
  }

  :deep(.vue-flow__minimap-node) {
    fill: var(--m-primary-soft);
    stroke: var(--m-primary);
  }
</style>
