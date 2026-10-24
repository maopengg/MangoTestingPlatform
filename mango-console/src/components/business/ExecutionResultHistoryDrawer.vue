<template>
  <a-drawer
    :visible="visible"
    :width="width || defaultDrawerWidth"
    :footer="false"
    class="execution-result-history-drawer"
    unmount-on-close
    @update:visible="(value) => emit('update:visible', value)"
    @cancel="emit('update:visible', false)"
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
        @select="selectResult"
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
                  :class="{ 'is-scenario': nodeData.nodeType === 'scenario' }"
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
          <slot name="result" :detail="selectedDetail" :error-message="selectedErrorMessage">
            <a-empty
              v-if="!selectedDetail"
              description="请选择执行记录"
              class="execution-result-history__empty"
            />
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
              <a-empty
                v-else
                description="本次执行没有生成测试结果"
                class="execution-result-history__empty"
              />
            </template>
          </slot>
        </mango-panel-spin>
      </section>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { computed, ref, useSlots, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
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
  import type { ExecutionHistoryItem } from '@/components/business/execution-history'

  type ScenarioOption = {
    key: string
    label: string
    parameterId: number | string | null
    status: number
    retryCount: number
    result: any
  }

  type StepOption = {
    key: string
    label: string
    status: number
    total: number
    passed: number
    scenarios: ScenarioOption[]
  }

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
  const slots = useSlots()
  const records = ref<any[]>([])
  const selectedId = ref<number | string>('')
  const selectedDetail = ref<any>(null)
  const selectedStepKey = ref('')
  const selectedScenarioKey = ref('')
  const selectedTreeKey = ref('')
  const expandedStepKeys = ref<string[]>([])
  const loading = ref(false)
  const detailLoading = ref(false)
  let detailRequestToken = 0
  const defaultDrawerWidth = 'min(1300px, calc(100vw - 32px))'
  const drawerTitle = computed(() => {
    const [main, ...context] = String(props.title || '历史执行结果').split(/[：:]/)
    return {
      main: main.trim() || '历史执行结果',
      context: context.join('：').trim(),
    }
  })
  const detailMode = computed(() => !!props.testSuiteDetailId)
  const effectiveQuery = computed<ExecutionResultQuery | null>(() => {
    if (props.caseId) {
      return {
        ...(props.query || {}),
        target_type: 'api_case',
        target_id: props.caseId,
      }
    }
    return props.query || null
  })
  const selectedErrorMessage = computed(
    () =>
      selectedDetail.value?.error_message || selectedDetail.value?.result_data?.error_message || ''
  )
  const stepOptions = computed<StepOption[]>(() => {
    const resultData = selectedDetail.value?.result_data
    return buildStepOptions(Array.isArray(resultData) ? resultData : resultData?.steps)
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
      nodeType: 'step',
      status: step.status,
      description: `${step.passed}/${step.total} 个场景通过`,
      children: step.scenarios.map((scenario) => ({
        key: scenario.key,
        title: scenario.label,
        nodeType: 'scenario',
        status: scenario.status,
        description: scenario.retryCount > 0 ? `重试 ${scenario.retryCount} 次` : '',
      })),
    }))
  )
  const directApiResult = computed(() => {
    const resultData = selectedDetail.value?.result_data
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
      latest: Boolean(item.is_case_latest ?? item.is_latest) || index === 0,
      sourceText: resultSourceText(item),
      sourceColor: resultSourceColor(item),
    }))
  )

  function resultTestSuiteId(item: any) {
    return item?.test_suite_id || item?.test_suite || ''
  }

  function isCurrentTestSuite(item: any) {
    const testSuiteId = resultTestSuiteId(item)
    return !!(
      testSuiteId &&
      props.currentTestSuiteId &&
      String(testSuiteId) === String(props.currentTestSuiteId)
    )
  }

  function resultSourceText(item: any) {
    const testSuiteId = resultTestSuiteId(item)
    if (testSuiteId) {
      if (isCurrentTestSuite(item)) return '本测试报告'
      if (props.currentTestSuiteId) return `其他报告 #${testSuiteId}`
      return `报告 #${testSuiteId}`
    }
    return item?.source_type_name || sourceTypeText(item?.source_type)
  }

  function resultSourceColor(item: any) {
    if (isCurrentTestSuite(item)) return 'arcoblue'
    if (resultTestSuiteId(item)) return 'purple'
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
    if (!selectedId.value || !selectedDetail.value?.trace_id) return
    emit('show-trace', { result_id: selectedId.value })
  }

  async function loadList() {
    loading.value = true
    selectedDetail.value = null
    try {
      await enumStore.getEnum()
      if (!detailMode.value && !effectiveQuery.value) {
        records.value = []
        selectedId.value = ''
        return
      }
      const res = detailMode.value
        ? await getSystemTestSuiteDetailsResultOptionsShare(props.testSuiteDetailId!, 20)
        : await getExecutionResultList({
            ...effectiveQuery.value!,
            page: 1,
            pageSize: 20,
          })
      records.value = res.data || []
      const latest = records.value[0]
      selectedId.value = latest?.id || ''
      if (selectedId.value) await selectResult(selectedId.value)
    } catch (error: any) {
      Message.error(error?.msg || error?.message || '加载历史执行结果失败')
    } finally {
      loading.value = false
    }
  }

  async function selectResult(id: number | string) {
    const requestToken = detailRequestToken + 1
    detailRequestToken = requestToken
    selectedId.value = id
    detailLoading.value = true
    try {
      const res = detailMode.value
        ? await getSystemTestSuiteDetailsResultShare(props.testSuiteDetailId!, id)
        : await getExecutionResultDetailResolved(id)
      if (detailRequestToken !== requestToken) return
      selectedDetail.value = detailMode.value
        ? buildReportDetail(
            res.data,
            records.value.find((item) => String(item.id) === String(id))
          )
        : res.data || null
      if (!slots.result) initializeResultSelection()
    } catch (error: any) {
      if (detailRequestToken === requestToken) {
        Message.error(error?.msg || error?.message || '加载执行结果详情失败')
      }
    } finally {
      if (detailRequestToken === requestToken) detailLoading.value = false
    }
  }

  function buildReportDetail(payload: any, option: any) {
    if (!payload) return null
    const children = Array.isArray(payload.children) ? payload.children : []
    const result =
      children.find(
        (item: any) =>
          props.preferredParameterId !== undefined &&
          props.preferredParameterId !== null &&
          String(item?.parameter_id) === String(props.preferredParameterId)
      ) ||
      children[0] ||
      payload
    return {
      ...option,
      id: option?.id,
      status: result?.status ?? option?.status,
      status_name: option?.status_text || option?.status_name,
      error_message: result?.error_message || payload?.error_message,
      result_data: result,
      test_suite: option?.test_suite_id,
    }
  }

  function displayResultLabel(item: any) {
    const label = item?.label || `记录 ${item?.id || '-'}`
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
    return 'red'
  }

  function statusText(status: number | string | null | undefined) {
    if (Number(status) === 4) return '警告'
    return enumStore.task_status?.[Number(status)]?.title || '未知'
  }

  function aggregateStatus(items: ScenarioOption[]) {
    if (items.some((item) => Number(item.status) === 0)) return 0
    if (items.some((item) => Number(item.status) === 3)) return 3
    if (items.some((item) => Number(item.status) === 4)) return 4
    if (items.length && items.every((item) => Number(item.status) === 1)) return 1
    return 2
  }

  function finalScenarioResult(results: any[]) {
    return results.reduce((latest, item) => {
      const latestRetry = Number(latest?.retry_index ?? -1)
      const itemRetry = Number(item?.retry_index ?? -1)
      return itemRetry >= latestRetry ? item : latest
    }, results[0])
  }

  function buildStepOptions(rawSteps: unknown): StepOption[] {
    if (!Array.isArray(rawSteps) || rawSteps.length === 0) return []
    const stepMap = new Map<
      string,
      {
        key: string
        label: string
        scenarios: Map<string, { key: string; label: string; results: any[] }>
      }
    >()
    rawSteps.forEach((result: any, index) => {
      const stepKey = String(result?.id ?? result?.api_info_id ?? `step-${index}`)
      if (!stepMap.has(stepKey)) {
        stepMap.set(stepKey, {
          key: stepKey,
          label: result?.api_info_name || `步骤 ${result?.id || index + 1}`,
          scenarios: new Map(),
        })
      }
      const step = stepMap.get(stepKey)!
      const scenarioKey = String(result?.parameter_id ?? result?.name ?? `scenario-${index}`)
      if (!step.scenarios.has(scenarioKey)) {
        step.scenarios.set(scenarioKey, {
          key: `${stepKey}:${scenarioKey}`,
          label: result?.name || result?.api_info_name || '默认场景',
          results: [],
        })
      }
      step.scenarios.get(scenarioKey)!.results.push(result)
    })
    return Array.from(stepMap.values()).map((step) => {
      const scenarios = Array.from(step.scenarios.values()).map((scenario) => {
        const result = finalScenarioResult(scenario.results)
        const retryCount = Math.max(scenario.results.length - 1, Number(result?.retry_index || 0))
        return {
          key: scenario.key,
          label: scenario.label,
          parameterId: result?.parameter_id ?? null,
          status: Number(result?.status ?? 2),
          retryCount,
          result,
        }
      })
      return {
        key: step.key,
        label: step.label,
        status: aggregateStatus(scenarios),
        total: scenarios.length,
        passed: scenarios.filter((item) => Number(item.status) === 1).length,
        scenarios,
      }
    })
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
      scenarios.find((item) => Number(item.scenario.status) === 0) ||
      scenarios.find((item) => Number(item.scenario.status) === 4) ||
      scenarios[0] ||
      null
    )
  }

  function initializeResultSelection() {
    const preferred = preferredScenario(stepOptions.value)
    selectedStepKey.value = preferred?.step.key || ''
    selectedScenarioKey.value = preferred?.scenario.key || ''
    selectedTreeKey.value = preferred?.scenario.key || ''
    expandedStepKeys.value = stepOptions.value.map((step) => `step:${step.key}`)
  }

  function selectTreeNode(keys: Array<string | number>) {
    const key = String(keys[0] || '')
    if (!key) return
    selectedTreeKey.value = key
    if (key.startsWith('step:')) {
      const stepKey = key.replace(/^step:/, '')
      const step = stepOptions.value.find((item) => item.key === stepKey)
      if (!step) return
      const scenario =
        step.scenarios.find((item) => Number(item.status) === 0) ||
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
    selectedStepKey.value = step.key
    selectedScenarioKey.value = key
  }

  watch(
    () => props.visible,
    (visible) => {
      if (visible) void loadList()
    }
  )
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
