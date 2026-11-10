<template>
  <div :class="['flow-container', { 'flow-container-compact': compact }]">
    <div v-if="!compact" class="left-column">
      <section class="step-control-panel">
        <div class="flow-panel-head">
          <div class="flow-panel-title">步骤调试控制</div>
          <div class="flow-panel-subtitle">仅对本次调试生效</div>
        </div>
        <div class="step-control-list">
          <div class="step-control-item">
            <span>执行后关闭浏览器</span>
            <a-switch v-model="controlState.close_after_execution" size="small" />
          </div>
          <div class="step-control-item">
            <span>执行前等待</span>
            <a-input-number
              :model-value="controlState.before_wait_seconds"
              size="small"
              :min="0"
              :max="3600"
              :precision="0"
              @change="updateControlWait('before_wait_seconds', $event)"
            >
              <template #suffix>秒</template>
            </a-input-number>
          </div>
          <div class="step-control-item">
            <span>执行后等待</span>
            <a-input-number
              :model-value="controlState.after_wait_seconds"
              size="small"
              :min="0"
              :max="3600"
              :precision="0"
              @change="updateControlWait('after_wait_seconds', $event)"
            >
              <template #suffix>秒</template>
            </a-input-number>
          </div>
        </div>
      </section>

      <section class="step-healing-panel">
        <div class="step-healing-summary">
          <button class="step-healing-summary__main" type="button" :disabled="readonly" @click="emit('openStepHealing')">
            <span class="flow-panel-title">流程自愈</span>
            <span class="flow-panel-subtitle">
              {{ healingEnabled ? (healingGoal || '已启用，点击查看配置') : '未启用，点击配置目标和条件' }}
            </span>
          </button>
          <div class="step-healing-summary__footer">
            <span
              :class="[
                'step-healing-status',
                {
                  'step-healing-status--enabled': healingEnabled && !healingPendingReviewCount,
                  'step-healing-status--pending': healingPendingReviewCount,
                },
              ]"
            >
              {{
                healingPendingReviewCount
                  ? `${healingPendingReviewCount} 个节点待检查`
                  : healingEnabled
                    ? '已启用'
                    : '未启用'
              }}
            </span>
            <a-space class="step-healing-summary__actions" :size="4">
              <a-button
                v-if="healingPendingReviewCount"
                size="small"
                type="primary"
                status="warning"
                :loading="healingReviewConfirming"
                :disabled="readonly"
                @click="emit('confirmHealingReview')"
              >
                确认修复
              </a-button>
              <a-button size="small" type="text" :disabled="readonly" @click="emit('openStepHealing')">
                查看配置
              </a-button>
            </a-space>
          </div>
        </div>
      </section>

      <section class="canvas-nodes-panel">
        <div class="flow-panel-head">
          <div class="flow-panel-title">画布节点</div>
          <div class="flow-panel-subtitle">拖至画布添加节点</div>
        </div>
        <div class="drag-panel">
          <section class="palette-section">
            <div class="node-types">
              <div
                v-for="nodeType in nodeTypes"
                :key="nodeType.type"
                class="node-type-card"
                :draggable="!readonly"
                @dragstart="onDragStart($event, nodeType.type.toString())"
              >
                <span class="color-dot" :style="{ backgroundColor: nodeType.color }"></span>
                <span>{{ nodeType.label }}</span>
              </div>
            </div>
          </section>
        </div>
      </section>
    </div>

    <div class="center-panel">
      <div class="flow-panel-head center-panel-head">
        <div>
          <div class="flow-panel-title">流程画布</div>
          <div class="flow-title-row">
            <div class="flow-panel-subtitle">画布修改后自动保存，执行前需完成节点配置与连线</div>
            <span
              v-if="debugStatusText"
              :class="['flow-debug-status', `flow-debug-status-${debugStatusType || 'running'}`]"
            >
              {{ debugStatusText }}
            </span>
          </div>
        </div>
        <div v-if="!compact || showStepDetailAction || showCacheDataAction" class="flow-head-side">
          <div class="flow-actions">
            <a-button
              v-if="showStepDetailAction"
              size="small"
              type="primary"
              @click="emit('openStepDetail')" data-testid="qa-views-uitest-page-steps-details-flowchart-button-步骤详情"
            >
              步骤详情
            </a-button>
            <a-button
              v-if="showCacheDataAction"
              size="small"
              type="primary"
              @click="emit('openCacheData')"
              data-testid="qa-views-uitest-page-steps-details-flowchart-button-缓存数据"
            >
              缓存数据
            </a-button>
            <template v-if="!compact">
              <a-button size="small" type="outline" @click="emit('canvasBeautify')" data-testid="qa-views-uitest-page-steps-details-flowchart-button-美化画布">
                美化画布
              </a-button>
              <a-button
                size="small"
                type="primary"
                :loading="flowSaving"
                :disabled="flowSaveStatus === 'saved'"
                @click="emit('canvasSave')"
              >
                {{ flowSaveButtonText }}
              </a-button>
            </template>
          </div>
          <div v-if="!compact" class="flow-stats">
            <span v-if="flowIssueSummary.unsaved" class="flow-stat-issue">
              未保存 {{ flowIssueSummary.unsaved }}
            </span>
            <span v-if="flowIssueSummary.isolated" class="flow-stat-issue">
              未连接 {{ flowIssueSummary.isolated }}
            </span>
            <span v-if="flowIssueSummary.decisionIncomplete" class="flow-stat-issue">
              判断待连 {{ flowIssueSummary.decisionIncomplete }}
            </span>
          </div>
        </div>
      </div>
      <div ref="flowCanvasRef" class="flow-canvas" @drop="onDrop" @dragover="onDragOver">
        <div v-if="!flowNodes.length" class="flow-empty">
          <div class="flow-empty-title">从左侧拖入节点开始编排</div>
          <div class="flow-empty-desc">画布会自动保存草稿；调试前请完成节点配置和流程连线。</div>
        </div>
        <UiFlowCanvas
          :id="flowId"
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          class="ui-step-flow"
          :nodes-draggable="!readonly"
          :nodes-connectable="!readonly"
          :connection-mode="ConnectionMode.Loose"
          :elements-selectable="true"
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
              <UiFlowNodeCard
                class="step-node"
                :badges="getNodeBadges(id)"
                :color="data.color"
                :operation="getNodeOperation(id)"
                :selected="selected || selectedNodeId === id"
                :status-key="getNodeStatus(id)"
                :title="getNodeTitle(id)"
                :type-text="getNodeTypeLabel(Number(data.uiType))"
                @pointerdown.capture="activateNodeShortcut(id)"
                @mouseenter="startNodePopoverTimer(id)"
                @mousemove="restartNodePopoverTimer(id)"
                @mouseleave="hideNodePopover(id)"
              >
                <template #before>
                  <Handle
                    id="top"
                    type="target"
                    :position="FlowPosition.Top"
                    :connectable="!readonly"
                    class="step-handle step-handle-top"
                  />
                  <Handle
                    id="left"
                    type="target"
                    :position="FlowPosition.Left"
                    :connectable="!readonly"
                    class="step-handle step-handle-side step-handle-left"
                  />
                  <Handle
                    id="right"
                    type="target"
                    :position="FlowPosition.Right"
                    :connectable="!readonly"
                    class="step-handle step-handle-side step-handle-right"
                  />
                </template>
                <template #actions>
                  <button
                    v-if="!readonly"
                    class="node-delete"
                    :disabled="Boolean(deletingNodeId)"
                    :aria-busy="deletingNodeId === id"
                    type="button"
                    title="删除节点"
                    @click.stop="deleteNodeById(id)" data-testid="qa-views-uitest-page-steps-details-flowchart-button-删除节点"
                  >
                    {{ deletingNodeId === id ? '…' : '×' }}
                  </button>
                </template>
                <template #after>
                  <Handle
                    id="bottom"
                    type="source"
                    :position="FlowPosition.Bottom"
                    :connectable="!readonly"
                    class="step-handle step-handle-bottom"
                  />
                  <Handle
                    id="left"
                    type="source"
                    :position="FlowPosition.Left"
                    :connectable="!readonly"
                    class="step-handle step-handle-side step-handle-left"
                  />
                  <Handle
                    id="right"
                    type="source"
                    :position="FlowPosition.Right"
                    :connectable="!readonly"
                    class="step-handle step-handle-side step-handle-right"
                  />
                </template>
              </UiFlowNodeCard>
              <template #content>
                <div
                  class="node-popover"
                  @mouseenter="keepNodePopover(id)"
                  @mouseleave="hideNodePopover(id)"
                >
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
        </UiFlowCanvas>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { Handle, ConnectionMode, Position as FlowPosition, useVueFlow } from '@vue-flow/core'
  import type {
    Connection,
    Edge,
    Node as VueNode,
    NodeDragEvent,
    NodeMouseEvent,
    EdgeMouseEvent,
  } from '@vue-flow/core'
  import type {
    Connector,
    ConnectorPosition,
    Position,
    UiStepControl,
    UIEdge,
  } from '@/types/components'
  import { readStepFlow, readStepConfig, type StepFlow as FlowData, type StepNode as UINode, type StepDetail, type StepResult, type StepNodeConfig } from '@/components/business/ui-page-step'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import { liveObject } from '@/components/business/ui-live-workbench'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  type Node = VueNode<{ uiType: number; label: string; config: StepNodeConfig; color: string }> & { dimensions?: { width: number; height: number } }
  import { useEnum } from '@/store/modules/get-enum'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import UiFlowCanvas from '@/components/display/UiFlowCanvas.vue'
  import UiFlowNodeCard from '@/components/display/UiFlowNodeCard.vue'
  import type { UiFlowNodeBadge, UiFlowNodeTone } from '@/components/display/ui-flow'
  import {
    UI_FLOW_INITIAL_MAX_ZOOM,
    UI_FLOW_NODE_HEIGHT,
    UI_FLOW_NODE_WIDTH,
    UI_FLOW_RESPONSIVE_MAX_ZOOM,
  } from '@/components/display/ui-flow'

  const enumStore = useEnum()
  const useSelectValue = useSelectValueStore()

  interface Props {
    contextKey?: string
    beforeNodeDelete?: (node: UINode) => Promise<boolean>
    flowData?: FlowData
    readonly?: boolean
    compact?: boolean
    showStepDetailAction?: boolean
    showCacheDataAction?: boolean
    allowDrop?: boolean
    tableData: StepDetail[]
    nodeTypes: Array<{ type: number; label: string; color: string }>
    healingEnabled?: boolean
    healingGoal?: string
    healingPendingReviewCount?: number
    healingReviewConfirming?: boolean
    resultData?: StepResult | null
    flowSaving?: boolean
    flowSaveStatus?: 'saved' | 'dirty' | 'saving' | 'error'
    debugStatusText?: string
    debugStatusType?: string
    debugRunning?: boolean
    draftNodeIds?: string[]
    decisionDraft?: {
      nodeId?: string
      opeKey?: string
    }
    stepControl?: UiStepControl
  }

  const props = withDefaults(defineProps<Props>(), {
    flowData: () => ({ nodes: [], edges: [] }),
    readonly: false,
    compact: false,
    showStepDetailAction: false,
    showCacheDataAction: false,
    allowDrop: true,
    tableData: () => [],
    nodeTypes: () => [],
    healingEnabled: false,
    healingGoal: '',
    healingPendingReviewCount: 0,
    healingReviewConfirming: false,
    resultData: null,
    flowSaving: false,
    flowSaveStatus: 'saved',
    debugStatusText: '',
    debugStatusType: '',
    debugRunning: false,
    draftNodeIds: () => [],
    decisionDraft: () => ({
      nodeId: '',
      opeKey: '',
    }),
    stepControl: () => ({
      close_after_execution: false,
      before_wait_seconds: 1,
      after_wait_seconds: 1,
      close_live_after_execution: false,
    }),
  })

  const emit = defineEmits<{
    (event: 'nodeClick', node: UINode): void
    (event: 'nodeSelect', node: UINode | null): void
    (event: 'flowChange', flowData: FlowData): void
    (event: 'edgeDelete', edge: UIEdge): void
    (event: 'nodeDelete', node: UINode): void
    (event: 'nodeDuplicate', node: UINode): void
    (event: 'canvasBeautify'): void
    (event: 'canvasSave'): void
    (event: 'openStepDetail'): void
    (event: 'openCacheData'): void
    (event: 'controlChange', control: UiStepControl): void
    (event: 'openStepHealing'): void
    (event: 'confirmHealingReview'): void
  }>()

  const flowId = `ui-step-flow-${Math.random().toString(36).slice(2)}`
  const flowNodes = shallowRef<Node[]>([])
  const flowEdges = shallowRef<Edge[]>([])
  const flowCanvasRef = ref<HTMLElement | null>(null)
  const controlState = ref<UiStepControl>({
    ...defaultStepControl(),
    ...(props.stepControl || {}),
  })
  const selectedNodeId = ref('')
  const shortcutNodeId = ref('')
  const copiedNodeId = ref('')
  const deletingNodeId = ref('')
  const activePopoverNodeId = ref('')
  const decisionMethodDrafts = ref<Record<string, string>>({})
  const lastEmittedSignature = ref('')
  let popoverTimer: ReturnType<typeof setTimeout> | null = null
  let popoverCloseTimer: ReturnType<typeof setTimeout> | null = null
  let canvasResizeTimer: ReturnType<typeof setTimeout> | null = null
  let canvasResizeObserver: ResizeObserver | null = null
  let canvasWidth = 0
  let canvasHeight = 0
  let syncingFromProps = false

  const { fitView, screenToFlowCoordinate } = useVueFlow(flowId)

  const legacyNodes = computed<UINode[]>(() => flowNodes.value.map(toLegacyNode))
  const legacyEdges = computed<UIEdge[]>(() => flowEdges.value.map(toLegacyEdge))
  const legacyFlowData = computed<FlowData>(() => ({
    nodes: legacyNodes.value,
    edges: legacyEdges.value,
  }))
  const resultList = computed(() =>
    Array.isArray(props.resultData?.element_result_list) ? props.resultData.element_result_list : []
  )
  const flowIssueSummary = computed(() => {
    const unsaved = legacyNodes.value.filter(
      (node) => node.config?.id == null || props.draftNodeIds.includes(node.id)
    ).length
    const isolated =
      legacyNodes.value.length <= 1
        ? 0
        : legacyNodes.value.filter((node) => {
            const connections = getNodeConnections(node.id)
            return !connections.inputs.length && !connections.outputs.length
          }).length
    const decisionIncomplete = legacyNodes.value.filter((node) => {
      if (!isDecisionNode(node.type) || node.config?.id == null) return false
      return getNodeConnections(node.id).outputs.length === 0
    }).length
    return { unsaved, isolated, decisionIncomplete }
  })
  const flowSaveButtonText = computed(() => {
    if (props.flowSaveStatus === 'error') return '重试保存'
    if (props.flowSaveStatus === 'dirty') return '立即保存'
    if (props.flowSaveStatus === 'saving') return '保存中'
    return '已自动保存'
  })

  let syncVersion = 0
  const scope = useLiveWorkbenchScope(() => props.contextKey, { invalidate() { syncVersion++; copiedNodeId.value = shortcutNodeId.value = activePopoverNodeId.value = ''; decisionMethodDrafts.value = {}; clearNodePopoverTimer(); clearNodePopoverCloseTimer(); if (canvasResizeTimer !== null) clearTimeout(canvasResizeTimer); canvasResizeTimer = null }, resume: scheduleCanvasFit })
  watch(() => props.stepControl, value => { if (value && JSON.stringify(value) !== JSON.stringify(controlState.value)) controlState.value = { ...value } }, { deep: true })
  watch(
    () => props.flowData,
    (newData) => {
      const normalized = normalizeFlowData(newData)
      const incomingSignature = getFlowSignature(normalized)
      if (incomingSignature === lastEmittedSignature.value) {
        return
      }
      lastEmittedSignature.value = incomingSignature
      syncingFromProps = true
      const current = scope.capture(), sequence = ++syncVersion
      flowNodes.value = normalized.nodes.map(toVueNode)
      flowEdges.value = normalized.edges
        .map((edge) => toVueEdge(edge, normalized.edges))
        .filter(isValidVueEdge)
      const previousSelectedNodeId = selectedNodeId.value
      selectedNodeId.value = flowNodes.value.some((node) => node.id === previousSelectedNodeId)
        ? previousSelectedNodeId
        : flowNodes.value[0]?.id || ''
      nextTick(() => {
        if (!current() || sequence !== syncVersion) return
        syncingFromProps = false
        if (flowNodes.value.length) {
          fitView({ padding: 0.35, maxZoom: UI_FLOW_INITIAL_MAX_ZOOM, duration: 200 })
        }
        if (selectedNodeId.value && selectedNodeId.value !== previousSelectedNodeId) {
          emitSelectedNode(selectedNodeId.value)
        }
      })
    },
    { immediate: true, deep: true }
  )

  watch(
    () => props.tableData,
    () => {
      if (selectedNodeId.value) {
        emitSelectedNode(selectedNodeId.value)
      }
      refreshRuntimeEdgeStyles()
    },
    { deep: true }
  )

  watch(
    () => props.decisionDraft,
    (draft) => {
      const nodeId = String(draft?.nodeId || '')
      if (nodeId) {
        decisionMethodDrafts.value = {
          ...decisionMethodDrafts.value,
          [nodeId]: String(draft?.opeKey || ''),
        }
      }
      refreshRuntimeEdgeStyles()
    },
    { deep: true }
  )

  watch(
    () => props.resultData,
    () => {
      refreshRuntimeEdgeStyles()
    },
    { deep: true }
  )

  watch(
    () => props.debugRunning,
    () => {
      refreshRuntimeEdgeStyles()
    }
  )

  watch(
    [flowNodes, flowEdges],
    () => {
      if (syncingFromProps) return
      notifyDataChange()
    },
    { deep: true }
  )

  watch(
    controlState,
    (value) => {
      emit('controlChange', { ...value })
    },
    { deep: true }
  )

  onMounted(() => {
    document.addEventListener('keydown', handleDuplicateShortcut, true)
    document.addEventListener('pointerdown', handleShortcutPointerDown, true)
    window.addEventListener('resize', scheduleCanvasFit)
    nextTick(() => {
      const canvas = flowCanvasRef.value
      if (!scope.available() || !canvas || typeof ResizeObserver === 'undefined') return
      const rect = canvas.getBoundingClientRect()
      canvasWidth = rect.width
      canvasHeight = rect.height
      canvasResizeObserver = new ResizeObserver(([entry]) => {
        const nextWidth = entry?.contentRect.width || 0
        const nextHeight = entry?.contentRect.height || 0
        if (Math.abs(nextWidth - canvasWidth) < 1 && Math.abs(nextHeight - canvasHeight) < 1) {
          return
        }
        canvasWidth = nextWidth
        canvasHeight = nextHeight
        scheduleCanvasFit()
      })
      canvasResizeObserver.observe(canvas)
    })
  })

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', handleDuplicateShortcut, true)
    document.removeEventListener('pointerdown', handleShortcutPointerDown, true)
    window.removeEventListener('resize', scheduleCanvasFit)
    canvasResizeObserver?.disconnect()
    canvasResizeObserver = null
    if (canvasResizeTimer) {
      clearTimeout(canvasResizeTimer)
      canvasResizeTimer = null
    }
    clearNodePopoverTimer()
    clearNodePopoverCloseTimer()
  })

  function scheduleCanvasFit() {
    const current = scope.capture()
    if (!current()) return
    if (canvasResizeTimer) {
      clearTimeout(canvasResizeTimer)
    }
    canvasResizeTimer = setTimeout(() => {
      canvasResizeTimer = null
      if (!current() || !flowNodes.value.length) return
      fitView({
        padding: 0.28,
        maxZoom: UI_FLOW_RESPONSIVE_MAX_ZOOM,
        duration: 160,
      })
    }, 120)
  }

  function handleDuplicateShortcut(event: KeyboardEvent) {
    if (
      !scope.available() || props.readonly ||
      event.repeat ||
      event.altKey ||
      event.shiftKey ||
      !(event.ctrlKey || event.metaKey)
    ) {
      return
    }
    if (!shortcutNodeId.value || !getLegacyNode(shortcutNodeId.value)) return
    const target = event.target
    if (
      target instanceof HTMLElement &&
      target.closest('input, textarea, select, [contenteditable="true"]')
    ) {
      return
    }
    const shortcutKey = event.code || `Key${String(event.key || '').toUpperCase()}`
    if (shortcutKey === 'KeyC') {
      if (window.getSelection()?.toString()) return
      event.preventDefault()
      copiedNodeId.value = shortcutNodeId.value
      Message.success('节点已复制，按 ⌘V / Ctrl+V 粘贴')
      return
    }
    if (shortcutKey === 'KeyV') {
      if (!copiedNodeId.value) {
        Message.warning('请先选中节点并按 ⌘C / Ctrl+C 复制')
        return
      }
      const copiedNode = getLegacyNode(copiedNodeId.value)
      if (!copiedNode) {
        copiedNodeId.value = ''
        Message.warning('复制的节点已不存在，请重新复制')
        return
      }
      event.preventDefault()
      emit('nodeDuplicate', copiedNode)
      return
    }
    if (shortcutKey !== 'KeyD') return
    const selectedNode = getLegacyNode(shortcutNodeId.value)
    if (!selectedNode) return
    event.preventDefault()
    emit('nodeDuplicate', selectedNode)
  }

  function handleShortcutPointerDown(event: PointerEvent) {
    const target = event.target
    if (!(target instanceof Element)) {
      shortcutNodeId.value = ''
      return
    }
    const canvas = flowCanvasRef.value
    if (!canvas?.contains(target) || !target.closest('.vue-flow__node')) {
      shortcutNodeId.value = ''
    }
  }

  function activateNodeShortcut(nodeId: string) {
    if (!scope.available() || props.readonly || !getLegacyNode(nodeId)) return
    shortcutNodeId.value = nodeId
    selectedNodeId.value = nodeId
  }

  function normalizeFlowData(value?: FlowData): FlowData { return readStepFlow(value) }

  function defaultStepControl(): UiStepControl {
    return {
      close_after_execution: false,
      before_wait_seconds: 1,
      after_wait_seconds: 1,
      close_live_after_execution: false,
    }
  }

  function updateControlWait(
    key: 'before_wait_seconds' | 'after_wait_seconds',
    value: number | undefined
  ) {
    const normalizedValue = Number.isFinite(Number(value))
      ? Math.min(3600, Math.max(0, Math.trunc(Number(value))))
      : 1
    controlState.value[key] = normalizedValue
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
    if (!scope.available() || props.readonly) return
    const data = legacyFlowData.value
    const signature = getFlowSignature(data)
    if (signature === lastEmittedSignature.value) return
    lastEmittedSignature.value = signature
    emit('flowChange', data)
  }

  function toVueNode(node: UINode): Node {
    return {
      id: node.id,
      type: 'uiStepNode',
      position: { ...(node.position || { x: 0, y: 0 }) },
      dimensions: { width: UI_FLOW_NODE_WIDTH, height: UI_FLOW_NODE_HEIGHT },
      data: {
        uiType: node.type,
        label: node.label,
        config: readStepConfig(node.config),
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
      config: readStepConfig(node.data?.config),
    }
  }

  function toVueEdge(edge: UIEdge, edgeList = legacyEdges.value): Edge {
    const decisionLabel = getDecisionEdgeLabel(edge, edgeList)
    const runtimeStatus = getEdgeRuntimeStatus(edge)
    const isDecisionEdge = isDecisionNode(getLegacyNode(edge.source.node_id)?.type)
    const edgeClass = [`flow-edge-${runtimeStatus}`, isDecisionEdge ? 'flow-edge-decision' : '']
      .filter(Boolean)
      .join(' ')
    return {
      id: edge.id,
      source: edge.source.node_id,
      target: edge.target.node_id,
      sourceHandle: edge.source.position || 'bottom',
      targetHandle: edge.target.position || 'top',
      type: 'default',
      pathOptions: { curvature: 0.3 },
      animated: runtimeStatus === 'running',
      class: edgeClass,
      style: { stroke: getEdgeStrokeColor(runtimeStatus) },
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

  function normalizeHandlePosition(value: unknown, fallback: ConnectorPosition): ConnectorPosition {
    return value === 'top' || value === 'right' || value === 'bottom' || value === 'left'
      ? value
      : fallback
  }

  function getLegacyNode(nodeId: string) {
    return legacyNodes.value.find((node) => node.id === nodeId)
  }

  function getStepDataByNodeId(nodeId: string) {
    const node = getLegacyNode(nodeId)
    if (node?.config?.id == null) return null
    return props.tableData.find(item => String(item.id) === String(node.config?.id)) || null
  }

  function getNodeTitle(nodeId: string) {
    const node = getLegacyNode(nodeId)
    const step = getStepDataByNodeId(nodeId)
    const nodeTypeLabel = node ? getNodeTypeLabel(node.type) : ''
    const nodeLabel =
      node?.label && node.label !== nodeTypeLabel && !node.label.endsWith('节点') ? node.label : ''
    return (
      step?.ele_name?.name ||
      nodeLabel ||
      useSelectValue.getSelectLabel(step?.ope_key) ||
      nodeTypeLabel ||
      '未保存节点'
    )
  }

  function getNodeOperation(nodeId: string) {
    const node = getLegacyNode(nodeId)
    const step = getStepDataByNodeId(nodeId)
    if (Number(node?.type) === 6) {
      const seconds = (step?.ope_value || []).find((item) => item?.f === 'seconds')?.v
      return seconds === undefined || seconds === null ? '强制等待' : `等待 ${seconds} 秒`
    }
    return useSelectValue.getSelectLabel(step?.ope_key) || node?.label || '待配置'
  }

  function getNodeInfoSections(nodeId: string) {
    const node = getLegacyNode(nodeId)
    const step = getStepDataByNodeId(nodeId)
    const result = getNodeResultByNodeId(nodeId)
    const elementInfo = step?.ele_name || null
    const sections = [
      {
        title: '节点信息',
        rows: toInfoRows({
          节点类型: node ? getNodeTypeLabel(node.type) : '',
          配置状态: getNodeConfigStatusText(nodeId),
          测试状态: getNodeRuntimeStatusText(nodeId),
          节点名称: getNodeTitle(nodeId),
          执行方法: getNodeOperation(nodeId),
        }),
      },
      {
        title: '元素信息',
        rows: elementInfo
          ? toInfoRows({
              元素名称: elementInfo.name,
              定位类型: getElementExpText(elementInfo.exp),
              定位表达式: elementInfo.loc,
              匹配下标: elementInfo.sub,
              iframe: elementInfo.is_iframe ? '是' : '',
              创建时间: elementInfo.create_time,
              更新时间: elementInfo.update_time,
            })
          : [{ label: '暂无元素信息', value: '-', multiline: false }],
      },
      {
        title: '操作信息',
        rows: step
          ? toInfoRows({
              步骤类型: step.type !== undefined ? getNodeTypeLabel(Number(step.type)) : '',
              执行方法: useSelectValue.getSelectLabel(step?.ope_key) || step?.ope_key,
              条件值: liveObject(step.condition_value).expect ?? step.condition_value,
              自定义变量: formatCustomVariables(step.custom),
              SQL配置: formatSqlExecute(step.sql_execute),
              操作参数: formatOperationValues(step.ope_value),
              创建时间: step.create_time,
              更新时间: step.update_time,
            })
          : [{ label: '暂无操作信息', value: '-', multiline: false }],
      },
    ]
    if (result) {
      sections.push({
        title: '测试结果',
        rows: toInfoRows({
          测试状态: getResultStatusText(result),
          执行方法:
            useSelectValue.getSelectLabel(result?.ope_key || step?.ope_key) || result?.ope_key,
          等待时间: formatSleep(result?.sleep),
          元素数量: getElementRows(result).length,
          错误提示: result?.error_message,
          断言提示: result?.ass_msg,
          失败截图: result?.picture_name,
          元素文本: getResultElementText(result),
        }),
      })
    }
    return sections
  }

  function getNodeResultByNodeId(nodeId: string) {
    const step = getStepDataByNodeId(nodeId)
    if (step?.id == null) return null
    return (
      [...resultList.value].reverse().find((item) => String(item?.id) === String(step.id)) ||
      null
    )
  }

  function getActiveRuntimeNodeId() {
    if (!props.debugRunning) return ''
    const results = resultList.value
    if (!results.length) {
      const rootNode = legacyNodes.value.find(
        (node) => getNodeConnections(node.id).inputs.length === 0
      )
      return rootNode?.id || legacyNodes.value[0]?.id || ''
    }
    const lastResult = results[results.length - 1]
    if (lastResult?.status === 0 || !lastResult?.next_node_id) return ''
    return getNodeByStepId(lastResult.next_node_id)?.id || ''
  }

  function getResultStatusText(result: StepResult | null) {
    if (!result) return '未测试'
    if (result.status === 1) return '通过'
    if (result.status === 0) return '失败'
    return '未测试'
  }

  function formatSleep(value: unknown) {
    if (value === null || value === undefined || value === '') return '-'
    return `${value} 秒`
  }

  function getElementRows(result: StepResult | null) {
    if (result?.elements?.length) return result.elements
    if (result?.ele_name) return [result.ele_name]
    if (result?.loc) return [{ loc: result.loc }]
    return []
  }

  function getElementExpText(value: unknown) {
    if (Array.isArray(value)) return value.map(getElementExpText).filter(Boolean).join(' / ')
    return enumStore.element_exp?.find((item) => item.key === value)?.title || value || '-'
  }

  function formatOperationValues(values: unknown) {
    if (!Array.isArray(values)) return ''
    const rows = values
      .filter((item) => item?.d || item?.v !== undefined)
      .map(
        (item) =>
          `${item.n || item.f || '参数'}=${formatInfoValue(item.v ?? item.value ?? '')}`
      )
      .filter((item: string) => !item.endsWith('='))
    return rows.join('\n')
  }

  function formatCustomVariables(values: unknown) {
    if (!Array.isArray(values)) return ''
    return values
      .map((item) => `${item.key || '变量'}=${formatInfoValue(item.value)}`)
      .filter((item: string) => !item.endsWith('='))
      .join('\n')
  }

  function formatSqlExecute(values: unknown) {
    if (!Array.isArray(values)) return ''
    return values
      .map((item) =>
        [
          item.key_list ? `缓存变量=${formatInfoValue(item.key_list)}` : '',
          item.sql ? `SQL=${formatInfoValue(item.sql)}` : '',
        ]
          .filter(Boolean)
          .join('\n')
      )
      .filter(Boolean)
      .join('\n')
  }

  function getResultElementText(result: StepResult | null) {
    return getElementRows(result)
      .map((item) => item?.element_text)
      .filter(Boolean)
      .join('\n')
  }

  function toInfoRows(record: Record<string, unknown>) {
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

  function pruneEmptyValue(value: unknown): unknown {
    if (isEmptyInfoValue(value)) return null
    if (Array.isArray(value)) {
      const items = value
        .map((item) => pruneEmptyValue(item))
        .filter((item) => !isEmptyInfoValue(item))
      return items.length ? items : null
    }
    if (value !== null && typeof value === 'object') {
      const entries = Object.entries(value)
        .map(([key, item]) => [key, pruneEmptyValue(item)])
        .filter(([, item]) => !isEmptyInfoValue(item))
      return entries.length ? Object.fromEntries(entries) : null
    }
    return value
  }

  function isEmptyInfoValue(value: unknown) {
    if (value === null || value === undefined || value === '') return true
    if (Array.isArray(value)) return value.length === 0
    if (value !== null && typeof value === 'object') return Object.keys(value).length === 0
    return false
  }

  function formatInfoValue(value: unknown) {
    if (value === undefined) return '-'
    if (value === null) return 'null'
    if (value !== null && typeof value === 'object') {
      return JSON.stringify(value, null, 2)
    }
    return String(value)
  }

  function startNodePopoverTimer(nodeId: string) {
    const current = scope.capture()
    if (!current()) return
    clearNodePopoverTimer()
    clearNodePopoverCloseTimer()
    if (activePopoverNodeId.value && activePopoverNodeId.value !== nodeId) {
      activePopoverNodeId.value = ''
    }
    popoverTimer = setTimeout(() => {
      if (current()) activePopoverNodeId.value = nodeId
      popoverTimer = null
    }, 1000)
  }

  function restartNodePopoverTimer(nodeId: string) {
    if (activePopoverNodeId.value === nodeId) return
    startNodePopoverTimer(nodeId)
  }

  function keepNodePopover(nodeId: string) {
    clearNodePopoverCloseTimer()
    activePopoverNodeId.value = nodeId
  }

  function hideNodePopover(nodeId: string) {
    clearNodePopoverTimer()
    clearNodePopoverCloseTimer()
    popoverCloseTimer = setTimeout(() => {
      if (activePopoverNodeId.value === nodeId) {
        activePopoverNodeId.value = ''
      }
      popoverCloseTimer = null
    }, 50)
  }

  function clearNodePopoverTimer() {
    if (popoverTimer) {
      clearTimeout(popoverTimer)
      popoverTimer = null
    }
  }

  function clearNodePopoverCloseTimer() {
    if (popoverCloseTimer) {
      clearTimeout(popoverCloseTimer)
      popoverCloseTimer = null
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
    if (!isDecisionNode(node?.type)) return false
    const step = node?.config?.id != null
      ? props.tableData.find((item) => String(item.id) === String(node.config?.id))
      : null
    const hasDraft = Object.prototype.hasOwnProperty.call(decisionMethodDrafts.value, nodeId)
    const opeKey = hasDraft ? decisionMethodDrafts.value[nodeId] : step?.ope_key
    const parameter = useSelectValue.findItemByValue(opeKey)?.parameter || []
    return parameter.some((item) => item.f === 'expect')
  }

  function getDecisionBranchValue(edge: UIEdge) {
    const targetNode = getLegacyNode(edge.target.node_id)
    if (targetNode?.config?.id == null) return ''
    const targetStep = props.tableData.find((item) => String(item.id) === String(targetNode.config?.id))
    const value = liveObject(targetStep?.condition_value).expect ?? targetStep?.condition_value
    if (value === null || value === undefined || value === '') return ''
    return typeof value === 'object' ? JSON.stringify(value) : String(value)
  }

  function getNodeStatus(nodeId: string): UiFlowNodeTone {
    return (getNodeRuntimeStatus(nodeId) || getNodeConfigStatus(nodeId)) as UiFlowNodeTone
  }

  function getNodeBadges(nodeId: string): UiFlowNodeBadge[] {
    const badges: UiFlowNodeBadge[] = []
    const node = getLegacyNode(nodeId)
    if (node?.config?.ai_healed) {
      const aiReviewPending = node.config.ai_review_status !== 'confirmed'
      badges.push({
        label: aiReviewPending ? 'AI待检查' : 'AI修复',
        title: aiReviewPending ? 'AI修复·待检查' : 'AI修复',
        tone: aiReviewPending ? 'warning' : 'ready',
      })
    }
    const runtimeStatus = getNodeRuntimeStatus(nodeId)
    if (runtimeStatus) {
      badges.push({
        label: getNodeRuntimeStatusText(nodeId),
        tone: runtimeStatus as UiFlowNodeTone,
      })
    }
    const configStatus = getNodeConfigStatus(nodeId) as UiFlowNodeTone
    badges.push({ label: getNodeConfigStatusText(nodeId), tone: configStatus })
    return badges
  }

  function getNodeRuntimeStatus(nodeId: string) {
    const runtimeResult = getNodeResultByNodeId(nodeId)
    if (runtimeResult?.status === 0) return 'failed'
    if (runtimeResult?.status === 1) return 'passed'
    if (props.debugRunning && getActiveRuntimeNodeId() === nodeId) return 'running'
    return ''
  }

  function getNodeConfigStatus(nodeId: string) {
    const node = getLegacyNode(nodeId)
    if (node?.config?.id == null || props.draftNodeIds.includes(nodeId)) return 'unsaved'
    const connections = getNodeConnections(nodeId)
    if (legacyNodes.value.length > 1 && !connections.inputs.length && !connections.outputs.length) {
      return 'isolated'
    }
    if (isDecisionNode(node.type) && connections.outputs.length === 0) {
      return 'warning'
    }
    return 'ready'
  }

  function getNodeConfigStatusText(nodeId: string) {
    const status = getNodeConfigStatus(nodeId)
    if (status === 'unsaved') return '未保存'
    if (status === 'isolated') return '未连接'
    if (status === 'warning') return '待连分支'
    return '已配置'
  }

  function getNodeRuntimeStatusText(nodeId: string) {
    const status = getNodeRuntimeStatus(nodeId)
    if (status === 'failed') return '失败'
    if (status === 'passed') return '通过'
    if (status === 'running') return '执行中'
    return '未测试'
  }

  function getNodeByStepId(stepId: unknown) {
    return legacyNodes.value.find((node) => String(node.config?.id) === String(stepId))
  }

  function getEdgeRuntimeStatus(edge: UIEdge) {
    const sourceNode = getLegacyNode(edge.source.node_id)
    const targetNode = getLegacyNode(edge.target.node_id)
    if (!sourceNode || !targetNode) return 'pending'
    const sourceResult = getNodeResultByNodeId(sourceNode.id)
    const targetResult = getNodeResultByNodeId(targetNode.id)
    const selectedTargetId = sourceResult?.next_node_id
    const followsRuntimePath =
      selectedTargetId !== null &&
      selectedTargetId !== undefined &&
      String(selectedTargetId) === String(targetNode.config?.id)
    if (!followsRuntimePath) return 'pending'
    if (targetResult?.status === 0) return 'failed'
    if (targetResult?.status === 1) return 'passed'
    if (props.debugRunning && getActiveRuntimeNodeId() === targetNode.id) return 'running'
    if (sourceResult?.status === 1) return 'passed'
    return 'pending'
  }

  function getEdgeStrokeColor(status: string) {
    if (status === 'running') return 'var(--m-primary)'
    if (status === 'passed') return 'var(--m-success)'
    if (status === 'failed') return 'var(--m-danger)'
    return 'var(--m-muted)'
  }

  function refreshRuntimeEdgeStyles() {
    if (!flowEdges.value.length) return
    syncingFromProps = true
    const edgeList = legacyEdges.value
    flowEdges.value.forEach((edge) => {
      const runtimeEdge = toVueEdge(toLegacyEdge(edge), edgeList)
      // Vue Flow 会为边维护内部渲染状态。运行结果变化只更新展示字段，
      // 保留原边对象，避免调试开始时整组替换导致 vnode 与 DOM 脱节。
      edge.animated = runtimeEdge.animated
      edge.class = runtimeEdge.class
      edge.style = runtimeEdge.style
      edge.label = runtimeEdge.label
      edge.labelStyle = runtimeEdge.labelStyle
      edge.labelBgStyle = runtimeEdge.labelBgStyle
    })
    flowEdges.value = [...flowEdges.value]
    nextTick(() => {
      syncingFromProps = false
    })
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
    return getDecisionBranchValue(edge) || `分支 ${index + 1} · 待填写判断值`
  }

  function getNodeConnections(nodeId: string) {
    const inputs = legacyEdges.value.filter((edge) => edge.target.node_id === nodeId)
    const outputs = legacyEdges.value.filter((edge) => edge.source.node_id === nodeId)
    return { inputs, outputs }
  }

  function onDragStart(event: DragEvent, type: string) {
    event.dataTransfer?.setData('application/mango-flow', type)
    if (!event.dataTransfer || props.readonly || !scope.available()) return
    event.dataTransfer.effectAllowed = 'move'
  }

  function onDragOver(event: DragEvent) {
    if (!scope.available() || !props.allowDrop || props.readonly) return
    event.preventDefault()
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
  }

  function onDrop(event: DragEvent) {
    if (!scope.available() || !props.allowDrop || props.readonly) return
    event.preventDefault()
    const type = event.dataTransfer?.getData('application/mango-flow')
    if (!type || !props.nodeTypes.some(item => String(item.type) === type)) return
    const nodeType = parseInt(type, 10)
    const id = `${type}-${Date.now()}`
    const pointerPosition = screenToFlowCoordinate({ x: event.clientX, y: event.clientY })
    const position = {
      x: pointerPosition.x - UI_FLOW_NODE_WIDTH / 2,
      y: pointerPosition.y - UI_FLOW_NODE_HEIGHT / 2,
    }
    flowNodes.value = flowNodes.value.concat({
      id,
      type: 'uiStepNode',
      position: constrainPosition(position),
      dimensions: { width: UI_FLOW_NODE_WIDTH, height: UI_FLOW_NODE_HEIGHT },
      data: {
        uiType: nodeType,
        label: getNodeTypeLabel(nodeType),
        config: {},
        color: getColor(nodeType),
      },
    })
  }

  function constrainPosition(position: Position): Position {
    const x = Number(position.x)
    const y = Number(position.y)
    return {
      x: Number.isFinite(x) ? x : 0,
      y: Number.isFinite(y) ? y : 0,
    }
  }

  function onConnect(connection: Connection) {
    if (!scope.available() || props.readonly || !connection.source || !connection.target) return
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
    flowEdges.value = [...flowEdges.value, edge]
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
      } else if (endConnections.inputs.length >= 1) {
        errorMessage = '普通节点最多只能有一条输入线'
      } else {
        isValid = true
      }
    } else if (isEndDecision) {
      if (startConnections.outputs.length >= 1) {
        errorMessage = '普通节点最多只能有一条输出线'
      } else {
        isValid = true
      }
    } else if (startConnections.outputs.length >= 1) {
      errorMessage = '普通节点最多只能有一条输出线'
    } else if (endConnections.inputs.length >= 1) {
      errorMessage = '普通节点最多只能有一条输入线'
    } else {
      isValid = true
    }

    if (!isValid && errorMessage) {
      Message.warning(`连接无效：${errorMessage}`)
    }
    return isValid
  }

  function onNodeClick(event: NodeMouseEvent) {
    activateNodeShortcut(event.node.id)
    emitSelectedNode(event.node.id)
  }

  function emitSelectedNode(nodeId: string) {
    selectedNodeId.value = nodeId
    const node = getLegacyNode(nodeId)
    if (node) {
      emit('nodeClick', node)
      emit('nodeSelect', node)
    }
  }

  function onNodeDragStop(event: NodeDragEvent) {
    if (!scope.available() || props.readonly) return
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

  async function deleteNodeById(nodeId: string) {
    if (!scope.available() || props.readonly || deletingNodeId.value) return
    const node = getLegacyNode(nodeId)
    if (!node) return
    const current = scope.capture()
    deletingNodeId.value = nodeId
    try { if (props.beforeNodeDelete && !(await props.beforeNodeDelete(cloneLosslessJson(node)))) return }
    catch { if (current()) Message.error('节点删除失败，请重试'); return }
    finally { deletingNodeId.value = '' }
    if (!current()) return
    if (Object.prototype.hasOwnProperty.call(decisionMethodDrafts.value, nodeId)) {
      const nextDrafts = { ...decisionMethodDrafts.value }
      delete nextDrafts[nodeId]
      decisionMethodDrafts.value = nextDrafts
    }
    flowEdges.value = flowEdges.value.filter(
      (edge) => edge.source !== nodeId && edge.target !== nodeId
    )
    flowNodes.value = flowNodes.value.filter((item) => item.id !== nodeId)
    if (selectedNodeId.value === nodeId) {
      shortcutNodeId.value = ''
      const nextNode = flowNodes.value[0]
      if (nextNode) {
        emitSelectedNode(nextNode.id)
      } else {
        selectedNodeId.value = ''
        emit('nodeSelect', null)
      }
    }
    emit('nodeDelete', node)
    await nextTick()
    if (current()) notifyDataChange()
  }

  function beautifyLayout() {
    if (!scope.available() || props.readonly) return
    if (flowNodes.value.length === 0) return
    const nodes = legacyNodes.value
    const edges = legacyEdges.value
    const startX = 80
    const startY = 80
    const horizontalGap = 260
    const verticalGap = 150
    const nodePositions = new Map<string, Position>()
    const connectedNodeIds = new Set(
      edges.flatMap((edge) => [edge.source.node_id, edge.target.node_id])
    )
    const connectedNodes = nodes.filter((node) => connectedNodeIds.has(node.id))
    const isolatedNodes = nodes.filter((node) => !connectedNodeIds.has(node.id))
    const outgoing = new Map<string, UIEdge[]>()
    const incoming = new Map<string, UIEdge[]>()
    nodes.forEach((node) => {
      outgoing.set(node.id, [])
      incoming.set(node.id, [])
    })
    edges.forEach((edge) => {
      outgoing.get(edge.source.node_id)?.push(edge)
      incoming.get(edge.target.node_id)?.push(edge)
    })
    const hasBranching = connectedNodes.some(
      (node) =>
        (outgoing.get(node.id)?.length || 0) > 1 ||
        (incoming.get(node.id)?.length || 0) > 1 ||
        isDecisionNode(node.type)
    )
    let arrangedEdges = edges.map((edge) => ({
      ...edge,
      source: { ...edge.source, position: 'bottom' as ConnectorPosition },
      target: { ...edge.target, position: 'top' as ConnectorPosition },
    }))

    if (hasBranching) {
      layoutBranchingFlow(
        connectedNodes,
        arrangedEdges,
        nodePositions,
        startX,
        startY,
        horizontalGap,
        verticalGap
      )
    } else {
      arrangedEdges = layoutSequentialFlow(
        connectedNodes,
        arrangedEdges,
        nodePositions,
        startX,
        startY,
        horizontalGap,
        verticalGap
      )
    }

    const usedPositions = Array.from(nodePositions.values())
    const isolatedStartX =
      (usedPositions.length ? Math.max(...usedPositions.map((position) => position.x)) : startX) +
      horizontalGap
    isolatedNodes.sort(compareNodePosition).forEach((node, index) => {
      nodePositions.set(node.id, {
        x: isolatedStartX,
        y: startY + index * 110,
      })
    })

    flowNodes.value = flowNodes.value.map((node) => ({
      ...node,
      position: constrainPosition(nodePositions.get(node.id) || node.position),
    }))
    flowEdges.value = arrangedEdges.map((edge) => toVueEdge(edge, arrangedEdges))
    const current = scope.capture()
    nextTick(() => { if (current()) fitView({ padding: 0.35, maxZoom: UI_FLOW_INITIAL_MAX_ZOOM, duration: 200 }) })
  }

  function compareNodePosition(left: UINode, right: UINode) {
    return left.position.y - right.position.y || left.position.x - right.position.x
  }

  function layoutSequentialFlow(
    nodes: UINode[],
    edges: UIEdge[],
    positions: Map<string, Position>,
    startX: number,
    startY: number,
    horizontalGap: number,
    verticalGap: number
  ) {
    const nodeMap = new Map(nodes.map((node) => [node.id, node]))
    const outgoing = new Map<string, UIEdge>()
    const incomingIds = new Set<string>()
    edges.forEach((edge) => {
      outgoing.set(edge.source.node_id, edge)
      incomingIds.add(edge.target.node_id)
    })
    const visited = new Set<string>()
    const chains: string[][] = []
    const starts = nodes.filter((node) => !incomingIds.has(node.id)).sort(compareNodePosition)
    const appendChain = (startId: string) => {
      if (visited.has(startId)) return
      const chain: string[] = []
      let currentId: string | undefined = startId
      while (currentId && !visited.has(currentId) && nodeMap.has(currentId)) {
        chain.push(currentId)
        visited.add(currentId)
        currentId = outgoing.get(currentId)?.target.node_id
      }
      if (chain.length) chains.push(chain)
    }
    starts.forEach((node) => appendChain(node.id))
    nodes
      .filter((node) => !visited.has(node.id))
      .sort(compareNodePosition)
      .forEach((node) => appendChain(node.id))

    const nodesPerRow = 4
    let groupStartY = startY
    const edgePositions = new Map<
      string,
      { source: ConnectorPosition; target: ConnectorPosition }
    >()
    chains.forEach((chain) => {
      chain.forEach((nodeId, index) => {
        const row = Math.floor(index / nodesPerRow)
        const columnInRow = index % nodesPerRow
        const leftToRight = row % 2 === 0
        const column = leftToRight ? columnInRow : nodesPerRow - 1 - columnInRow
        positions.set(nodeId, {
          x: startX + column * horizontalGap,
          y: groupStartY + row * verticalGap,
        })
        const nextNodeId = chain[index + 1]
        if (!nextNodeId) return
        const edge = edges.find(
          (item) => item.source.node_id === nodeId && item.target.node_id === nextNodeId
        )
        if (!edge) return
        const nextRow = Math.floor((index + 1) / nodesPerRow)
        if (nextRow !== row) {
          edgePositions.set(edge.id, { source: 'bottom', target: 'top' })
        } else if (leftToRight) {
          edgePositions.set(edge.id, { source: 'right', target: 'left' })
        } else {
          edgePositions.set(edge.id, { source: 'left', target: 'right' })
        }
      })
      groupStartY += Math.ceil(chain.length / nodesPerRow) * verticalGap + 80
    })
    return edges.map((edge) => {
      const handles = edgePositions.get(edge.id)
      if (!handles) return edge
      return {
        ...edge,
        source: { ...edge.source, position: handles.source },
        target: { ...edge.target, position: handles.target },
      }
    })
  }

  function layoutBranchingFlow(
    nodes: UINode[],
    edges: UIEdge[],
    positions: Map<string, Position>,
    startX: number,
    startY: number,
    horizontalGap: number,
    verticalGap: number
  ) {
    const nodeMap = new Map(nodes.map((node) => [node.id, node]))
    const indegree = new Map(nodes.map((node) => [node.id, 0]))
    const levels = new Map(nodes.map((node) => [node.id, 0]))
    edges.forEach((edge) => {
      if (indegree.has(edge.target.node_id)) {
        indegree.set(edge.target.node_id, (indegree.get(edge.target.node_id) || 0) + 1)
      }
    })
    const queue = nodes
      .filter((node) => (indegree.get(node.id) || 0) === 0)
      .sort(compareNodePosition)
    const processed = new Set<string>()
    while (queue.length) {
      const node = queue.shift()!
      if (processed.has(node.id)) continue
      processed.add(node.id)
      edges
        .filter((edge) => edge.source.node_id === node.id)
        .forEach((edge) => {
          const targetId = edge.target.node_id
          levels.set(targetId, Math.max(levels.get(targetId) || 0, (levels.get(node.id) || 0) + 1))
          indegree.set(targetId, Math.max(0, (indegree.get(targetId) || 0) - 1))
          if (indegree.get(targetId) === 0 && nodeMap.has(targetId)) {
            queue.push(nodeMap.get(targetId)!)
          }
        })
    }
    nodes.filter((node) => !processed.has(node.id)).forEach((node) => levels.set(node.id, 0))
    const levelNodes = new Map<number, UINode[]>()
    nodes.forEach((node) => {
      const level = levels.get(node.id) || 0
      if (!levelNodes.has(level)) levelNodes.set(level, [])
      levelNodes.get(level)!.push(node)
    })
    const maxNodesAtLevel = Math.max(
      1,
      ...Array.from(levelNodes.values()).map((items) => items.length)
    )
    levelNodes.forEach((items, level) => {
      items.sort((left, right) => {
        const parentCenter = (node: UINode) => {
          const parents = edges
            .filter((edge) => edge.target.node_id === node.id)
            .map((edge) => positions.get(edge.source.node_id)?.x)
            .filter((value): value is number => value !== undefined)
          return parents.length
            ? parents.reduce((sum, value) => sum + value, 0) / parents.length
            : node.position.x
        }
        return parentCenter(left) - parentCenter(right) || compareNodePosition(left, right)
      })
      const rowWidth = (items.length - 1) * horizontalGap
      const maxWidth = (maxNodesAtLevel - 1) * horizontalGap
      const rowStartX = startX + (maxWidth - rowWidth) / 2
      items.forEach((node, index) => {
        positions.set(node.id, {
          x: rowStartX + index * horizontalGap,
          y: startY + level * verticalGap,
        })
      })
    })
  }

  defineExpose({
    clearSelection: () => {
      selectedNodeId.value = ''
      shortcutNodeId.value = ''
      emit('nodeSelect', null)
    },
    selectNode: (nodeId: string) => {
      emitSelectedNode(nodeId)
    },
    getFlowData: () => legacyFlowData.value,
    beautifyLayout,
  })
</script>

<style scoped>
  .flow-container {
    display: grid;
    grid-template-columns: var(--steps-left-panel-width, 220px) minmax(0, 1fr);
    width: 100%;
    height: 100%;
    min-height: 0;
    gap: var(--steps-panel-gap, 12px);
  }

  .flow-container-compact {
    grid-template-columns: minmax(0, 1fr);
  }

  .step-control-panel,
  .step-healing-panel,
  .canvas-nodes-panel,
  .center-panel {
    display: flex;
    min-height: 0;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    overflow: hidden;
  }

  .left-column {
    display: flex;
    width: var(--steps-left-panel-width, 220px);
    min-width: var(--steps-left-panel-width, 220px);
    max-width: var(--steps-left-panel-width, 220px);
    min-height: 0;
    flex-direction: column;
    gap: var(--steps-panel-gap, 12px);
  }

  .step-control-panel {
    flex: none;
  }

  .step-healing-panel {
    flex: none;
  }

  .canvas-nodes-panel {
    flex: 1;
  }

  .center-panel {
    width: 100%;
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

  .flow-head-side {
    display: flex;
    flex: none;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
  }

  .flow-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 6px;
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

  .flow-title-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-top: 2px;
  }

  .flow-title-row .flow-panel-subtitle {
    margin-top: 0;
  }

  .flow-debug-status {
    display: inline-flex;
    align-items: center;
    min-height: 20px;
    padding: 1px 8px;
    color: var(--m-primary);
    font-size: 12px;
    font-weight: 500;
    line-height: 18px;
    border: 1px solid var(--m-primary-border);
    border-radius: var(--m-radius-pill);
    background: var(--m-primary-soft);
  }

  .flow-debug-status-warning {
    color: var(--m-warning);
    border-color: color-mix(in srgb, var(--m-warning) 36%, transparent);
    background: color-mix(in srgb, var(--m-warning) 10%, transparent);
  }

  .flow-debug-status-pending {
    color: var(--m-muted);
    border-color: var(--m-border);
    background: var(--m-surface-soft);
  }

  .flow-debug-status-done {
    color: var(--m-success);
    border-color: color-mix(in srgb, var(--m-success) 36%, transparent);
    background: color-mix(in srgb, var(--m-success) 10%, transparent);
  }

  .flow-debug-status-failed {
    color: var(--m-danger);
    border-color: color-mix(in srgb, var(--m-danger) 36%, transparent);
    background: color-mix(in srgb, var(--m-danger) 10%, transparent);
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
    display: flex;
    flex-direction: column;
    gap: 12px;
    flex: 1;
    min-height: 0;
    padding: 10px;
    overflow: auto;
  }

  .palette-section {
    flex: none;
  }

  .step-healing-summary {
    display: flex;
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 10px 10px 8px;
    color: var(--m-text);
    text-align: left;
    border: 0;
    background: var(--m-surface);
    transition: background-color 160ms ease;
  }

  .step-healing-summary:has(.step-healing-summary__main:hover) {
    background: var(--m-surface-soft);
  }

  .step-healing-summary__main {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 3px;
    padding: 0 2px;
    color: inherit;
    text-align: left;
    border: 0;
    background: transparent;
    cursor: pointer;
  }

  .step-healing-summary__main:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: 2px;
  }

  .step-healing-summary .flow-panel-subtitle {
    display: -webkit-box;
    min-height: 36px;
    margin-top: 0;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .step-healing-summary__footer {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
    min-width: 0;
    color: var(--m-primary);
    font-size: 12px;
    line-height: 18px;
  }

  .step-healing-status {
    color: var(--m-muted);
    font-weight: 500;
    white-space: nowrap;
  }

  .step-healing-status--enabled {
    color: var(--m-success);
  }

  .step-healing-status--pending {
    color: var(--m-warning);
  }

  .step-healing-summary__actions {
    justify-content: flex-end;
  }

  .step-control-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
  }

  .step-control-item {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
  }

  .step-control-item > span {
    min-width: 0;
  }

  .step-control-item :deep(.arco-input-number) {
    width: 82px;
    flex: none;
  }

  .palette-section-title {
    color: var(--m-text);
    font-size: 12px;
    font-weight: 600;
    line-height: 18px;
  }

  .palette-section-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .node-types {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .node-type-card {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    gap: 9px;
    padding: 8px 10px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    cursor: grab;
    transition: all 0.2s;
  }

  .node-type-card:hover {
    border-color: var(--m-primary-border);
    background: var(--m-primary-soft);
  }

  .node-type-card:active {
    cursor: grabbing;
  }

  .node-type-card span:last-child {
    overflow: hidden;
    color: var(--m-text);
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .color-dot {
    flex-shrink: 0;
    width: 8px;
    height: 8px;
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

  .step-handle-side {
    opacity: 0;
    transition: opacity 0.16s ease;
  }

  .step-node:hover .step-handle-side,
  .step-node.mango-ui-flow-node--selected .step-handle-side {
    opacity: 1;
  }

  .step-handle-left {
    left: -7px;
  }

  .step-handle-right {
    right: -7px;
  }

  :deep(.vue-flow__edge-path) {
    stroke: var(--m-muted);
    stroke-width: 2;
  }

  :deep(.vue-flow__edge.selected .vue-flow__edge-path),
  :deep(.vue-flow__edge:hover .vue-flow__edge-path) {
    stroke: var(--m-primary);
  }

  :deep(.vue-flow__edge.flow-edge-pending .vue-flow__edge-path),
  :deep(.vue-flow__edge.flow-edge-pending.selected .vue-flow__edge-path),
  :deep(.vue-flow__edge.flow-edge-pending:hover .vue-flow__edge-path) {
    stroke: var(--m-muted);
  }

  :deep(.vue-flow__edge.flow-edge-passed .vue-flow__edge-path),
  :deep(.vue-flow__edge.flow-edge-passed.selected .vue-flow__edge-path),
  :deep(.vue-flow__edge.flow-edge-passed:hover .vue-flow__edge-path) {
    stroke: var(--m-success);
  }

  :deep(.vue-flow__edge.flow-edge-failed .vue-flow__edge-path),
  :deep(.vue-flow__edge.flow-edge-failed.selected .vue-flow__edge-path),
  :deep(.vue-flow__edge.flow-edge-failed:hover .vue-flow__edge-path) {
    stroke: var(--m-danger);
  }

  :deep(.vue-flow__edge.flow-edge-decision .vue-flow__edge-path) {
    stroke-dasharray: 8 8;
  }

  :deep(.vue-flow__edge.flow-edge-running .vue-flow__edge-path),
  :deep(.vue-flow__edge.flow-edge-running.selected .vue-flow__edge-path),
  :deep(.vue-flow__edge.flow-edge-running:hover .vue-flow__edge-path) {
    stroke: var(--m-primary);
    stroke-dasharray: 8 8;
    animation: mango-flow-edge-running 1.1s linear infinite;
  }

  @keyframes mango-flow-edge-running {
    from {
      stroke-dashoffset: 16;
    }

    to {
      stroke-dashoffset: 0;
    }
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
