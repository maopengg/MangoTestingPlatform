<template>
  <a-drawer
    :visible="visible"
    :width="width || defaultDrawerWidth"
    :footer="false"
    class="execution-result-history-drawer"
    unmount-on-close
    @update:visible="updateVisible"
    @cancel="updateVisible(false)"
  >
    <template #title>
      <div class="execution-result-history__drawer-title">
        <span class="execution-result-history__drawer-icon">
          <IconHistory />
        </span>
        <div class="execution-result-history__drawer-heading">
          <div>
            <strong>{{ drawerTitle.main }}</strong>
            <a-tag v-if="drawerTitle.context" color="arcoblue" size="small">
              {{ drawerTitle.context }}
            </a-tag>
          </div>
          <small>{{ description || '查看执行记录、步骤场景及完整响应详情' }}</small>
        </div>
      </div>
    </template>
    <div
      class="execution-result-history"
      :class="{ 'execution-result-history--with-navigator': showResultNavigator }"
    >
      <ExecutionHistoryList
        class="execution-result-history__list"
        :items="historyItems"
        :selected-id="selectedId"
        :loading="loading"
        :error-text="listFailed ? '加载执行记录失败' : ''"
        @select="selectResult"
        @retry="loadList"
      />
      <div v-if="showResultNavigator" class="execution-result-history__navigation">
        <section class="execution-result-history__selector">
          <div class="execution-result-history__head">
            <div>
              <strong>步骤与场景</strong>
              <span>{{ stepOptions.length }} 个步骤 · {{ scenarioTotal }} 个场景</span>
            </div>
            <a-button
              size="small"
              class="execution-result-history__trace-button"
              :disabled="!selectedDetail?.trace_id"
              :title="
                selectedDetail?.trace_id ? '查看当前执行记录的执行链路' : '该次执行未记录执行链路'
              "
              @click.stop="openExecutionTrace"
            >
              执行链路
            </a-button>
          </div>
          <div class="execution-result-history__tree mango-native-scrollbar">
            <a-tree
              v-model:expanded-keys="expandedStepKeys"
              :data="resultTreeData"
              :selected-keys="selectedTreeKey ? [selectedTreeKey] : []"
              block-node
              size="small"
              @select="selectTreeNode"
            >
              <template #title="nodeData">
                <span
                  class="execution-result-history__tree-node"
                  :class="{ 'is-scenario': nodeData['data-result-kind'] === 'scenario' }"
                >
                  <span class="execution-result-history__tree-node-main">
                    <strong :title="nodeData.title">{{ nodeData.title }}</strong>
                    <small v-if="nodeData.description">{{ nodeData.description }}</small>
                  </span>
                  <a-tag :color="statusColor(nodeData.status)" size="small">
                    {{ statusText(nodeData.status) }}
                  </a-tag>
                </span>
              </template>
            </a-tree>
          </div>
        </section>
      </div>
      <section class="execution-result-history__detail">
        <mango-panel-spin :loading="detailLoading" class="execution-result-history__spin">
          <template v-if="detailFailed"></template>
          <template v-else>
          <slot name="result" :detail="selectedDetail" :error-message="selectedErrorMessage">
            <div v-if="!selectedDetail" class="execution-result-history__empty mango-empty-state">请选择执行记录</div>
            <template v-else>
              <a-alert
                v-if="selectedErrorMessage && !selectedApiResult"
                type="error"
                class="execution-result-history__alert"
              >
                {{ selectedErrorMessage }}
              </a-alert>
              <div v-if="selectedApiResult" class="execution-result-history__report">
                <ApiTestReport :result-data="selectedApiResult" contained />
              </div>
              <div v-else class="execution-result-history__empty mango-empty-state">本次执行没有生成测试结果</div>
            </template>
          </slot>
          </template>
        </mango-panel-spin>
      </section>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, useSlots, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { IconHistory } from '@arco-design/web-vue/es/icon'
  import {
    getExecutionResultDetailResolved,
    getExecutionResultList,
    type ExecutionResultQuery,
  } from '@/api/system/execution_result'
  import {
    getSystemTestSuiteDetailsResultOptionsShare,
    getSystemTestSuiteDetailsResultShare,
  } from '@/api/system/test_sute_details'
  import { useEnum } from '@/store/modules/get-enum'
  import ApiTestReport from '@/components/reports/ApiTestReport.vue'
  import ExecutionHistoryList from '@/components/business/ExecutionHistoryList.vue'
  import { historyDetail, historyId, historyObject, historyRecords, historySteps, historyText, reportHistoryDetail } from './execution-history'
  import type { ExecutionHistoryItem, HistoryDetail, HistoryRecord, HistoryStep as StepOption } from './execution-history'

  const props = defineProps<{
    visible: boolean
    title: string
    query?: ExecutionResultQuery
    caseId?: number | string
    testSuiteDetailId?: number | string
    currentTestSuiteId?: number | string
    preferredParameterId?: number | string
    description?: string
    width?: string | number
  }>()

  const emit = defineEmits<{
    (event: 'update:visible', value: boolean): void
    (event: 'show-trace', query: { result_id: number | string }): void
  }>()

  const enumStore = useEnum()
  const userStore = useUserStore(), route = useRoute()
  const slots = useSlots()
  const records = shallowRef<HistoryRecord[]>([])
  const selectedId = ref<number | string | null>(null)
  const selectedDetail = shallowRef<HistoryDetail | null>(null)
  const selectedStepKey = ref('')
  const selectedScenarioKey = ref('')
  const selectedTreeKey = ref('')
  const expandedStepKeys = ref<string[]>([])
  const loading = ref(false)
  const detailLoading = ref(false)
  const listFailed = ref(false), detailFailed = ref(false)
  let contextVersion = 0, listRequestToken = 0
  let detailRequestToken = 0
  let listJob: Promise<void> | null = null
  let detailJob: { id: string; promise: Promise<void> } | null = null
  let active = true, disposed = false, dismissed = false
  const available = () => props.visible && !dismissed && active && !disposed && !document.hidden
  const defaultDrawerWidth = 'min(1300px, calc(100vw - 32px))'
  const drawerTitle = computed(() => {
    const [main, ...context] = String(props.title || '历史执行结果').split(/[：:]/)
    return {
      main: main.trim() || '历史执行结果',
      context: context.join('：').trim(),
    }
  })
  const detailMode = computed(() => historyId(props.testSuiteDetailId) !== null)
  const effectiveQuery = computed<ExecutionResultQuery | null>(() => {
    if (historyId(props.caseId) !== null) {
      return {
        ...(props.query || {}),
        target_type: 'api_case',
        target_id: props.caseId,
      }
    }
    return props.query || null
  })
  const selectedErrorMessage = computed(() => selectedDetail.value?.error_message || historyText(historyObject(selectedDetail.value?.result_data)?.error_message))
  const stepOptions = computed<StepOption[]>(() => {
    const resultData = selectedDetail.value?.result_data
    return slots.result ? [] : historySteps(Array.isArray(resultData) ? resultData : historyObject(resultData)?.steps)
  })
  const selectedStep = computed(
    () => stepOptions.value.find((item) => item.key === selectedStepKey.value) || null
  )
  const selectedScenario = computed(
    () =>
      selectedStep.value?.scenarios.find((item) => item.key === selectedScenarioKey.value) || null
  )
  const scenarioTotal = computed(() =>
    stepOptions.value.reduce((total, step) => total + step.scenarios.length, 0)
  )
  const resultTreeData = computed(() =>
    stepOptions.value.map((step) => ({
      key: `step:${step.key}`,
      title: step.label,
      'data-result-kind': 'step',
      status: step.status,
      description: `${step.passed}/${step.total} 个场景通过`,
      children: step.scenarios.map((scenario) => ({
        key: scenario.key,
        title: scenario.label,
        'data-result-kind': 'scenario',
        status: scenario.status,
        description: scenario.retryCount > 0 ? `重试 ${scenario.retryCount} 次` : '',
      })),
    }))
  )
  const directApiResult = computed(() => {
    const resultData = historyObject(selectedDetail.value?.result_data)
    if (!resultData || stepOptions.value.length) return null
    if (
      selectedDetail.value?.target_type === 'api_info' ||
      resultData.request ||
      resultData.response ||
      resultData.ass
    ) {
      return resultData
    }
    return null
  })
  const selectedApiResult = computed(() => selectedScenario.value?.result || directApiResult.value)
  const showResultNavigator = computed(
    () => !detailMode.value && !slots.result && stepOptions.value.length > 0
  )
  const historyItems = computed<ExecutionHistoryItem[]>(() =>
    records.value.map((item, index) => ({
      id: item.id,
      title: displayResultLabel(item),
      statusText: item.status_name || item.status_text || '未知',
      statusColor: statusColor(item.status, item.status_text),
      time: item.update_time || item.create_time || item.trigger_time || '-',
      actor: item.trigger_user_name || '-',
      latest: item.is_case_latest ?? item.is_latest ?? index === 0,
      sourceText: resultSourceText(item),
      sourceColor: resultSourceColor(item),
    }))
  )

  function resultTestSuiteId(item: HistoryRecord) {
    return item.test_suite_id ?? item.test_suite
  }

  function isCurrentTestSuite(item: HistoryRecord) {
    const testSuiteId = resultTestSuiteId(item)
    return !!(
      testSuiteId !== null &&
      historyId(props.currentTestSuiteId) !== null &&
      String(testSuiteId) === String(props.currentTestSuiteId)
    )
  }

  function resultSourceText(item: HistoryRecord) {
    const testSuiteId = resultTestSuiteId(item)
    if (testSuiteId !== null) {
      if (isCurrentTestSuite(item)) return '本测试报告'
      if (historyId(props.currentTestSuiteId) !== null) return `其他报告 #${testSuiteId}`
      return `报告 #${testSuiteId}`
    }
    return item?.source_type_name || sourceTypeText(item?.source_type)
  }

  function resultSourceColor(item: HistoryRecord) {
    if (isCurrentTestSuite(item)) return 'arcoblue'
    if (resultTestSuiteId(item) !== null) return 'purple'
    if (item?.source_type === 'mcp') return 'orange'
    return 'gray'
  }

  function sourceTypeText(sourceType: unknown) {
    const sourceMap: Record<string, string> = {
      page: '页面执行',
      mcp: 'MCP执行',
      report: '测试报告',
      retry: '重试执行',
    }
    return sourceMap[String(sourceType || '')] || String(sourceType || '-')
  }

  function openExecutionTrace() {
    if (!available() || selectedId.value === null || !selectedDetail.value?.trace_id) return
    emit('show-trace', { result_id: selectedId.value })
  }

  function resetSelection() {
    selectedDetail.value = null
    selectedStepKey.value = ''
    selectedScenarioKey.value = ''
    selectedTreeKey.value = ''
    expandedStepKeys.value = []
  }

  function invalidate(clear = true) {
    contextVersion++
    listRequestToken++
    detailRequestToken++
    listJob = null
    detailJob = null
    loading.value = false
    detailLoading.value = false
    listFailed.value = false
    detailFailed.value = false
    if (clear) {
      records.value = []
      selectedId.value = null
      resetSelection()
    }
  }

  function loadList(): Promise<void> {
    if (!available()) return Promise.resolve()
    if (listJob) return listJob
    const scope = contextVersion, token = ++listRequestToken
    const detailId = historyId(props.testSuiteDetailId)
    const query = effectiveQuery.value ? { ...effectiveQuery.value } : null
    const previousId = selectedId.value
    const previousScenarioKey = selectedScenarioKey.value
    detailRequestToken++
    detailJob = null
    detailLoading.value = false
    detailFailed.value = false
    resetSelection()
    records.value = []
    selectedId.value = null
    listFailed.value = false
    if (detailId === null && !query) return Promise.resolve()
    loading.value = true
    const current = () => available() && scope === contextVersion && token === listRequestToken
    const job = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        // 枚举只补充展示；报告分享复用公开枚举接口，不能触发登录接口。
        void Promise.resolve().then(() => {
          if (current()) return detailId !== null ? enumStore.getEnumShare() : enumStore.getEnum()
        }).catch(() => {})
        const res = detailId !== null
          ? await getSystemTestSuiteDetailsResultOptionsShare(detailId, 20)
          : await getExecutionResultList({ ...query!, page: 1, pageSize: 20 })
        if (!current()) return
        records.value = historyRecords(res, detailId !== null ? undefined : query!)
        const next = records.value.find(item => previousId !== null && String(item.id) === String(previousId)) || records.value[0]
        // 左侧记录完成后立即解除其 loading，详情有独立的请求状态。
        if (next) void selectResult(next.id, String(next.id) === String(previousId) ? previousScenarioKey : '')
      } catch (loadFailure0) {
        if (current()) {
          void (reportLoadError(loadFailure0, "加载失败，请重试", false), listFailed.value = true)
        }
      } finally {
        if (current()) loading.value = false
        if (listJob === job) listJob = null
      }
    })
    listJob = job
    return job
  }

  function selectResult(id: number | string, restoreScenarioKey = ''): Promise<void> {
    if (!available()) return Promise.resolve()
    const option = records.value.find(item => String(item.id) === String(id))
    if (!option) return Promise.resolve()
    if (detailJob?.id === String(id)) return detailJob.promise
    const scope = contextVersion, token = ++detailRequestToken
    const detailId = historyId(props.testSuiteDetailId), parameterId = props.preferredParameterId
    selectedId.value = option.id
    resetSelection()
    detailFailed.value = false
    detailLoading.value = true
    const current = () => available() && scope === contextVersion && token === detailRequestToken
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const res = detailId !== null
          ? await getSystemTestSuiteDetailsResultShare(detailId, option.id)
          : await getExecutionResultDetailResolved(option.id)
        if (!current()) return
        const detail = detailId !== null ? reportHistoryDetail(res, option, parameterId) : historyDetail(res, option.id)
        if (detailId === null && (detail.target_type !== option.target_type || String(detail.target_id) !== String(option.target_id))) throw new Error('Invalid history target')
        selectedDetail.value = detail
        if (!slots.result) initializeResultSelection(restoreScenarioKey)
      } catch (loadFailure1) {
        if (current()) {
          void (reportLoadError(loadFailure1, "加载失败，请重试", false), detailFailed.value = true)
        }
      } finally {
        if (current()) detailLoading.value = false
        if (detailJob?.promise === promise) detailJob = null
      }
    })
    detailJob = { id: String(id), promise }
    return promise
  }

  function retryDetail() {
    return selectedId.value !== null ? selectResult(selectedId.value) : Promise.resolve()
  }

  function displayResultLabel(item: HistoryRecord) {
    const label = item.label || `记录 ${item.id}`
    return String(label).replace(/^最新[，,]?\s*/, '')
  }

  function statusColor(status: number | string | null | undefined, statusTextValue?: unknown) {
    const statusText = String(statusTextValue || '')
    if (statusText.includes('通过') || statusText.includes('成功')) return 'green'
    if (statusText.includes('警告')) return 'orange'
    if (statusText.includes('进行中') || statusText.includes('执行中')) return 'arcoblue'
    if (statusText.includes('失败')) return 'red'
    if (Number(status) === 1) return 'green'
    if (Number(status) === 4) return 'orange'
    if (Number(status) === 3) return 'arcoblue'
    if (Number(status) === 2) return 'gray'
    return status === 0 ? 'red' : 'gray'
  }

  function statusText(status: number | string | null | undefined) {
    if (status === null || status === undefined || status === '') return '未知'
    if (Number(status) === 4) return '警告'
    return enumStore.task_status?.[Number(status)]?.title || '未知'
  }

  function preferredScenario(steps: StepOption[]) {
    const scenarios = steps.flatMap((step) =>
      step.scenarios.map((scenario) => ({ step, scenario }))
    )
    return (
      scenarios.find(
        (item) =>
          props.preferredParameterId !== undefined &&
          props.preferredParameterId !== null &&
          String(item.scenario.parameterId) === String(props.preferredParameterId)
      ) ||
      scenarios.find((item) => item.scenario.status === 0) ||
      scenarios.find((item) => Number(item.scenario.status) === 4) ||
      scenarios[0] ||
      null
    )
  }

  function initializeResultSelection(restoreScenarioKey = '') {
    const restoredStep = stepOptions.value.find(step => step.scenarios.some(scenario => scenario.key === restoreScenarioKey))
    const restoredScenario = restoredStep?.scenarios.find(scenario => scenario.key === restoreScenarioKey)
    const preferred = restoredStep && restoredScenario ? { step: restoredStep, scenario: restoredScenario } : preferredScenario(stepOptions.value)
    selectedStepKey.value = preferred?.step.key || ''
    selectedScenarioKey.value = preferred?.scenario.key || ''
    selectedTreeKey.value = preferred?.scenario.key || ''
    expandedStepKeys.value = stepOptions.value.map((step) => `step:${step.key}`)
  }

  function selectTreeNode(keys: Array<string | number>) {
    if (!available() || detailLoading.value || detailFailed.value) return
    const key = String(keys[0] || '')
    if (!key) return
    if (key.startsWith('step:')) {
      const stepKey = key.replace(/^step:/, '')
      const step = stepOptions.value.find((item) => item.key === stepKey)
      if (!step) return
      selectedTreeKey.value = key
      const scenario =
        step.scenarios.find((item) => item.status === 0) ||
        step.scenarios.find((item) => Number(item.status) === 4) ||
        step.scenarios[0]
      selectedStepKey.value = step.key
      selectedScenarioKey.value = scenario?.key || ''
      return
    }
    const step = stepOptions.value.find((item) =>
      item.scenarios.some((scenario) => scenario.key === key)
    )
    if (!step) return
    selectedTreeKey.value = key
    selectedStepKey.value = step.key
    selectedScenarioKey.value = key
  }

  function updateVisible(value: boolean) {
    if (!value) {
      dismissed = true
      invalidate()
    }
    emit('update:visible', value)
  }

  watch(() => [props.visible, props.caseId, props.testSuiteDetailId, props.preferredParameterId, JSON.stringify(effectiveQuery.value)], () => {
    dismissed = false
    invalidate()
    if (available()) void loadList()
  }, { immediate: true, flush: 'sync' })

  watch(() => [userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment, route.fullPath], () => {
    invalidate()
    dismissed = true
    if (props.visible) emit('update:visible', false)
  }, { flush: 'sync' })

  function onVisibilityChange() {
    if (document.hidden) invalidate(false)
    else if (available()) void loadList()
  }
  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibilityChange)
  })
  onDeactivated(() => { active = false; invalidate(false) })
  onActivated(() => { active = true; if (available()) void loadList() })
  onBeforeUnmount(() => {
    disposed = true
    invalidate()
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })
</script>

<style scoped>
  :deep(.execution-result-history-drawer .arco-drawer-header) {
    height: auto;
    min-height: 64px;
    padding: var(--m-card-padding) var(--m-page-gap);
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  :deep(.execution-result-history-drawer .arco-drawer-body) {
    box-sizing: border-box;
    height: 100%;
    min-height: 0;
    padding: var(--m-page-gap);
    overflow: hidden;
    background: var(--m-bg);
  }

  .execution-result-history__drawer-title {
    display: flex;
    width: 100%;
    min-width: 0;
    align-items: center;
    gap: 10px;
  }

  .execution-result-history__drawer-icon {
    display: inline-flex;
    width: 34px;
    height: 34px;
    flex: 0 0 34px;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--m-primary-border);
    border-radius: var(--m-radius-md);
    background: var(--m-primary-soft);
    color: var(--m-primary);
    font-size: 18px;
  }

  .execution-result-history__drawer-heading {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }

  .execution-result-history__drawer-heading > div {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
  }

  .execution-result-history__drawer-heading strong {
    overflow: hidden;
    color: var(--m-text);
    font-size: 16px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .execution-result-history__drawer-heading small {
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 400;
    line-height: 18px;
  }

  .execution-result-history__trace-button {
    flex: 0 0 auto;
    margin-left: auto;
  }

  .execution-result-history {
    display: grid;
    height: 100%;
    min-height: 0;
    grid-template-columns: 270px minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
    gap: var(--m-page-gap);
  }

  .execution-result-history--with-navigator {
    grid-template-columns: 260px 340px minmax(0, 1fr);
  }

  .execution-result-history__list {
    grid-row: 1;
  }

  .execution-result-history__navigation {
    display: flex;
    min-width: 0;
    min-height: 0;
    grid-column: 2;
    grid-row: 1;
  }

  .execution-result-history__list,
  .execution-result-history__selector,
  .execution-result-history__detail {
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
    overflow: hidden;
  }

  .execution-result-history__head {
    display: flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .execution-result-history__head > div {
    display: flex;
    min-width: 0;
    align-items: baseline;
    gap: 8px;
  }

  .execution-result-history__head strong {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
  }

  .execution-result-history__head span {
    color: var(--m-muted);
    font-size: 12px;
  }

  .execution-result-history__spin {
    display: flex;
    width: 100%;
    height: 100%;
    min-height: 0;
    flex: 1;
    overflow: hidden;
  }

  :deep(.execution-result-history__spin.arco-spin),
  :deep(.execution-result-history__spin > .arco-spin) {
    display: flex;
    width: 100%;
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  :deep(.execution-result-history__spin > .mango-panel-spin__content) {
    width: 100%;
    height: 100%;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: auto;
    scrollbar-gutter: stable;
  }

  .execution-result-history__empty {
    margin-top: 120px;
  }

  .execution-result-history__detail {
    grid-column: 2;
    grid-row: 1;
    min-width: 0;
    min-height: 0;
    padding: var(--m-card-padding);
  }

  .execution-result-history--with-navigator .execution-result-history__detail {
    grid-column: 3;
  }

  .execution-result-history__spin :deep(> .mango-panel-spin__content) {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;
  }

  .execution-result-history__alert {
    margin-bottom: 10px;
    flex: 0 0 auto;
  }

  .execution-result-history__tree {
    min-height: 0;
    flex: 1;
    padding: 6px;
    background: var(--m-surface);
    overflow: auto;
  }

  .execution-result-history__tree :deep(.arco-tree) {
    min-width: 0;
  }

  .execution-result-history__tree :deep(.arco-tree-node-title) {
    min-width: 0;
    flex: 1;
  }

  .execution-result-history__tree-node {
    display: flex;
    width: 100%;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    min-height: 30px;
    padding: 2px 4px;
    color: var(--m-text);
  }

  .execution-result-history__tree-node-main {
    display: flex;
    min-width: 0;
    flex: 1;
    align-items: baseline;
    gap: 6px;
  }

  .execution-result-history__tree-node-main strong {
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .execution-result-history__tree-node-main small {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .execution-result-history__report {
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }

  @media (max-width: 900px) {
    :deep(.execution-result-history-drawer .arco-drawer) {
      width: 92vw !important;
    }

    .execution-result-history {
      grid-template-columns: 1fr;
      grid-template-rows: minmax(180px, 28%) minmax(0, 1fr);
    }

    .execution-result-history--with-navigator {
      grid-template-columns: 1fr;
      grid-template-rows:
        minmax(180px, 24%)
        minmax(320px, 44%)
        minmax(0, 1fr);
    }

    .execution-result-history__list,
    .execution-result-history__navigation,
    .execution-result-history__detail,
    .execution-result-history--with-navigator .execution-result-history__detail {
      grid-column: 1;
      grid-row: auto;
    }
  }
</style>
