<template>
  <a-drawer v-model:visible="visible" :width="860" title="API 执行链路">
    <mango-panel-spin :loading="loading" class="mango-trace-drawer-spin">
      <MangoRequestFeedback v-if="errorText" :message="(errorText)"><a-button size="small" :loading="loading" @click="loadTrace">重试</a-button></MangoRequestFeedback>
      <div v-else-if="!trace" class="mango-empty-state">
        {{ loading ? '正在加载执行链路' : '本次执行没有链路记录，请重试该 API 用例后再查看' }}
      </div>
      <div v-else class="mango-trace-panel">
        <div class="mango-trace-summary">
          <div><span>Trace ID</span><strong :title="trace.trace_id">{{ trace.trace_id }}</strong></div>
          <div><span>状态</span><a-tag :color="statusColor(trace.status)" size="small">{{ trace.status === 3 && trace.execution_phase === 'automatic_recovery'
            ? enumStore.report_execution_phase[trace.execution_phase]?.title || '自动恢复中' : traceStatusText(trace.status) }}</a-tag></div>
          <div><span>耗时</span><strong>{{ trace.duration_ms ?? '-' }} ms</strong></div>
          <div><span>触发时间</span><strong>{{ trace.started_at || '-' }}</strong></div>
          <div><span>完成时间</span><strong>{{ trace.finished_at || '-' }}</strong></div>
          <div><span>执行来源</span><strong>{{ traceSourceText(trace.source_type) }}</strong></div>
          <div><span>执行节点</span><strong :title="trace.worker_name">{{ trace.worker_name || '-' }}</strong></div>
        </div>
        <div class="mango-trace-flow-layout">
          <div class="mango-trace-flow">
            <button v-for="node in visibleNodes" :key="node.id" type="button"
              class="mango-trace-node" :class="[traceNodeClass(node.status), { 'is-active': selectedNode?.id === node.id }]"
              :aria-pressed="selectedNode?.id === node.id"
              :style="{ marginLeft: `${scaleDensityPixels(nodeDepth(node) * 18)}px` }"
              @click="selectNode(node)">
              <span class="mango-trace-node__toggle"
                :class="{ 'is-visible': hasChildren(node), 'is-expanded': expandedIds.includes(node.id) }"
                @click.stop="toggleNode(node)"></span>
              <span class="mango-trace-node__dot"></span>
              <span class="mango-trace-node__body"><strong>{{ node.label }}</strong><span>{{ node.step_type }} / {{ node.duration_ms ?? '-' }} ms</span></span>
            </button>
          </div>
          <div class="mango-trace-node-detail">
            <template v-if="selectedNode">
              <div class="mango-trace-node-detail__title"><strong>{{ selectedNode.label }}</strong><a-tag :color="statusColor(selectedNode.status)" size="small">{{ traceStatusText(selectedNode.status) }}</a-tag></div>
              <div v-if="selectedNode.error_message" class="mango-trace-step__error">{{ selectedNode.error_message }}</div>
              <div class="mango-trace-node-detail__meta">引用：{{ selectedNode.detail_ref_type || '-' }} / {{ selectedNode.detail_ref_id ?? '-' }}</div>
              <pre class="mango-trace-json">{{ formatTraceSummary(selectedNode.summary) }}</pre>
            </template>
            <div v-else class="mango-empty-state">选择节点查看摘要</div>
          </div>
        </div>
      </div>
    </mango-panel-spin>
  </a-drawer>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { getSystemTestSuiteDetailsExecutionTrace } from '@/api/system/test_sute_details'
  import { useUserStoreContext } from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import {
    formatTraceSummary, parseReportTrace, reportTraceQuery, traceAncestors, traceNodeClass,
    traceSourceText, traceStatusText,
    type ReportTrace, type ReportTraceNode, type ReportTraceQuery,
  } from '../execution-trace'

  const props = defineProps<{ reportId: string }>()
  const route = useRoute(), userStore = useUserStoreContext(), enumStore = useEnum()
  const visible = ref(false), loading = ref(false), errorText = ref('')
  const trace = ref<ReportTrace | null>(null), nodes = ref<ReportTraceNode[]>([])
  const selectedId = ref<string | null>(null), expandedIds = ref<string[]>([])
  const nodeMap = computed(() => new Map(nodes.value.map(node => [node.id, node])))
  const selectedNode = computed(() => selectedId.value === null ? null : nodeMap.value.get(selectedId.value) ?? null)
  const visibleNodes = computed(() => nodes.value.filter(node =>
    traceAncestors(node, nodeMap.value).every(parent => parent.step_type !== 'retry_round' || expandedIds.value.includes(parent.id))
  ))
  let version = 0, active = true, disposed = false
  let query: ReportTraceQuery | null = null
  let pending: { version: number; promise: Promise<void> } | null = null
  const available = () => !disposed && active && visible.value && document.visibilityState === 'visible'

  function resetEvidence() {
    trace.value = null
    nodes.value = []
    selectedId.value = null
    expandedIds.value = []
  }
  function invalidate() {
    version += 1
    loading.value = false
    errorText.value = ''
    resetEvidence()
  }
  function close() {
    visible.value = false
    query = null
    invalidate()
  }
  function open(input: ReportTraceQuery): Promise<void> {
    const next = reportTraceQuery(input)
    if (!next || disposed) return Promise.resolve()
    if (!visible.value || JSON.stringify(next) !== JSON.stringify(query)) {
      invalidate()
      query = next
      visible.value = true
    }
    return loadTrace()
  }
  function loadTrace(): Promise<void> {
    if (!available() || !query) return Promise.resolve()
    if (pending?.version === version) return pending.promise
    const currentVersion = version, snapshot = { ...query }
    const isCurrent = () => available() && version === currentVersion
    loading.value = true
    errorText.value = ''
    resetEvidence()
    const task = Promise.resolve().then(async () => {
      try {
        if (!isCurrent()) return
        const response: unknown = await getSystemTestSuiteDetailsExecutionTrace({ ...snapshot, include_list: true })
        if (!isCurrent()) return
        const result = parseReportTrace(response, snapshot)
        trace.value = result.trace
        nodes.value = result.nodes
        selectedId.value = result.nodes.find(node => node.status === 0)?.id ?? result.nodes[0]?.id ?? null
        const selected = selectedNode.value
        if (selected) expandedIds.value = traceAncestors(selected, nodeMap.value)
          .filter(node => node.step_type === 'retry_round').map(node => node.id)
      } catch (loadFailure0) {
        if (isCurrent()) (reportLoadError(loadFailure0, "执行链路加载失败，请重试", false), errorText.value = '执行链路加载失败，请重试')
      } finally {
        if (isCurrent()) loading.value = false
        if (pending?.version === currentVersion) pending = null
      }
    })
    pending = { version: currentVersion, promise: task }
    return task
  }
  function selectNode(node: ReportTraceNode) {
    if (available() && visibleNodes.value.some(item => item.id === node.id)) selectedId.value = node.id
  }
  function hasChildren(node: ReportTraceNode) {
    return node.step_type === 'retry_round' && nodes.value.some(item => item.parent_step_id === node.id)
  }
  function toggleNode(node: ReportTraceNode) {
    if (!available() || !nodeMap.value.has(node.id) || !hasChildren(node)) return
    if (expandedIds.value.includes(node.id)) {
      expandedIds.value = expandedIds.value.filter(id => id !== node.id)
      if (selectedNode.value && traceAncestors(selectedNode.value, nodeMap.value).some(parent => parent.id === node.id)) selectedId.value = node.id
    } else expandedIds.value = [...expandedIds.value, node.id]
  }
  function nodeDepth(node: ReportTraceNode) { return Math.min(3, traceAncestors(node, nodeMap.value).length) }
  function statusColor(status: number | null) { return status === null ? 'gray' : enumStore.status_colors?.[status] || 'gray' }
  function pause() { invalidate() }
  function visibilityChanged() {
    if (document.visibilityState === 'visible') void loadTrace()
    else pause()
  }
  watch(() => visible.value, value => { if (!value) close() }, { flush: 'sync' })
  watch(() => [props.reportId, route.fullPath, userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment], close, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onDeactivated(() => { active = false; pause() })
  onActivated(() => { const resume = !active; active = true; if (resume) void loadTrace() })
  onBeforeUnmount(() => { disposed = true; active = false; close(); document.removeEventListener('visibilitychange', visibilityChanged) })
  defineExpose({ open, close })
</script>
