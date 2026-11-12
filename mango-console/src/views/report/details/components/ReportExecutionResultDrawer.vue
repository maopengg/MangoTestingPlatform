<template>
  <a-drawer v-model:visible="visible" :width="'min(1280px, 80vw)'" :footer="false"
    title="测试用例详情" class="mango-report-result-drawer" unmount-on-close>
    <div class="mango-report-result-history">
      <ExecutionHistoryList :items="historyItems" :selected-id="selectedResultId" :loading="historyLoading"
        :error-text="historyError" @select="selectResult" @retry="loadHistory" />
      <mango-panel-spin :loading="detailLoading" class="mango-report-result-spin">
        <template v-if="detailError"></template>
        <div v-else-if="!hasDetail" class="mango-empty-state">
          <a-alert data-feedback-kind="execution-result" v-if="selectedCase?.error_message" type="error">{{ selectedCase.error_message }}</a-alert>
          <span>{{ detailLoading ? '正在加载执行结果' : '本次执行没有生成测试结果' }}</span>
        </div>
        <ElementTestReport v-else-if="target?.caseType === 0 && selectedCase" :result-data="selectedCase" />
        <PytestTestReport v-else-if="target?.caseType === 2 && selectedCase" :result-data="selectedCase" />
      </mango-panel-spin>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { useUserStoreContext } from '@/store/modules/user'
  import { getSystemTestSuiteDetailsResultOptionsShare, getSystemTestSuiteDetailsResultShare } from '@/api/system/test_sute_details'
  import ExecutionHistoryList from '@/components/business/ExecutionHistoryList.vue'
  import type { ExecutionHistoryItem } from '@/components/business/execution-history'
  import ElementTestReport from '@/components/reports/ElementTestReport.vue'
  import PytestTestReport from '@/components/reports/PytestTestReport.vue'
  import { createReportReadSession } from '../report-read-session'
  import { buildReportResult, parseReportResult, parseReportResultOptions, reportResultTarget, type ReportResultOption, type ReportResultTarget } from '../report-result'

  const props = defineProps<{ reportId: string }>()
  const route = useRoute(), userStore = useUserStoreContext()
  const visible = ref(false), historyLoading = ref(false), detailLoading = ref(false)
  const historyError = ref(''), detailError = ref('')
  const target = ref<ReportResultTarget | null>(null)
  const selectedCase = ref<Record<string, unknown> | null>(null)
  const options = ref<ReportResultOption[]>([]), selectedResultId = ref<string | null>(null)
  let version = 0, active = true, disposed = false
  let opening: { version: number; promise: Promise<void> } | null = null
  const available = () => !disposed && active && visible.value && document.visibilityState === 'visible'
  const historyReads = createReportReadSession(available), detailReads = createReportReadSession(available)
  const historyItems = computed<ExecutionHistoryItem[]>(() => options.value.map(item => ({
    id: item.id, title: item.attempt_no <= 1 ? '首次执行' : `第${item.attempt_no - 1}次重试`,
    statusText: item.status_text || '未知', statusColor: resultStatusColor(item.status_text),
    time: item.update_time || item.create_time || '-', actor: item.trigger_user_name,
    latest: item.is_case_latest, sourceText: item.source_scope_name || 'Case执行',
    sourceColor: item.source_scope === 'current_report' ? 'arcoblue' : item.source_scope === 'other_report' ? 'purple' : 'gray',
  })))
  const hasDetail = computed(() => {
    const row = selectedCase.value
    if (!row) return false
    if (target.value?.caseType === 0) return (Array.isArray(row.element_result_list) && row.element_result_list.length > 0)
      || (Array.isArray(row.children) && row.children.length > 0)
    return Boolean(row.attachments || row.statusDetails || row.fullName || row.description || row.name)
  })
  function resultStatusColor(value: string) {
    if (value.includes('成功') || value.includes('通过')) return 'green'
    if (value.includes('失败')) return 'red'
    if (value.includes('警告')) return 'orange'
    if (value.includes('执行中') || value.includes('进行中')) return 'arcoblue'
    return 'gray'
  }
  function invalidate() {
    version += 1
    historyReads.invalidate(); detailReads.invalidate()
    selectedCase.value = null
    historyError.value = ''; detailError.value = ''
  }
  function close() {
    target.value = null
    visible.value = false
    invalidate()
    options.value = []; selectedResultId.value = null
  }
  function open(input: ReportResultTarget): Promise<void> {
    const next = reportResultTarget(input.source, String(input.caseType))
    if (!next || disposed || !active || document.visibilityState !== 'visible') return Promise.resolve()
    if (visible.value && opening?.version === version && JSON.stringify(target.value) === JSON.stringify(next)) return opening.promise
    invalidate()
    target.value = next
    options.value = []; selectedResultId.value = null
    visible.value = true
    const currentVersion = version
    const promise = loadBoth().finally(() => { if (opening?.version === currentVersion) opening = null })
    opening = { version: currentVersion, promise }
    return promise
  }
  async function loadBoth() { await Promise.allSettled([loadHistory(), loadResult()]) }
  function readTarget() {
    const snapshot = target.value, currentVersion = version
    return snapshot ? { ...snapshot, current: () => version === currentVersion } : null
  }
  function loadHistory(): Promise<void> {
    const snapshot = readTarget()
    if (!snapshot) return Promise.resolve()
    return historyReads.run({ key: snapshot.detailId, silent: false, loading: historyLoading, error: historyError,
      message: '执行记录加载失败，请重试', isCurrent: snapshot.current,
      read: async () => parseReportResultOptions(await getSystemTestSuiteDetailsResultOptionsShare(snapshot.detailId)),
      apply: items => {
        options.value = items
        if (selectedResultId.value === null) selectedResultId.value = items.find(item => item.test_suite_detail_id === snapshot.detailId && item.is_latest)?.id ?? null
      },
    })
  }
  function loadResult(): Promise<void> {
    const snapshot = readTarget()
    if (!snapshot) return Promise.resolve()
    const resultId = selectedResultId.value
    selectedCase.value = null
    return detailReads.run({ key: `${snapshot.detailId}:${resultId ?? 'latest'}`, silent: false, loading: detailLoading, error: detailError,
      message: '执行结果加载失败，请重试', isCurrent: snapshot.current,
      read: async () => parseReportResult(await getSystemTestSuiteDetailsResultShare(snapshot.detailId, resultId ?? undefined), snapshot.detailId),
      apply: result => { selectedCase.value = result === null ? null : buildReportResult(snapshot.source, result, String(snapshot.caseType)) },
    })
  }
  function selectResult(id: string | number): Promise<void> {
    const resultId = String(id)
    if (!available() || !options.value.some(item => item.id === resultId)) return Promise.resolve()
    selectedResultId.value = resultId
    return loadResult()
  }
  function pause() { invalidate() }
  function visibilityChanged() {
    if (document.visibilityState === 'visible') { if (visible.value) void loadBoth() }
    else pause()
  }
  watch(() => visible.value, value => { if (!value && target.value) close() }, { flush: 'sync' })
  watch(() => [props.reportId, route.fullPath, userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment], close, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onDeactivated(() => { active = false; pause() })
  onActivated(() => { const resume = !active; active = true; if (resume && visible.value) void loadBoth() })
  onBeforeUnmount(() => { disposed = true; active = false; close(); document.removeEventListener('visibilitychange', visibilityChanged) })
  defineExpose({ open, close })
</script>

<style scoped lang="less">
  .mango-report-result-history {
    display: grid;
    height: 100%;
    min-width: 0;
    min-height: 0;
    grid-template-columns: minmax(200px, 26%) minmax(0, 1fr);
    gap: var(--m-page-gap);
  }
  :global(.mango-report-result-drawer .arco-drawer-body) {
    padding: var(--m-page-gap);
    overflow: hidden;
    background: var(--m-bg);
    container-type: inline-size;
    container-name: mango-report-result;
  }
  .mango-report-result-spin {
    display: block;
    min-width: 0;
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
  }
  .mango-report-result-spin :deep(> .mango-panel-spin__content) {
    box-sizing: border-box;
    min-height: 100%;
    padding: var(--m-card-padding);
  }
  @container mango-report-result (max-width: 760px) {
    .mango-report-result-history {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: minmax(160px, 28%) minmax(0, 1fr);
    }
  }
</style>
