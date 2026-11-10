<template>
  <a-drawer
    v-model:visible="localVisible"
    :width="'min(1280px, 80vw)'"
    :footer="false"
    :title="drawerTitle"
    class="mango-test-report-result-drawer"
    unmount-on-close
  >
    <div class="mango-workbench-scroll-x mango-test-report-result-drawer__workspace">
    <div class="mango-detail-workbench mango-test-report-result-drawer__layout">
      <ExecutionHistoryList
        :items="historyItems"
        :selected-id="selectedResultId"
        :loading="historyLoading"
        :error-text="historyError"
        empty-text="当前失败记录暂无可切换的执行结果"
        @select="changeResult"
        @retry="loadHistory"
      />
      <mango-panel-spin
        :loading="detailLoading"
        class="mango-test-report-result-drawer__spin"
        :class="{ 'mango-test-report-result-drawer__spin--api': normalizedCaseType === 1 }"
      >
        <template v-if="loadError"><a-button size="small" type="primary" @click="loadDetail">重新加载</a-button></template>
        <div v-else-if="!hasDetail && !detailLoading" class="mango-test-report-result-drawer__feedback">
          <icon-file />
          <div>
            <strong>本次失败没有生成详细结果</strong>
            <span>{{ resultData?.error_message || fallbackError || '后端未返回失败原因' }}</span>
          </div>
        </div>
        <ElementTestReport v-else-if="hasDetail && normalizedCaseType === 0" :result-data="resultData" />
        <ApiTestReport
          v-else-if="hasDetail && normalizedCaseType === 1"
          :result-data="resultData"
          contained
        />
        <PytestTestReport v-else-if="hasDetail && normalizedCaseType === 2" :result-data="resultData" />
      </mango-panel-spin>
    </div>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { useUserStoreContext } from '@/store/modules/user'
  import { IconExclamationCircleFill, IconFile } from '@arco-design/web-vue/es/icon'
  import { getSystemTestSuiteDetailsResultOptionsShare, getSystemTestSuiteDetailsResultShare } from '@/api/system/test_sute_details'
  import ExecutionHistoryList from '@/components/business/ExecutionHistoryList.vue'
  import { historyId, type ExecutionHistoryItem } from '../business/execution-history'
  import { failureResultTarget, failureResultOptions, failureResultRecord, type FailureResultOption } from './test-report-result'
  import ElementTestReport from './ElementTestReport.vue'
  import ApiTestReport from './ApiTestReport.vue'
  import PytestTestReport from './PytestTestReport.vue'

  const props = withDefaults(defineProps<{
    visible?: boolean
    testSuiteDetailId?: number | string
    caseType?: number | string
    caseName?: string
    caseId?: number | string
    fallbackError?: string
  }>(), { visible: false, testSuiteDetailId: '', caseType: -1, caseName: '', caseId: '', fallbackError: '' })
  const emit = defineEmits<{ (event: 'update:visible', value: boolean): void }>()
  const route = useRoute(), user = useUserStoreContext(), pagePath = route.path
  const localVisible = computed({ get: () => props.visible, set: value => { if (!value) { dismissed = true; invalidate() }; emit('update:visible', value) } })
  const target = computed(() => failureResultTarget(props))
  const normalizedCaseType = computed(() => target.value?.caseType ?? -1)
  const drawerTitle = computed(() => `失败详情：${target.value?.caseName || (target.value?.caseId !== null && target.value?.caseId !== undefined ? `Case ID ${target.value.caseId}` : '测试用例')}`)
  const detailLoading = ref(false), historyLoading = ref(false)
  const loadError = ref(''), historyError = ref('')
  const resultData = ref<Record<string, unknown> | null>(null)
  const resultOptions = ref<FailureResultOption[]>([])
  const selectedResultId = ref<number | string | null>(null)
  let version = 0, detailSequence = 0, mounted = false, active = true, disposed = false, dismissed = false
  let historyPending: { version: number; promise: Promise<void> } | null = null
  let detailPending: { version: number; sequence: number; key: string; promise: Promise<void> } | null = null
  const available = () => mounted && active && !disposed && !dismissed && props.visible && route.path === pagePath && document.visibilityState === 'visible'
  const historyItems = computed<ExecutionHistoryItem[]>(() => resultOptions.value.map(item => ({
    id: item.id, title: item.label || item.status_text || '执行结果', statusText: item.status_text || '未知',
    statusColor: statusColor(item.status_text), time: item.update_time || item.create_time || '-',
    actor: item.trigger_user_name, latest: item.is_case_latest, sourceText: item.source_scope_name || '测试报告',
  })))
  const hasDetail = computed(() => {
    const record = resultData.value
    if (!record) return false
    if (normalizedCaseType.value === 0) return Boolean((Array.isArray(record.element_result_list) && record.element_result_list.length) || (Array.isArray(record.children) && record.children.length))
    if (normalizedCaseType.value === 1) return Boolean(record.request || record.response || record.ass || record.error_message || record.name)
    return normalizedCaseType.value === 2 && Boolean(record.attachments || record.statusDetails || record.fullName || record.description || record.error_message || record.name)
  })
  function statusColor(value: string) {
    if (value.includes('通过') || value.includes('成功')) return 'green'
    if (value.includes('失败') || value.includes('错误')) return 'red'
    if (value.includes('警告')) return 'orange'
    if (value.includes('执行中') || value.includes('进行中')) return 'arcoblue'
    return 'gray'
  }
  function invalidate() {
    version++; detailSequence++
    resultData.value = null; detailLoading.value = false; historyLoading.value = false
    loadError.value = ''; historyError.value = ''
  }
  function closeContext() {
    dismissed = true; invalidate(); resultOptions.value = []; selectedResultId.value = null
    if (props.visible) emit('update:visible', false)
  }
  function validateTarget() {
    if (!target.value) { loadError.value = '缺少有效报告明细或用例类型，无法加载结果'; return null }
    return { ...target.value }
  }
  function loadHistory(): Promise<void> {
    if (!available()) return Promise.resolve()
    const snapshot = validateTarget(), currentVersion = version
    if (!snapshot) return Promise.resolve()
    if (historyPending?.version === version) return historyPending.promise
    historyLoading.value = true; historyError.value = ''
    const current = () => available() && currentVersion === version
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const response = await getSystemTestSuiteDetailsResultOptionsShare(snapshot.detailId)
        if (!current()) return
        resultOptions.value = failureResultOptions(response)
        // Default detail endpoint resolves this report's latest result, not the case-wide first history entry.
        if (selectedResultId.value === null) selectedResultId.value = resultOptions.value.find(item => item.is_latest && String(item.detailId) === String(snapshot.detailId))?.id ?? null
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "执行历史加载失败，请重试", false), historyError.value = '执行历史加载失败，请重试') }
      finally {
        if (currentVersion === version) historyLoading.value = false
        if (historyPending?.version === currentVersion) historyPending = null
      }
    })
    historyPending = { version: currentVersion, promise }; return promise
  }
  function loadDetail(): Promise<void> {
    if (!available()) return Promise.resolve()
    const snapshot = validateTarget(), currentVersion = version, resultId = selectedResultId.value
    if (!snapshot) return Promise.resolve()
    const key = JSON.stringify([snapshot, resultId])
    if (detailPending?.version === version && detailPending.sequence === detailSequence && detailPending.key === key) return detailPending.promise
    const sequence = ++detailSequence
    detailLoading.value = true; loadError.value = ''; resultData.value = null
    const current = () => available() && currentVersion === version && sequence === detailSequence
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const response = await getSystemTestSuiteDetailsResultShare(snapshot.detailId, resultId)
        if (current()) resultData.value = failureResultRecord(response, snapshot)
      } catch (loadFailure1) { if (current()) (reportLoadError(loadFailure1, "详细报告加载失败，请重试", false), loadError.value = '详细报告加载失败，请重试') }
      finally {
        if (currentVersion === version && sequence === detailSequence) detailLoading.value = false
        if (detailPending?.version === currentVersion && detailPending.sequence === sequence) detailPending = null
      }
    })
    detailPending = { version: currentVersion, sequence, key, promise }; return promise
  }
  function changeResult(value: number | string): Promise<void> {
    const id = historyId(value)
    if (!available() || id === null || !resultOptions.value.some(item => String(item.id) === String(id))) return Promise.resolve()
    selectedResultId.value = id
    return loadDetail()
  }
  function resume() { if (available()) { void loadHistory(); void loadDetail() } }
  function visibilityChanged() { if (available()) resume(); else invalidate() }
  watch(() => [props.visible, props.testSuiteDetailId, props.caseType, props.caseId, props.caseName, props.fallbackError], () => {
    dismissed = false; invalidate(); resultOptions.value = []; selectedResultId.value = null; resume()
  }, { flush: 'sync' })
  watch(() => [route.fullPath, user.userId, user.roleId, user.token, user.selected_environment], closeContext, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
  onDeactivated(() => { active = false; invalidate() })
  onActivated(() => { const wasInactive = !active; active = true; if (wasInactive) resume() })
  onBeforeUnmount(() => { disposed = true; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
  .mango-test-report-result-drawer__workspace {
    --mango-workbench-min-width: 920px;
  }

  .mango-test-report-result-drawer__layout {
    box-sizing: border-box;
    display: grid;
    height: 100%;
    min-height: 0;
    padding: var(--m-page-gap);
    margin-top: 0;
    grid-template-columns: 260px minmax(0, 1fr);
    gap: var(--m-page-gap);
    background: var(--m-bg);
  }

  .mango-test-report-result-drawer__spin {
    display: block;
    min-width: 0;
    min-height: 0;
    overflow: auto;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-test-report-result-drawer__spin :deep(> .mango-panel-spin__content) {
    display: block;
    min-height: 100%;
  }

  .mango-test-report-result-drawer__spin--api {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-test-report-result-drawer__spin--api :deep(> .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-test-report-result-drawer__feedback {
    box-sizing: border-box;
    display: flex;
    min-height: 180px;
    margin: 12px;
    padding: 24px;
    align-items: center;
    justify-content: center;
    gap: 12px;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-lg);
    color: var(--m-muted);
    text-align: left;
  }

  .mango-test-report-result-drawer__feedback > svg {
    flex: none;
    color: var(--m-danger);
    font-size: 24px;
  }

  .mango-test-report-result-drawer__feedback > div {
    display: flex;
    max-width: 560px;
    flex: 1;
    flex-direction: column;
    gap: 4px;
  }

  .mango-test-report-result-drawer__feedback strong {
    color: var(--m-text);
  }

  :global(.mango-test-report-result-drawer .arco-drawer-body) {
    min-height: 0;
    padding: 0;
    overflow: hidden;
  }

</style>
