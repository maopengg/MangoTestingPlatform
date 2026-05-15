<template>
  <div class="report-lab" :class="{ 'standalone-report-container': isShareReportRoute }">
    <section class="report-head">
      <div class="head-main">
        <div class="report-title">
          <p class="eyebrow">TEST REPORT WORKBENCH</p>
          <h1>{{ reportInfo.tasks?.name || `测试报告 #${reportId}` }}</h1>
          <p class="report-subtitle">
            <span>{{ currentTypeLabel }}</span>
            <i></i>
            <span>{{ currentStatusLabel }}</span>
            <i></i>
            <span>通过率 {{ passRate }}%</span>
          </p>
        </div>

        <div class="status-console">
          <a-tag :color="statusColor(reportInfo.status)" size="large">
            {{ statusText(reportInfo.status) }}
          </a-tag>
          <strong>{{ passRate }}%</strong>
          <span>SUCCESS RATE</span>
        </div>
      </div>

      <dl class="meta-strip" :class="{ 'has-task-name': hasTaskName }">
        <div v-if="hasTaskName" class="meta-item wide">
          <dt>任务名称</dt>
          <dd>{{ reportInfo.tasks?.name || '-' }}</dd>
        </div>
        <div class="meta-item">
          <dt>报告ID</dt>
          <dd>{{ reportInfo.id || reportId }}</dd>
        </div>
        <div class="meta-item">
          <dt>测试环境</dt>
          <dd>{{ envText(reportInfo.test_env) }}</dd>
        </div>
        <div class="meta-item">
          <dt>执行人</dt>
          <dd>{{ reportInfo.user?.name || '-' }}</dd>
        </div>
        <div class="meta-item">
          <dt>通知状态</dt>
          <dd>
            <a-tag :color="noticeColor(reportInfo.is_notice)" size="small">
              {{ noticeText(reportInfo.is_notice) }}
            </a-tag>
          </dd>
        </div>
        <div class="meta-item">
          <dt>执行时间</dt>
          <dd>{{ reportInfo.create_time || '-' }}</dd>
        </div>
      </dl>
    </section>

    <section class="metric-strip">
      <div v-for="item in metrics" :key="item.key" class="metric-item" :class="item.key">
        <i class="metric-mark"></i>
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </section>

    <section class="overview-grid">
      <div class="overview-panel result-panel">
        <div class="panel-title">
          <div>
            <span>结果分布</span>
            <p>按执行结果聚合当前测试报告</p>
          </div>
          <strong>{{ passRate }}%</strong>
        </div>
        <div class="ratio-bar">
          <i class="success" :style="{ width: `${successRatio}%` }"></i>
          <i class="fail" :style="{ width: `${failRatio}%` }"></i>
          <i class="running" :style="{ width: `${runningRatio}%` }"></i>
        </div>
        <div class="legend-row">
          <span><i class="dot success"></i>成功 {{ summary.success_count || 0 }}</span>
          <span><i class="dot fail"></i>失败 {{ summary.fail_count || 0 }}</span>
          <span><i class="dot running"></i>未完成 {{ unfinishedCount }}</span>
        </div>
      </div>

      <div class="overview-panel type-panel">
        <div class="panel-title">
          <div>
            <span>类型进度</span>
            <p>UI / API / Pytest 执行覆盖</p>
          </div>
          <em v-if="summaryLoading">更新中</em>
        </div>
        <div v-for="item in typeProgress" :key="item.key" class="type-progress">
          <div class="type-row">
            <span>{{ item.label }}</span>
            <em>{{ item.done }}/{{ item.total }}</em>
          </div>
          <a-progress :percent="item.percent" :show-text="false" :stroke-width="8" />
        </div>
      </div>
    </section>

    <section class="case-section">
      <div class="case-main">
          <div class="case-toolbar">
            <div class="case-toolbar-main">
              <div class="case-toolbar-copy">
              <h2>测试套用例列表</h2>
              <p>
                <span>{{ currentTypeLabel }}</span>
                <i></i>
                <span>{{ currentStatusLabel }}</span>
                <i></i>
                <span>已加载 {{ cases.length }} / {{ pagination.total || '未知' }}</span>
              </p>
              </div>
              <div v-if="visibleTypeTabs.length > 0" class="type-switch">
                <button
                  v-for="item in visibleTypeTabs"
                  :key="item.key"
                  type="button"
                  class="type-switch-item"
                  :class="{ active: activeType === item.key }"
                  @click="selectType(item.key)"
                >
                  <span>{{ item.label }}</span>
                  <strong>{{ item.total }}</strong>
                </button>
              </div>
            </div>
            <div class="toolbar-actions">
              <a-radio-group v-model="caseStatus" type="button" size="small" @change="reloadCases">
                <a-radio :value="null">全部</a-radio>
                <a-radio :value="0">失败</a-radio>
                <a-radio :value="1">成功</a-radio>
                <a-radio :value="3">进行中</a-radio>
                <a-radio :value="2">待开始</a-radio>
              </a-radio-group>
            </div>
          </div>

          <a-spin :loading="caseLoading && cases.length === 0" class="case-spin">
            <div v-if="cases.length === 0 && !caseLoading" class="empty-state">暂无用例结果</div>
            <UiCaseTable
              v-else-if="activeType === '0'"
              :cases="cases"
              :enum-store="enumStore"
              :can-retry="canRetry"
              @show-details="showDetails"
              @retry="onRetry"
            />
            <ApiCaseTable
              v-else-if="activeType === '1'"
              :cases="cases"
              :enum-store="enumStore"
              :can-retry="canRetry"
              @show-details="showDetails"
              @retry="onRetry"
            />
            <PytestCaseTable
              v-else-if="activeType === '2'"
              :cases="cases"
              :enum-store="enumStore"
              :can-retry="canRetry"
              @show-details="showDetails"
              @retry="onRetry"
            />
          </a-spin>

          <div ref="loadMoreRef" class="load-more">
            <a-spin v-if="caseLoading && cases.length > 0" size="small" />
            <span v-else-if="pagination.finished && cases.length > 0">没有更多了</span>
          </div>
      </div>
    </section>

    <a-drawer v-model:visible="drawerVisible" :width="1000" title="测试用例详情">
      <a-card v-if="selectedCase.case_type === 0" :title="selectedCase?.name" :bordered="false">
        <ElementTestReport :resultData="selectedCase" />
      </a-card>
      <a-card v-else-if="selectedCase.case_type === 1" :title="selectedCase?.name" :bordered="false">
        <ApiTestReport :resultData="selectedCase" />
      </a-card>
      <a-card v-else-if="selectedCase.case_type === 2" :title="selectedCase?.name" :bordered="false">
        <PytestTestReport :resultData="selectedCase" />
      </a-card>
    </a-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import {
    getSystemTestSuiteDetailsRetry,
    getSystemTestSuiteDetailsShare,
    getSystemTestSuiteDetailsSummaryShare,
  } from '@/api/system/test_sute_details'
  import { getSystemTestSuiteShare } from '@/api/system/test_suite'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePageData } from '@/store/page-data'
  import { useUserStoreContext } from '@/store/modules/user'
  import ElementTestReport from '@/components/ElementTestReport.vue'
  import ApiTestReport from '@/components/ApiTestReport.vue'
  import PytestTestReport from '@/components/PytestTestReport.vue'
  import UiCaseTable from './UiCaseTable.vue'
  import ApiCaseTable from './ApiCaseTable.vue'
  import PytestCaseTable from './PytestCaseTable.vue'

  const route = useRoute()
  const enumStore = useEnum()
  const pageData: any = usePageData()
  const userStore = useUserStoreContext()
  const canRetry = computed(() => !!userStore.token)
  const isShareReportRoute = computed(() => route.path === '/report/details')

  if (!pageData.record) {
    pageData.setRecord({})
  }

  const reportInfo = ref<any>({})
  const summary = ref<any>({})
  const cases = ref<any[]>([])
  const activeType = ref('0')
  const caseStatus = ref<number | null>(null)
  const summaryLoading = ref(false)
  const caseLoading = ref(false)
  const drawerVisible = ref(false)
  const selectedCase = ref<any>({})
  const loadMoreRef = ref<HTMLElement | null>(null)
  const isPolling = ref(false)
  const pollingTimer = ref<ReturnType<typeof setInterval> | null>(null)
  let observer: IntersectionObserver | null = null

  const pagination = reactive({
    page: 1,
    pageSize: 20,
    total: 0,
    finished: false,
  })

  const reportId = computed(() => String(route.query.id || pageData.record?.id || reportInfo.value?.id || ''))
  const unfinishedCount = computed(
    () => (summary.value.stay_begin_count || 0) + (summary.value.proceed_count || 0)
  )
  const totalCount = computed(() => summary.value.count || 0)
  const successRatio = computed(() => ratio(summary.value.success_count, totalCount.value))
  const failRatio = computed(() => ratio(summary.value.fail_count, totalCount.value))
  const runningRatio = computed(() => ratio(unfinishedCount.value, totalCount.value))
  const passRate = computed(() => ratio(summary.value.success_count, totalCount.value))
  const hasTaskName = computed(() => !!reportInfo.value.tasks?.name)

  const metrics = computed(() => [
    { key: 'total', label: '总用例', value: summary.value.count || 0 },
    { key: 'success', label: '成功', value: summary.value.success_count || 0 },
    { key: 'fail', label: '失败', value: summary.value.fail_count || 0 },
    { key: 'running', label: '进行中', value: summary.value.proceed_count || 0 },
    { key: 'wait', label: '待开始', value: summary.value.stay_begin_count || 0 },
  ])

  const typeProgress = computed(() =>
    [
      {
        key: 'ui',
        type: '0',
        label: 'UI 自动化',
        tabLabel: 'UI',
        total: summary.value.ui_count || 0,
        done: summary.value.ui_in_progress_count || 0,
        percent: ratio(summary.value.ui_in_progress_count, summary.value.ui_count) / 100,
      },
      {
        key: 'api',
        type: '1',
        label: 'API 自动化',
        tabLabel: 'API',
        total: summary.value.api_count || 0,
        done: summary.value.api_in_progress_count || 0,
        percent: ratio(summary.value.api_in_progress_count, summary.value.api_count) / 100,
      },
      {
        key: 'pytest',
        type: '2',
        label: 'Pytest',
        tabLabel: 'Pytest',
        total: summary.value.pytest_count || 0,
        done: summary.value.pytest_in_progress_count || 0,
        percent: ratio(summary.value.pytest_in_progress_count, summary.value.pytest_count) / 100,
      },
    ].filter((item) => item.total > 0)
  )
  const visibleTypeTabs = computed(() =>
    typeProgress.value.map((item) => ({
      key: item.type,
      label: item.tabLabel,
      total: item.total,
    }))
  )
  const currentTypeLabel = computed(() => {
    if (activeType.value === '1') return 'API 自动化'
    if (activeType.value === '2') return 'Pytest'
    return 'UI 自动化'
  })
  const currentStatusLabel = computed(() => {
    const map: Record<number, string> = {
      0: '只看失败',
      1: '只看成功',
      2: '只看待开始',
      3: '只看进行中',
    }
    return caseStatus.value === null ? '全部结果' : map[caseStatus.value] || '全部结果'
  })

  function ratio(value = 0, total = 0) {
    if (!total) return 0
    return Math.round((Number(value || 0) / Number(total)) * 100)
  }

  function statusColor(status: number) {
    return enumStore.status_colors?.[status] || 'gray'
  }

  function statusText(status: number) {
    return enumStore.task_status?.[status]?.title || '未知'
  }

  function envText(env: number) {
    return enumStore.environment_type?.[env]?.title || '-'
  }

  function noticeText(status: number) {
    return enumStore.test_suite_notice?.[status]?.title || '-'
  }

  function noticeColor(status: number) {
    return enumStore.colors?.[status] || 'gray'
  }

  function getTotal(res: any) {
    return Number(res?.totalSize || res?.total || res?.count || 0)
  }

  function showDetails(record: any) {
    selectedCase.value = {
      ...record,
      case_type: record?.case_type ?? Number(activeType.value),
    }
    drawerVisible.value = true
  }

  function buildCaseQuery() {
    const data: any = {
      test_suite_id: reportId.value,
      type: activeType.value,
      page: pagination.page,
      pageSize: pagination.pageSize,
    }
    if (caseStatus.value !== null) {
      data.status = caseStatus.value
    }
    return data
  }

  async function loadReportInfo() {
    if (!reportId.value) return
    if (pageData.record?.id?.toString() === reportId.value) {
      reportInfo.value = pageData.record || {}
      return
    }
    const res = await getSystemTestSuiteShare(reportId.value)
    reportInfo.value = res.data || {}
    pageData.setRecord(reportInfo.value)
  }

  async function loadSummary() {
    if (!reportId.value) return
    summaryLoading.value = true
    try {
      const res = await getSystemTestSuiteDetailsSummaryShare(reportId.value)
      summary.value = res.data || {}
      const [firstVisibleType] = visibleTypeTabs.value
      if (firstVisibleType && !visibleTypeTabs.value.some((item) => item.key === activeType.value)) {
        activeType.value = firstVisibleType.key
      }
      handlePolling()
    } finally {
      summaryLoading.value = false
    }
  }

  async function loadCases(reset = false) {
    if (!reportId.value || caseLoading.value) return
    if (!reset && pagination.finished) return
    if (reset) {
      cases.value = []
      pagination.page = 1
      pagination.total = 0
      pagination.finished = false
    }

    caseLoading.value = true
    try {
      const res = await getSystemTestSuiteDetailsShare(buildCaseQuery())
      const list = Array.isArray(res.data) ? res.data : []
      cases.value = reset ? list : cases.value.concat(list)
      pagination.total = getTotal(res)
      pagination.finished =
        list.length < pagination.pageSize ||
        (pagination.total > 0 && cases.value.length >= pagination.total)
      if (!pagination.finished) {
        pagination.page += 1
      }
    } catch (error: any) {
      Message.error(error?.msg || '加载报告失败')
    } finally {
      caseLoading.value = false
    }
  }

  function reloadCases() {
    loadCases(true)
  }

  function selectType(type: string) {
    if (activeType.value === type) return
    activeType.value = type
    reloadCases()
  }

  async function refreshLoadedCases() {
    if (!reportId.value || caseLoading.value) return
    const loadedPageSize = Math.max(cases.value.length, pagination.pageSize)
    const currentPage = pagination.page
    const wasFinished = pagination.finished
    caseLoading.value = true
    try {
      const query = buildCaseQuery()
      query.page = 1
      query.pageSize = loadedPageSize
      const res = await getSystemTestSuiteDetailsShare(query)
      const list = Array.isArray(res.data) ? res.data : []
      cases.value = list
      pagination.total = getTotal(res)
      pagination.finished =
        list.length < loadedPageSize ||
        (pagination.total > 0 && list.length >= pagination.total)
      pagination.page = pagination.finished
        ? currentPage
        : Math.floor(list.length / pagination.pageSize) + 1
    } catch (error) {
      pagination.page = currentPage
      pagination.finished = wasFinished
      throw error
    } finally {
      caseLoading.value = false
    }
  }

  function handlePolling() {
    const hasInProgress = (summary.value.stay_begin_count || 0) > 0 || (summary.value.proceed_count || 0) > 0
    if (hasInProgress && !isPolling.value) {
      startPolling()
    } else if (!hasInProgress && isPolling.value) {
      stopPolling()
    }
  }

  function startPolling() {
    stopPolling()
    isPolling.value = true
    pollingTimer.value = setInterval(async () => {
      await loadSummary()
      await refreshLoadedCases()
    }, 5000)
  }

  function stopPolling() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
    isPolling.value = false
  }

  function initObserver() {
    observer?.disconnect()
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          loadCases()
        }
      },
      { root: null, rootMargin: '260px 0px', threshold: 0 }
    )
    if (loadMoreRef.value) {
      observer.observe(loadMoreRef.value)
    }
  }

  function onRetry(id: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要重试这个测试任务？',
      cancelText: '取消',
      okText: '重试',
      onOk: () => {
        getSystemTestSuiteDetailsRetry(id)
          .then((res) => {
            Message.success(res.msg)
            loadSummary()
            reloadCases()
          })
          .catch(console.log)
      },
    })
  }

  onMounted(async () => {
    if (!enumStore.task_status?.length) {
      enumStore.getEnumShare()
    }
    await loadReportInfo()
    await loadSummary()
    const [firstVisibleType] = visibleTypeTabs.value
    if (firstVisibleType) {
      activeType.value = firstVisibleType.key
    }
    await loadCases(true)
    nextTick(initObserver)
  })

  onUnmounted(() => {
    stopPolling()
    observer?.disconnect()
    observer = null
  })
</script>

<style scoped lang="less">
  .report-lab {
    height: 100%;
    overflow-y: auto;
    padding: 14px;
    background:
      linear-gradient(180deg, rgba(22, 93, 255, 0.1), rgba(245, 247, 251, 0) 320px),
      linear-gradient(90deg, rgba(15, 23, 42, 0.04) 1px, transparent 1px),
      #f5f7fb;
    background-size:
      auto,
      24px 24px,
      auto;
    color: #0f172a;
  }

  .standalone-report-container {
    height: 100vh;
    overflow-x: hidden;
    overflow-y: auto;
  }

  .report-head,
  .overview-panel,
  .case-section {
    background: #fff;
    border: 1px solid #dde5f2;
    border-radius: 8px;
    box-shadow: 0 14px 34px rgba(15, 23, 42, 0.07);
  }

  .report-head {
    position: relative;
    overflow: hidden;
    padding: 16px 18px;
  }

  .report-head::before {
    position: absolute;
    inset: 0 auto 0 0;
    width: 5px;
    background: linear-gradient(180deg, #165dff, #00b42a 56%, #ff7d00);
    content: '';
  }

  .head-main {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 150px;
    gap: 16px;
    align-items: stretch;
  }

  .report-title {
    min-width: 0;
    padding-left: 2px;
  }

  .eyebrow {
    margin: 0 0 4px;
    color: #165dff;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0;
  }

  h1,
  h2,
  p,
  dl,
  dt,
  dd {
    margin: 0;
  }

  h1 {
    max-width: 920px;
    overflow: hidden;
    font-size: 21px;
    line-height: 28px;
    color: #0f172a;
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .report-subtitle {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 7px;
    color: #5b6b85;
    font-size: 13px;
  }

  .report-subtitle i,
  .case-toolbar p i {
    width: 4px;
    height: 4px;
    display: inline-block;
    border-radius: 50%;
    background: #c7d1e0;
  }

  .status-console {
    display: grid;
    align-content: center;
    justify-items: start;
    min-height: 92px;
    padding: 12px;
    background:
      linear-gradient(135deg, rgba(22, 93, 255, 0.12), rgba(22, 93, 255, 0.03)),
      #f8fbff;
    border: 1px solid #cfe0ff;
    border-radius: 8px;
  }

  .status-console strong {
    margin-top: 8px;
    color: #165dff;
    font-size: 28px;
    line-height: 32px;
    font-weight: 750;
  }

  .status-console span {
    color: #6b778c;
    font-size: 12px;
    font-weight: 600;
  }

  .meta-strip {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0;
    margin-top: 14px;
    overflow: hidden;
    border: 1px solid #e5ebf5;
    border-radius: 8px;
  }

  .meta-strip.has-task-name {
    grid-template-columns: minmax(180px, 1.6fr) repeat(5, minmax(0, 1fr));
  }

  .meta-item {
    min-width: 0;
    padding: 8px 12px;
    background: #fbfcff;
  }

  .meta-item + .meta-item {
    border-left: 1px solid #e5ebf5;
  }

  .meta-item dt,
  .metric-item span {
    display: block;
    color: #6b778c;
    font-size: 12px;
    margin-bottom: 4px;
  }

  .meta-item dd {
    overflow: hidden;
    color: #0f172a;
    font-size: 14px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .metric-strip {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
    margin: 10px 0;
  }

  .metric-item {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr);
    grid-template-areas:
      'mark label'
      'mark value';
    column-gap: 10px;
    align-items: center;
    background: #fff;
    border: 1px solid #dde5f2;
    border-radius: 8px;
    padding: 10px 12px;
    transition:
      border-color 0.2s ease,
      box-shadow 0.2s ease,
      transform 0.2s ease;
  }

  .metric-item:hover {
    border-color: #9fc3ff;
    box-shadow: 0 12px 24px rgba(22, 93, 255, 0.1);
    transform: translateY(-1px);
  }

  .metric-mark {
    grid-area: mark;
    width: 4px;
    height: 32px;
    display: block;
    border-radius: 999px;
    background: #86909c;
  }

  .metric-item span {
    grid-area: label;
    margin-bottom: 2px;
  }

  .metric-item strong {
    grid-area: value;
    font-size: 22px;
    line-height: 26px;
    color: #0f172a;
  }

  .metric-item.success .metric-mark {
    background: #00b42a;
  }

  .metric-item.fail .metric-mark {
    background: #f53f3f;
  }

  .metric-item.running .metric-mark {
    background: #ff7d00;
  }

  .metric-item.wait .metric-mark {
    background: #165dff;
  }

  .overview-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.35fr);
    gap: 10px;
    margin-bottom: 10px;
  }

  .overview-panel {
    padding: 12px 14px;
  }

  .panel-title,
  .case-toolbar,
  .type-row,
  .legend-row {
    display: flex;
    align-items: center;
  }

  .panel-title,
  .case-toolbar {
    justify-content: space-between;
    gap: 16px;
  }

  .panel-title span {
    color: #0f172a;
    font-weight: 600;
  }

  .panel-title p {
    margin-top: 2px;
    color: #86909c;
    font-size: 12px;
  }

  .panel-title strong {
    font-size: 26px;
    color: #165dff;
  }

  .ratio-bar {
    display: flex;
    height: 10px;
    overflow: hidden;
    border-radius: 4px;
    background: #edf1f7;
    margin: 14px 0 10px;
  }

  .ratio-bar i {
    display: block;
    min-width: 2px;
  }

  .ratio-bar .success,
  .dot.success {
    background: #00b42a;
  }

  .ratio-bar .fail,
  .dot.fail {
    background: #f53f3f;
  }

  .ratio-bar .running,
  .dot.running {
    background: #ff7d00;
  }

  .legend-row {
    gap: 18px;
    flex-wrap: wrap;
    color: #475569;
    font-size: 13px;
  }

  .dot {
    width: 8px;
    height: 8px;
    display: inline-block;
    border-radius: 50%;
    margin-right: 6px;
  }

  .type-progress + .type-progress {
    margin-top: 10px;
  }

  .type-row {
    justify-content: space-between;
    margin-bottom: 6px;
    color: #475569;
  }

  .type-row em {
    font-style: normal;
    color: #64748b;
  }

  .case-section {
    overflow: hidden;
    padding: 0;
  }

  .case-toolbar {
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 11px 14px;
    background: rgba(251, 252, 255, 0.97);
    border-bottom: 1px solid #e2e8f0;
    backdrop-filter: blur(8px);
  }

  .case-toolbar-main {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
  }

  .case-toolbar-copy {
    min-width: 0;
  }

  .case-toolbar h2 {
    font-size: 16px;
    color: #0f172a;
    margin-bottom: 4px;
  }

  .case-toolbar p {
    display: flex;
    align-items: center;
    gap: 7px;
    color: #475569;
    font-size: 13px;
  }

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .type-switch {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 0 0 auto;
    padding: 3px;
    border: 1px solid #e5ebf5;
    border-radius: 8px;
    background: #f7f9fc;
  }

  .type-switch-item {
    display: flex;
    align-items: center;
    gap: 5px;
    min-height: 28px;
    padding: 4px 9px;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: #475569;
    cursor: pointer;
    line-height: 18px;
    transition:
      background-color 0.2s ease,
      color 0.2s ease,
      box-shadow 0.2s ease;
  }

  .type-switch-item:hover {
    background: #eef5ff;
    color: #165dff;
  }

  .type-switch-item.active {
    background: #fff;
    color: #165dff;
    box-shadow: 0 2px 8px rgba(22, 93, 255, 0.12);
  }

  .type-switch-item span {
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
  }

  .type-switch-item strong {
    min-width: 18px;
    padding: 0 5px;
    border: 1px solid #e5ebf5;
    border-radius: 999px;
    background: #f8fafc;
    font-size: 12px;
    text-align: center;
  }

  .case-main {
    min-width: 0;
  }

  .case-spin {
    width: 100%;
    min-height: 220px;
  }

  .empty-state,
  .load-more {
    min-height: 46px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #64748b;
  }

  @media (max-width: 1100px) {
    .head-main {
      grid-template-columns: minmax(0, 1fr) 140px;
    }

    .meta-strip,
    .metric-strip,
    .overview-grid {
      grid-template-columns: 1fr 1fr;
    }

    .case-toolbar {
      align-items: flex-start;
      flex-direction: column;
    }

    .case-toolbar-main {
      align-items: flex-start;
      flex-direction: column;
      width: 100%;
    }
  }

  @media (max-width: 768px) {
    .report-lab {
      padding: 8px;
    }

    .report-head {
      padding: 14px;
    }

    .head-main {
      grid-template-columns: 1fr;
      gap: 10px;
    }

    .status-console {
      min-height: 72px;
      padding: 10px 12px;
    }

    .status-console strong {
      font-size: 24px;
      line-height: 28px;
    }

    .meta-strip,
    .metric-strip,
    .overview-grid {
      grid-template-columns: 1fr;
    }

    .type-switch {
      flex-wrap: wrap;
    }

    h1 {
      font-size: 18px;
      line-height: 25px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .metric-item {
      transition: none;
    }
  }
</style>
