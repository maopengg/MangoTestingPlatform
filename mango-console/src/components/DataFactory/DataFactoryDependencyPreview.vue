<template>
  <div class="mango-data-factory-preview">
    <div class="mango-preview-summary">
      <a-alert :type="canDebugRun ? 'success' : 'warning'" class="mango-summary-alert" show-icon>
        {{
          canDebugRun
            ? '当前依赖链路已能生成数据，可以继续调试运行。'
            : `当前依赖链路还有 ${summary.missingCount} 个字段需要配置，暂不能调试运行。`
        }}
      </a-alert>
      <div class="mango-summary-metrics">
        <div class="mango-metric-item">
          <span class="mango-metric-value">{{ summary.nodeCount }}</span>
          <span class="mango-metric-label">实体</span>
        </div>
        <div class="mango-metric-item">
          <span class="mango-metric-value">{{ summary.dependencyCount }}</span>
          <span class="mango-metric-label">依赖</span>
        </div>
        <div class="mango-metric-item">
          <span class="mango-metric-value">{{ summary.createCount }}</span>
          <span class="mango-metric-label">创建</span>
        </div>
        <div class="mango-metric-item">
          <span class="mango-metric-value">{{ summary.reuseCount }}</span>
          <span class="mango-metric-label">复用</span>
        </div>
        <div :class="['mango-metric-item', { 'metric-danger': summary.missingCount }]">
          <span class="mango-metric-value">{{ summary.missingCount }}</span>
          <span class="mango-metric-label">缺失字段</span>
        </div>
      </div>
    </div>

    <div class="mango-preview-body">
      <div class="mango-flow-panel">
        <div class="mango-panel-header">
          <div>
            <div class="mango-panel-title">依赖关系</div>
            <div class="mango-panel-subtitle">当前模板的局部依赖，点击非复用节点查看字段生成明细</div>
          </div>
        </div>
        <a-spin :loading="flowLoading" class="mango-flow-spin" tip="依赖关系加载中...">
          <div ref="flowCanvasRef" class="mango-flow-canvas">
            <VueFlow
              :id="flowId"
              v-model:nodes="flowNodes"
              v-model:edges="flowEdges"
              class="mango-relation-flow"
              :nodes-draggable="false"
              :nodes-connectable="false"
              :elements-selectable="true"
              :min-zoom="0.25"
              :max-zoom="1.2"
              @pane-ready="onFlowPaneReady"
              @nodes-initialized="onFlowNodesInitialized"
              @node-click="onNodeClick"
            >
              <template #node-tableNode="{ data }">
                <div
                  :class="[
                    'table-node',
                    `table-node-${data.status || 'valid'}`,
                    { 'table-node-selected': selectedNodeId === data.nodeId },
                    { 'table-node-disabled': !data.clickable },
                  ]"
                >
                  <div class="mango-node-header">
                    <span class="mango-node-title">{{ data.entityName || data.templateName }}</span>
                    <a-tag v-if="data.reused" color="blue" size="small">复用</a-tag>
                    <a-tag v-else :color="getNodeStatusColor(data.status)" size="small">
                      {{ getNodeStatusText(data.status, data.missingCount) }}
                    </a-tag>
                  </div>
                  <div class="mango-node-table">{{ data.tableName || '-' }}</div>
                  <div class="mango-node-template">{{ data.templateName || '-' }}</div>
                  <div v-if="data.linkText" class="mango-node-link">{{ data.linkText }}</div>
                </div>
              </template>
              <Background pattern-color="var(--m-border)" :gap="18" />
              <Controls />
            </VueFlow>
          </div>
        </a-spin>
      </div>

      <div class="mango-field-panel">
        <div class="mango-field-panel-header">
          <div>
            <div class="mango-field-title">{{
              selectedNode?.entity_name || selectedNode?.template_name || '-'
            }}</div>
            <div class="mango-field-subtitle">
              {{ selectedNode?.table_name || '-' }} / {{ selectedNode?.template_name || '-' }}
            </div>
          </div>
          <a-tag :color="getNodeStatusColor(selectedNode?.status)" size="small">
            {{ getNodeStatusText(selectedNode?.status, selectedNode?.missing_count) }}
          </a-tag>
          <a-button
            v-if="canOpenSelectedTemplate"
            size="mini"
            type="text"
            @click="emit('openTemplate', selectedNode)"
          >
            前往配置该模板
          </a-button>
        </div>
        <a-spin :loading="fieldLoading" class="mango-field-spin" tip="字段明细加载中...">
          <a-alert
            v-if="selectedNodeIssues.length"
            class="mango-node-issues"
            type="warning"
            show-icon
          >
            <div v-for="issue in selectedNodeIssues" :key="`${issue.field}-${issue.message}`">
              {{ issue.message || issue.field }}
            </div>
          </a-alert>
          <TemplateFieldConfigEditor
            v-if="currentNodeFields.length"
            :fields="currentNodeFields"
            :field-overrides="selectedNodeEditable ? currentFieldOverrides : {}"
            :output-config="selectedNodeEditable ? currentOutputConfig : []"
            :generator-options="generatorOptions"
            :dependency-template-options="dependencyTemplateOptions"
            :load-dependency-template-options="loadDependencyTemplateOptions"
            :preview-fields="selectedNodeFields"
            :readonly="!selectedNodeEditable"
            :show-config="selectedNodeEditable"
            :show-output="false"
            :table-scroll-y="fieldTableScrollY"
            show-preview
            @update:field-overrides="updateSelectedNodeOverrides"
            @update:output-config="updateSelectedNodeOutputConfig"
          />
          <div v-else class="mango-empty-state mango-dependency-empty">当前节点暂无字段明细</div>
        </a-spin>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
  import { VueFlow, useVueFlow } from '@vue-flow/core'
  import type { Edge, Node } from '@vue-flow/core'
  import { Background, Controls } from '@vue-flow/additional-components'
  import '@vue-flow/core/dist/style.css'
  import '@vue-flow/core/dist/theme-default.css'
  import TemplateFieldConfigEditor from '@/components/DataFactory/TemplateFieldConfigEditor.vue'

  interface EnumOption {
    key: number | null
    title: string
  }

  interface PreviewNode {
    template_id?: number | null
    template_name?: string
    entity_id?: number | null
    entity_name?: string
    table_name?: string
    alias?: string
    field?: string
    target_field?: string
    action?: string
    reused?: boolean
    scene_item_id?: number | string
    scene_item_name?: string
    status?: string
    missing_count?: number
    fields?: any[]
    children?: PreviewNode[]
  }

  const props = withDefaults(
    defineProps<{
      dependencyTree?: PreviewNode | null
      canDebugRun?: boolean
      generatorOptions: EnumOption[]
      fieldTableScrollY?: number | string
      editableRoot?: boolean
      rootFields?: any[]
      fieldOverrides?: Record<string, any>
      outputConfig?: any[]
      editableNodeConfigs?: Record<string, any>
      dependencyTemplateOptions?: Record<string, any[]>
      loadDependencyTemplateOptions?: (row: any) => void
      focusNodeKey?: string
      flowLoading?: boolean
      fieldLoading?: boolean
    }>(),
    {
      dependencyTree: null,
      canDebugRun: false,
      fieldTableScrollY: 'calc(100vh - 360px)',
      editableRoot: false,
      rootFields: () => [],
      fieldOverrides: () => ({}),
      outputConfig: () => [],
      editableNodeConfigs: () => ({}),
      dependencyTemplateOptions: () => ({}),
      loadDependencyTemplateOptions: undefined,
      focusNodeKey: 'root',
      flowLoading: false,
      fieldLoading: false,
    }
  )

  const emit = defineEmits<{
    (event: 'update:fieldOverrides', value: Record<string, any>): void
    (event: 'update:outputConfig', value: any[]): void
    (event: 'updateNodeFieldOverrides', key: string, value: Record<string, any>): void
    (event: 'updateNodeOutputConfig', key: string, value: any[]): void
    (event: 'openTemplate', value: PreviewNode): void
  }>()

  const selectedNodeId = ref('')
  const flowNodes = ref<Node[]>([])
  const flowEdges = ref<Edge[]>([])
  const flowCanvasRef = ref<HTMLElement>()
  const flowPaneReady = ref(false)
  const fitFrameId = ref<number>()
  const fitTimerId = ref<number>()
  const flowId = 'mango-data-factory-dependency-flow'
  const INITIAL_MAX_ZOOM = 0.62
  const nodeMap = computed(() => {
    const map = new Map<string, PreviewNode>()
    flattenTree(focusedDependencyTree.value).forEach((item) => map.set(item.id, item.node))
    return map
  })
  const focusedDependencyTree = computed(() => {
    return (
      findNodeByEditableKey(props.dependencyTree, props.focusNodeKey || 'root') ||
      props.dependencyTree
    )
  })
  const selectedNode = computed(() => nodeMap.value.get(selectedNodeId.value))
  const selectedNodeFields = computed(() => selectedNode.value?.fields || [])
  const selectedNodeIssues = computed(() => selectedNode.value?.missing_fields || [])
  const selectedEditableKey = computed(() => getEditableNodeKey(selectedNode.value))
  const selectedEditableConfig = computed(() => {
    if (selectedEditableKey.value === 'root') {
      return {
        fields: props.rootFields,
        fieldOverrides: props.fieldOverrides,
        outputConfig: props.outputConfig,
      }
    }
    return selectedEditableKey.value ? props.editableNodeConfigs?.[selectedEditableKey.value] : null
  })
  const selectedNodeEditable = computed(() => Boolean(selectedEditableConfig.value))
  const canOpenSelectedTemplate = computed(() => {
    return Boolean(
      selectedNode.value?.template_id &&
        selectedNode.value.action !== 'root' &&
        selectedNode.value.action !== 'reuse' &&
        !selectedNode.value.reused
    )
  })
  const currentNodeFields = computed(() => {
    if (selectedNodeEditable.value && selectedEditableConfig.value?.fields?.length) {
      return selectedEditableConfig.value.fields
    }
    return selectedNodeFields.value
  })
  const currentFieldOverrides = computed(
    () => selectedEditableConfig.value?.fieldOverrides || props.fieldOverrides
  )
  const currentOutputConfig = computed(
    () => selectedEditableConfig.value?.outputConfig || props.outputConfig
  )
  const summary = computed(() => {
    const items = flattenTree(props.dependencyTree)
    return {
      nodeCount: items.length,
      dependencyCount: Math.max(items.length - 1, 0),
      createCount: items.filter(
        (item) => item.node.action === 'create' || item.node.action === 'root'
      ).length,
      reuseCount: items.filter((item) => item.node.reused || item.node.action === 'reuse').length,
      missingCount: items.reduce((total, item) => total + Number(item.node.missing_count || 0), 0),
    }
  })
  const { fitView, areNodesInitialized } = useVueFlow(flowId)

  watch(
    () => props.dependencyTree,
    () => {
      buildFlow()
      scheduleFitView()
    },
    { immediate: true, deep: true }
  )

  watch(
    () => props.focusNodeKey,
    () => {
      buildFlow()
      scheduleFitView()
    }
  )

  watch(
    () => props.flowLoading,
    (loading) => {
      if (!loading) {
        scheduleFitView()
      }
    }
  )

  watch(areNodesInitialized, (ready) => {
    if (ready) {
      scheduleFitView()
    }
  })

  onBeforeUnmount(() => {
    cancelScheduledFitView()
  })

  function onFlowPaneReady() {
    flowPaneReady.value = true
    scheduleFitView()
  }

  function onFlowNodesInitialized() {
    scheduleFitView()
  }

  function cancelScheduledFitView() {
    if (fitFrameId.value) {
      window.cancelAnimationFrame(fitFrameId.value)
      fitFrameId.value = undefined
    }
    if (fitTimerId.value) {
      window.clearTimeout(fitTimerId.value)
      fitTimerId.value = undefined
    }
  }

  function scheduleFitView(retry = 0) {
    cancelScheduledFitView()
    nextTick(() => {
      fitFrameId.value = window.requestAnimationFrame(() => {
        const rect = flowCanvasRef.value?.getBoundingClientRect()
        const canFit =
          flowPaneReady.value &&
          areNodesInitialized.value &&
          flowNodes.value.length > 0 &&
          rect &&
          rect.width > 80 &&
          rect.height > 80

        if (!canFit) {
          if (retry < 8) {
            fitTimerId.value = window.setTimeout(() => scheduleFitView(retry + 1), 80)
          }
          return
        }

        fitView({
          padding: 0.38,
          maxZoom: INITIAL_MAX_ZOOM,
          duration: retry ? 0 : 180,
        })

        if (retry === 0) {
          fitTimerId.value = window.setTimeout(() => scheduleFitView(1), 120)
        }
      })
    })
  }

  function buildFlow() {
    const nodes: Node[] = []
    const edges: Edge[] = []
    const levels: Record<number, number> = {}

    function walk(node: PreviewNode, level = 0, indexPath = '0') {
      const id = buildNodeId(node, indexPath)
      levels[level] = levels[level] || 0
      const row = levels[level]
      levels[level] += 1
      nodes.push({
        id,
        type: 'tableNode',
        position: { x: level * 248, y: row * 126 },
        selectable: node.action !== 'reuse' && !node.reused,
        data: {
          nodeId: id,
          templateName: node.template_name || node.alias || '-',
          entityName: node.entity_name || node.alias || '-',
          tableName: node.table_name || '',
          status: node.status || 'valid',
          missingCount: node.missing_count || 0,
          clickable: node.action !== 'reuse' && !node.reused,
          reused: node.action === 'reuse' || node.reused,
          linkText: node.field ? `${node.field} -> ${node.target_field || 'id'}` : '',
        },
      })
      ;(node.children || []).forEach((child, childIndex) => {
        const childId = buildNodeId(child, `${indexPath}-${childIndex}`)
        edges.push({
          id: `${id}-${childId}`,
          source: id,
          target: childId,
          label: child.field ? `${child.field} -> ${child.target_field || 'id'}` : '',
          type: 'smoothstep',
          animated: child.action === 'create',
          style: { stroke: child.status === 'warning' ? 'var(--m-warning)' : 'var(--m-muted)' },
          labelStyle: { fill: 'var(--m-text-2)', fontSize: 12 },
          labelBgStyle: { fill: 'var(--m-surface)', fillOpacity: 0.85 },
        })
        walk(child, level + 1, `${indexPath}-${childIndex}`)
      })
    }

    if (focusedDependencyTree.value) {
      walk(focusedDependencyTree.value)
    }
    flowNodes.value = nodes
    flowEdges.value = edges
    selectedNodeId.value = nodes.some((node) => node.id === selectedNodeId.value)
      ? selectedNodeId.value
      : nodes[0]?.id || ''
  }

  function flattenTree(
    tree?: PreviewNode | null,
    indexPath = '0'
  ): Array<{ id: string; node: PreviewNode }> {
    if (!tree) {
      return []
    }
    const id = buildNodeId(tree, indexPath)
    return [
      { id, node: tree },
      ...(tree.children || []).flatMap((child, index) =>
        flattenTree(child, `${indexPath}-${index}`)
      ),
    ]
  }

  function buildNodeId(node: PreviewNode, indexPath: string) {
    return `node-${
      node.scene_item_id || node.template_id || node.entity_id || node.alias || indexPath
    }-${indexPath}`
  }

  function getEditableNodeKey(node?: PreviewNode) {
    if (!node) {
      return ''
    }
    if (node.action === 'root' && props.editableRoot) {
      return 'root'
    }
    if (node.scene_item_id !== undefined && node.scene_item_id !== null) {
      return `item:${node.scene_item_id}`
    }
    return ''
  }

  function findNodeByEditableKey(tree?: PreviewNode | null, key = 'root'): PreviewNode | null {
    if (!tree) {
      return null
    }
    if (getEditableNodeKey(tree) === key) {
      return tree
    }
    for (const child of tree.children || []) {
      const found = findNodeByEditableKey(child, key)
      if (found) {
        return found
      }
    }
    return null
  }

  function updateSelectedNodeOverrides(value: Record<string, any>) {
    const key = selectedEditableKey.value
    if (!key || key === 'root') {
      emit('update:fieldOverrides', value)
      return
    }
    emit('updateNodeFieldOverrides', key, value)
  }

  function updateSelectedNodeOutputConfig(value: any[]) {
    const key = selectedEditableKey.value
    if (!key || key === 'root') {
      emit('update:outputConfig', value)
      return
    }
    emit('updateNodeOutputConfig', key, value)
  }

  function onNodeClick(event: any) {
    if (!event.node?.data?.clickable) {
      return
    }
    selectedNodeId.value = event.node?.id || ''
  }

  function getNodeStatusColor(status?: string) {
    if (status === 'warning') {
      return 'orange'
    }
    if (status === 'error') {
      return 'red'
    }
    return 'green'
  }

  function getNodeStatusText(status?: string, missingCount?: number) {
    if (status === 'warning') {
      return `缺 ${missingCount || 0} 项`
    }
    if (status === 'error') {
      return '异常'
    }
    return '可生成'
  }
</script>

<style scoped lang="less">
  .mango-data-factory-preview {
    display: flex;
    flex-direction: column;
    gap: 10px;
    height: 100%;
    min-height: 0;
  }

  .mango-preview-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-summary-alert {
    flex: 1;
    min-width: 320px;
    border: 0;
    background: transparent;
    padding-left: 0;
  }

  .mango-summary-metrics {
    display: grid;
    grid-template-columns: repeat(5, minmax(58px, 1fr));
    gap: 8px;
    flex-shrink: 0;
    min-width: 360px;
  }

  .mango-metric-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 48px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-metric-value {
    color: var(--m-text);
    font-size: 18px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-metric-label {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .metric-danger {
    border-color: color-mix(in srgb, var(--m-danger) 34%, transparent);
    background: color-mix(in srgb, var(--m-danger) 10%, transparent);
  }

  .metric-danger .mango-metric-value {
    color: var(--m-danger);
  }

  .mango-preview-body {
    display: grid;
    grid-template-columns: minmax(430px, 40%) minmax(560px, 1fr);
    gap: 12px;
    min-height: 0;
    flex: 1;
  }

  .mango-flow-panel,
  .mango-field-panel {
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-flow-panel {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .mango-flow-spin,
  .mango-field-spin {
    display: block;
    height: 100%;
    min-height: 0;
    flex: 1;
  }

  .mango-flow-spin :deep(.arco-spin),
  .mango-flow-spin :deep(.arco-spin-children),
  .mango-field-spin :deep(.arco-spin),
  .mango-field-spin :deep(.arco-spin-children) {
    height: 100%;
    min-height: 0;
  }

  .mango-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-panel-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-panel-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-flow-canvas {
    flex: 1;
    height: 100%;
    min-height: 0;
  }

  .mango-relation-flow {
    width: 100%;
    height: 100%;
    background: linear-gradient(
        180deg,
        color-mix(in srgb, var(--m-surface) 72%, transparent),
        color-mix(in srgb, var(--m-surface-soft) 85%, transparent)
      ),
      var(--m-surface-soft);
  }

  .table-node {
    width: 206px;
    padding: 10px 11px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    cursor: pointer;
    box-shadow: var(--m-shadow);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .table-node-selected {
    border-color: var(--m-primary);
    box-shadow: var(--m-form-focus-shadow);
  }

  .table-node-disabled {
    cursor: not-allowed;
    opacity: 0.72;
  }

  .table-node-warning {
    border-color: var(--m-warning);
  }

  .table-node-error {
    border-color: var(--m-danger);
  }

  .mango-node-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-node-title {
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-node-table,
  .mango-node-template,
  .mango-node-link {
    overflow: hidden;
    margin-top: 4px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-node-link {
    color: var(--m-primary);
  }

  .mango-field-panel {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .mango-field-panel-header {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 12px;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-field-panel-header > div:first-child {
    flex: 1;
    min-width: 0;
  }

  .mango-node-issues {
    box-sizing: border-box;
    width: calc(100% - 24px);
    max-width: calc(100% - 24px);
    margin: 10px 12px 10px;
    overflow: hidden;
    flex-shrink: 0;
  }

  .mango-node-issues :deep(.arco-alert-content) {
    min-width: 0;
  }

  .mango-node-issues :deep(.arco-alert-description),
  .mango-node-issues :deep(.arco-alert-content) {
    white-space: normal;
    word-break: break-word;
  }

  .mango-field-panel :deep(.arco-table-container) {
    border-radius: 0;
  }

  .mango-field-panel :deep(.arco-table),
  .mango-field-panel :deep(.arco-table-content),
  .mango-field-panel :deep(.arco-table-border),
  .mango-field-panel :deep(.arco-table-scroll-position-left),
  .mango-field-panel :deep(.arco-table-scroll-position-right),
  .mango-field-panel :deep(.arco-table-body),
  .mango-field-panel :deep(.arco-table-td),
  .mango-field-panel :deep(.arco-table-th) {
    border-radius: 0 !important;
  }

  .mango-field-panel :deep(.arco-table-th) {
    background: var(--m-table-header-bg);
  }

  .mango-field-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-field-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-dependency-empty {
    margin: 12px;
    min-height: 160px;
  }

  @media (max-width: 1100px) {
    .mango-preview-summary {
      align-items: stretch;
      flex-direction: column;
    }

    .mango-summary-metrics {
      width: 100%;
      min-width: 0;
    }

    .mango-preview-body {
      grid-template-columns: 1fr;
    }
  }
</style>
