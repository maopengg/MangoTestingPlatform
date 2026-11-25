<template>
  <a-drawer v-model:visible="state.visible" :width="860" title="API 执行链路">
    <a-spin :loading="state.loading" class="mango-trace-drawer-spin">
      <div v-if="!state.trace" class="mango-trace-empty">暂无执行链路</div>
      <div v-else class="mango-trace-panel">
        <div class="mango-trace-summary">
          <div>
            <span>Trace ID</span>
            <strong>{{ state.trace.trace_id }}</strong>
          </div>
          <div>
            <span>状态</span>
            <a-tag :color="statusColor(state.trace.status)" size="small">
              {{ state.trace.status === 3 && state.trace.execution_phase === 'automatic_recovery'
                ? enumStore.report_execution_phase[state.trace.execution_phase]?.title || '自动恢复中'
                : enumStore.task_status?.[state.trace.status]?.title || statusText(state.trace.status) }}
            </a-tag>
          </div>
          <div>
            <span>执行版本</span>
            <strong>{{ state.trace.summary?.execution_source === 'editing' ? '当前编辑态'
              : state.trace.summary?.version_label || (state.trace.summary?.case_revision_no
                ? `修订 r${state.trace.summary.case_revision_no}` : '历史记录未标注版本') }}</strong>
          </div>
          <div>
            <span>执行环境</span>
            <strong>{{ state.trace.test_env == null ? '历史记录未标注环境'
              : enumStore.environment_type?.[state.trace.test_env]?.title || state.trace.test_env }}</strong>
          </div>
          <div v-if="state.trace.test_suite_id">
            <span>执行报告</span>
            <router-link :to="{ path: '/report/system/details', query: { id: state.trace.test_suite_id } }">
              {{ state.trace.test_suite_id }}
            </router-link>
          </div>
          <div>
            <span>耗时</span>
            <strong>{{ state.trace.duration_ms || 0 }} ms</strong>
          </div>
          <div>
            <span>触发时间</span>
            <strong>{{ state.trace.started_at || '-' }}</strong>
          </div>
          <div>
            <span>完成时间</span>
            <strong>{{ state.trace.finished_at || '-' }}</strong>
          </div>
          <div>
            <span>执行来源</span>
            <strong>{{ sourceText(state.trace.source_type) }}</strong>
          </div>
          <div>
            <span>执行节点</span>
            <strong>{{ state.trace.worker_name || '-' }}</strong>
          </div>
        </div>
        <div class="mango-trace-flow-layout">
          <div class="mango-trace-flow">
            <button
              v-for="node in visibleNodes"
              :key="node.id"
              type="button"
              class="mango-trace-node"
              :class="[nodeClass(node.status), { 'is-active': state.selectedNode?.id === node.id }]"
              :style="{ marginLeft: `${scaleDensityPixels(nodeDepth(node) * 18)}px` }"
              @click="state.selectedNode = node"
            >
              <span
                class="mango-trace-node__toggle"
                :class="{
                  'is-visible': nodeHasChildren(node),
                  'is-expanded': nodeExpanded(node),
                }"
                @click.stop="toggleNode(node)"
              ></span>
              <span class="mango-trace-node__dot"></span>
              <span class="mango-trace-node__body">
                <strong>{{ node.label }}</strong>
                <span>{{ node.step_type }} / {{ node.duration_ms || 0 }} ms</span>
              </span>
            </button>
          </div>
          <div class="mango-trace-node-detail">
            <template v-if="state.selectedNode">
              <div class="mango-trace-node-detail__title">
                <strong>{{ state.selectedNode.label }}</strong>
                <a-tag :color="statusColor(state.selectedNode.status)" size="small">
                  {{ statusText(state.selectedNode.status) }}
                </a-tag>
              </div>
              <div v-if="state.selectedNode.error_message" class="mango-trace-step__error">
                {{ state.selectedNode.error_message }}
              </div>
              <div class="mango-trace-node-detail__meta">
                <span>
                  引用：{{ state.selectedNode.detail_ref_type || '-' }} /
                  {{ state.selectedNode.detail_ref_id || '-' }}
                </span>
              </div>
              <pre class="mango-trace-json">{{ formatSummary(state.selectedNode.summary) }}</pre>
            </template>
            <div v-else class="mango-trace-empty">选择节点查看摘要</div>
          </div>
        </div>
      </div>
    </a-spin>
  </a-drawer>
</template>

<script setup lang="ts">
  import { computed, reactive, watch, onBeforeUnmount, onDeactivated } from 'vue'
  import { createCaseRequestScope } from '../request-scope'
  import { Message } from '@arco-design/web-vue'
  import { getSystemTestSuiteDetailsExecutionTrace } from '@/api/system/test_sute_details'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { useEnum } from '@/store/modules/get-enum'
  import type { ApiCaseExecutionTraceQuery, CaseTrace, CaseTraceNode } from '../types'

  const requests = createCaseRequestScope()
  const enumStore = useEnum()
  const state = reactive({
    visible: false,
    loading: false,
    trace: null as CaseTrace | null,
    nodes: [] as CaseTraceNode[],
    selectedNode: null as CaseTraceNode | null,
    expandedNodeIds: [] as string[],
  })
  const nodeMap = computed(
    () => new Map(state.nodes.map((node: CaseTraceNode) => [String(node.id), node]))
  )
  const visibleNodes = computed(() =>
    state.nodes.filter((node: CaseTraceNode) => {
      const visited = new Set<string>([String(node.id)])
      let parent = node.parent_step_id ? nodeMap.value.get(String(node.parent_step_id)) : null
      while (parent) {
        if (visited.has(String(parent.id))) return false
        visited.add(String(parent.id))
        if (
          parent.step_type === 'retry_round' &&
          !state.expandedNodeIds.includes(String(parent.id))
        ) {
          return false
        }
        parent = parent.parent_step_id ? nodeMap.value.get(String(parent.parent_step_id)) : null
      }
      return true
    })
  )

  async function open(query: ApiCaseExecutionTraceQuery) {
    if (!query.result_id && !query.trace_id && !query.test_suite_detail_id && !query.case_id) return
    const isCurrent = requests.begin('trace')
    state.visible = true
    state.loading = true
    state.trace = null
    state.nodes = []
    state.selectedNode = null
    state.expandedNodeIds = []
    try {
      const response = await getSystemTestSuiteDetailsExecutionTrace({
        ...query,
        include_list: true,
      })
      if (!isCurrent() || !state.visible) return
      state.trace = response.data?.trace || null
      state.nodes = response.data?.nodes || []
      state.selectedNode =
        state.nodes.find((node: CaseTraceNode) => Number(node.status) === 0) ||
        state.nodes[0] ||
        null
      if (!state.trace) Message.warning('当前用例暂无执行链路记录，请先执行一次用例')
    } catch (error: any) {
      if (isCurrent()) Message.error(error?.msg || error?.message || '执行链路查询失败')
    } finally {
      if (isCurrent()) state.loading = false
    }
  }

  function nodeHasChildren(node: CaseTraceNode) {
    return (
      node.step_type === 'retry_round' &&
      state.nodes.some(
        (item: CaseTraceNode) => String(item.parent_step_id || '') === String(node.id)
      )
    )
  }

  function nodeExpanded(node: CaseTraceNode) {
    return state.expandedNodeIds.includes(String(node.id))
  }

  function toggleNode(node: CaseTraceNode) {
    if (!nodeHasChildren(node)) return
    const id = String(node.id)
    if (nodeExpanded(node)) {
      state.expandedNodeIds = state.expandedNodeIds.filter((item) => item !== id)
      if (String(state.selectedNode?.parent_step_id || '') === id) state.selectedNode = node
    } else {
      state.expandedNodeIds = [...state.expandedNodeIds, id]
    }
  }

  function nodeDepth(node: CaseTraceNode) {
    let depth = 0
    let parent = node.parent_step_id ? nodeMap.value.get(String(node.parent_step_id)) : null
    while (parent && depth < 3) {
      depth += 1
      parent = parent.parent_step_id ? nodeMap.value.get(String(parent.parent_step_id)) : null
    }
    return depth
  }

  function sourceText(sourceType: number) {
    const sourceMap: Record<number, string> = {
      1: '测试报告',
      2: '定时任务',
      3: 'MCP',
      4: '单 Case 执行',
      5: '调试执行',
      6: '其他',
    }
    return sourceMap[Number(sourceType)] || '未知'
  }

  function statusText(status: number) {
    if (Number(status) === 6) return '平台受阻'
    if (Number(status) === 1) return '通过'
    if (Number(status) === 0) return '失败'
    if (Number(status) === 3) return '进行中'
    if (Number(status) === 5) return '跳过'
    if (Number(status) === 4) return '清理失败'
    return '待开始'
  }

  function statusColor(status: number) {
    if (Number(status) === 4) return 'red'
    return enumStore.status_colors?.[Number(status)] || 'gray'
  }

  function nodeClass(status: number) {
    if (Number(status) === 1) return 'is-success'
    if (Number(status) === 0) return 'is-fail'
    if (Number(status) === 3) return 'is-running'
    if (Number(status) === 5) return 'is-skip'
    if (Number(status) === 4) return 'is-warning'
    return 'is-pending'
  }

  function formatSummary(value: any) {
    return JSON.stringify(value || {}, null, 2)
  }

  function close() {
    requests.invalidate()
    state.visible = false
    state.loading = false
  }
  watch(
    () => state.visible,
    (visible) => {
      if (!visible) close()
    }
  )
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>
