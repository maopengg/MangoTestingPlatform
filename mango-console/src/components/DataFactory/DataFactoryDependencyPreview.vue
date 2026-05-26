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
      <DataFactoryRelationFlow
        :dependency-tree="dependencyTree"
        :focus-node-key="focusNodeKey"
        :editable-root="editableRoot"
        :flow-loading="flowLoading"
        title="依赖关系"
        subtitle="展示场景入口、关联模板和字段依赖，点击节点查看字段生成明细"
        @select-node="onRelationNodeSelect"
      >
        <template #extra>
          <a-button size="mini" type="primary" @click.stop="flowDrawerVisible = true">
            放大查看
          </a-button>
        </template>
      </DataFactoryRelationFlow>

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
          <div v-if="currentNodeFields.length" class="mango-field-editor-body">
            <TemplateFieldConfigEditor
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
          </div>
          <div v-else class="mango-empty-state mango-dependency-empty">当前节点暂无字段明细</div>
        </a-spin>
      </div>
    </div>
  </div>

  <a-drawer
    v-model:visible="flowDrawerVisible"
    title="依赖关系 / 放大查看"
    width="76%"
    :footer="false"
    unmount-on-close
  >
    <div class="mango-relation-drawer-body">
      <DataFactoryRelationFlow
        :dependency-tree="dependencyTree"
        :focus-node-key="focusNodeKey"
        :editable-root="editableRoot"
        :flow-loading="flowLoading"
        title="依赖关系"
        subtitle="展示场景入口、关联模板和字段依赖"
        height="calc(100vh - 110px)"
        :initial-max-zoom="0.82"
        show-download
        show-mini-map
        download-name="数据工厂依赖关系"
        @select-node="onRelationNodeSelect"
      />
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { computed, ref } from 'vue'
  import DataFactoryRelationFlow from '@/components/DataFactory/DataFactoryRelationFlow.vue'
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
    missing_fields?: any[]
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
      fieldTableScrollY: 'calc(100vh - 320px)',
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
    (event: 'openTemplate', value?: PreviewNode): void
  }>()

  const selectedNode = ref<PreviewNode>()
  const flowDrawerVisible = ref(false)

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

  function onRelationNodeSelect(payload: { id: string; node?: PreviewNode }) {
    selectedNode.value = payload.node
  }

  function flattenTree(tree?: PreviewNode | null): Array<{ node: PreviewNode }> {
    if (!tree) {
      return []
    }
    return [{ node: tree }, ...(tree.children || []).flatMap((child) => flattenTree(child))]
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
    grid-template-columns: minmax(380px, 34%) minmax(0, 1fr);
    gap: 12px;
    min-height: 0;
    flex: 1;
  }

  .mango-field-panel {
    display: flex;
    overflow: hidden;
    flex-direction: column;
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-field-spin {
    display: block;
    height: 100%;
    min-height: 0;
    flex: 1;
  }

  .mango-field-spin :deep(.arco-spin),
  .mango-field-spin :deep(.arco-spin-children) {
    height: 100%;
    min-height: 0;
  }

  .mango-field-spin :deep(.arco-spin-children) {
    display: flex;
    overflow: hidden;
    flex-direction: column;
  }

  .mango-field-editor-body {
    overflow: hidden;
    flex: 1;
    min-height: 0;
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

  .mango-relation-drawer-body {
    height: calc(100vh - 110px);
    min-height: 0;
  }

  @media (max-width: 1px) {
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
