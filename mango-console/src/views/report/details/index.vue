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
          <div class="status-line">
            <span>报告状态</span>
            <a-tag :color="statusColor(reportInfo.status)" size="small">
              {{ statusText(reportInfo.status) }}
            </a-tag>
          </div>
          <div class="success-rate">
            <span>成功率</span>
            <strong>{{ passRate }}%</strong>
          </div>
          <div class="success-rate-bar">
            <i :style="{ width: `${passRate}%` }"></i>
          </div>
        </div>
      </div>

      <dl class="meta-strip" :class="{ 'has-task-name': hasTaskName }">
        <div v-if="hasTaskName" class="report-meta-item wide">
          <dt>任务名称</dt>
          <dd>{{ reportInfo.tasks?.name || '-' }}</dd>
        </div>
        <div class="report-meta-item">
          <dt>报告ID</dt>
          <dd>{{ reportInfo.id || reportId }}</dd>
        </div>
        <div class="report-meta-item">
          <dt>测试环境</dt>
          <dd>{{ envText(reportInfo.test_env) }}</dd>
        </div>
        <div class="report-meta-item">
          <dt>执行人</dt>
          <dd>{{ reportInfo.user?.name || '-' }}</dd>
        </div>
        <div class="report-meta-item">
          <dt>通知状态</dt>
          <dd>
            <a-tag :color="noticeColor(reportInfo.is_notice)" size="small">
              {{ noticeText(reportInfo.is_notice) }}
            </a-tag>
          </dd>
        </div>
        <div class="report-meta-item">
          <dt>执行时间</dt>
          <dd>{{ reportInfo.create_time || '-' }}</dd>
        </div>
      </dl>
    </section>

    <section class="overview-grid">
      <div class="result-stack">
        <div class="overview-panel result-panel">
          <div class="panel-title">
            <div>
              <span>执行结果占比</span>
              <p>总用例 {{ totalCount }}，按当前报告状态分布</p>
            </div>
            <strong>{{ passRate }}%</strong>
          </div>
          <StatusChart
            :success="summary.success_count || 0"
            :fail="summary.fail_count || 0"
            :pending="summary.proceed_count || 0"
            :todo="summary.stay_begin_count || 0"
          />
        </div>

        <div class="overview-panel failure-panel">
          <div class="panel-title">
            <div>
              <span>失败聚焦</span>
              <p>快速收敛到需要排查的用例</p>
            </div>
            <strong>{{ failRatio }}%</strong>
          </div>
          <div class="failure-body">
            <div>
              <span>失败用例</span>
              <strong>{{ summary.fail_count || 0 }}</strong>
            </div>
            <button type="button" @click="focusFailed">只看失败</button>
          </div>
        </div>
      </div>

      <div class="overview-panel failure-reason-panel">
        <div class="panel-title">
          <div>
            <span>失败原因 Top</span>
            <p>基于当前已加载失败明细聚合</p>
          </div>
          <em>{{ failureReasons.length }} 类</em>
        </div>
        <div v-if="failureReasons.length === 0" class="reason-empty">
          当前已加载数据中暂无失败原因
        </div>
        <div v-else class="reason-list">
          <div
            v-for="item in failureReasons"
            :key="item.message"
            class="reason-item"
            :title="item.message"
          >
            <div class="reason-main">
              <span>{{ item.message }}</span>
              <i>
                <b :style="{ width: `${item.percent}%` }"></b>
              </i>
            </div>
            <strong>{{ item.count }}</strong>
          </div>
        </div>
      </div>

      <div class="overview-panel type-panel">
        <div class="panel-title">
          <div>
            <span>执行覆盖进度</span>
            <p>各自动化类型已执行 / 总用例</p>
          </div>
          <em v-if="summaryLoading">更新中</em>
        </div>
        <div v-for="item in typeProgress" :key="item.key" class="type-progress">
          <div class="type-row">
            <div>
              <span>{{ item.label }}</span>
              <small>{{ item.done >= item.total ? '已执行完成' : '执行中' }}</small>
            </div>
            <em>{{ item.done }}/{{ item.total }}</em>
          </div>
          <div class="execution-progress">
            <a-progress :percent="item.percent" :show-text="false" :stroke-width="10" />
            <strong>{{ Math.round(item.percent * 100) }}%</strong>
          </div>
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
              <a-radio value="all">全部</a-radio>
              <a-radio :value="0">失败</a-radio>
              <a-radio :value="1">成功</a-radio>
              <a-radio :value="3">进行中</a-radio>
              <a-radio :value="2">待开始</a-radio>
            </a-radio-group>
          </div>
        </div>

        <a-spin :loading="caseLoading && cases.length === 0" class="case-spin">
          <div v-if="cases.length === 0" class="empty-state">
            {{ caseLoading ? '正在加载用例结果' : '暂无用例结果' }}
          </div>
          <UiCaseTable
            v-else-if="activeType === '0'"
            :cases="cases"
            :enum-store="enumStore"
            :can-retry="canRetry"
            :loading="false"
            @show-details="showDetails"
            @retry="onRetry"
          />
          <ApiCaseTable
            v-else-if="activeType === '1'"
            :cases="cases"
            :enum-store="enumStore"
            :can-retry="canRetry"
            :loading="false"
            @show-details="showDetails"
            @retry="onRetry"
          />
          <PytestCaseTable
            v-else-if="activeType === '2'"
            :cases="cases"
            :enum-store="enumStore"
            :can-retry="canRetry"
            :loading="false"
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
      <div v-if="!selectedCaseHasDetail" class="report-detail-empty">
        暂无详细执行结果
      </div>
      <section
        v-else-if="selectedCase.case_type === 0"
        class="mango-section-card report-detail-drawer-card"
      >
        <div class="mango-section-title">
          <div>
            <h2>{{ selectedCase?.name }}</h2>
            <p>UI 自动化执行明细</p>
          </div>
        </div>
        <ElementTestReport :resultData="selectedCase" />
      </section>
      <section
        v-else-if="selectedCase.case_type === 1"
        class="mango-section-card report-detail-drawer-card"
      >
        <div class="mango-section-title">
          <div>
            <h2>{{ selectedCase?.name }}</h2>
            <p>API 自动化执行明细</p>
          </div>
        </div>
        <ApiTestReport :resultData="selectedCase" />
      </section>
      <section
        v-else-if="selectedCase.case_type === 2"
        class="mango-section-card report-detail-drawer-card"
      >
        <div class="mango-section-title">
          <div>
            <h2>{{ selectedCase?.name }}</h2>
            <p>Pytest 执行明细</p>
          </div>
        </div>
        <PytestTestReport :resultData="selectedCase" />
      </section>
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
  import ElementTestReport from '@/components/reports/ElementTestReport.vue'
  import ApiTestReport from '@/components/reports/ApiTestReport.vue'
  import PytestTestReport from '@/components/reports/PytestTestReport.vue'
  import UiCaseTable from './UiCaseTable.vue'
  import ApiCaseTable from './ApiCaseTable.vue'
  import PytestCaseTable from './PytestCaseTable.vue'
  import StatusChart from '@/components/chart/StatusChart.vue'

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
  const caseStatus = ref<number | 'all'>('all')
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

  const reportId = computed(() =>
    String(route.query.id || pageData.record?.id || reportInfo.value?.id || '')
  )
  const totalCount = computed(() => summary.value.count || 0)
  const failRatio = computed(() => ratio(summary.value.fail_count, totalCount.value))
  const passRate = computed(() => ratio(summary.value.success_count, totalCount.value))
  const hasTaskName = computed(() => !!reportInfo.value.tasks?.name)
  const failureReasons = computed(() => {
    const counter = new Map<string, number>()
    ;(cases.value || []).forEach((item: any) => {
      const rows =
        Array.isArray(item?.children) && item.children.length > 0 ? item.children : [item]
      rows.forEach((row: any) => {
        if (Number(row?.status) !== 0) return
        const rawMessage =
          row?.error_message ||
          row?.statusDetails?.message ||
          row?.response?.error ||
          row?.message ||
          '未返回失败原因'
        const message = String(rawMessage).replace(/\s+/g, ' ').trim() || '未返回失败原因'
        counter.set(message, (counter.get(message) || 0) + 1)
      })
    })
    const max = Math.max(...Array.from(counter.values()), 1)
    return Array.from(counter.entries())
      .map(([message, count]) => ({
        message,
        count,
        percent: Math.round((count / max) * 100),
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5)
  })

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
    return caseStatus.value === 'all' ? '全部结果' : map[caseStatus.value] || '全部结果'
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

  const selectedCaseHasDetail = computed(() => {
    const record = selectedCase.value || {}
    const caseType = Number(record?.case_type ?? activeType.value)
    if (caseType === 0) {
      return (
        (Array.isArray(record?.element_result_list) && record.element_result_list.length > 0) ||
        (Array.isArray(record?.children) && record.children.length > 0)
      )
    }
    if (caseType === 1) {
      return !!(
        record?.request ||
        record?.response ||
        record?.ass ||
        record?.error_message ||
        record?.name
      )
    }
    if (caseType === 2) {
      return !!(
        record?.attachments ||
        record?.statusDetails ||
        record?.fullName ||
        record?.description ||
        record?.name
      )
    }
    return false
  })

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
    if (caseStatus.value !== 'all') {
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
      if (
        firstVisibleType &&
        !visibleTypeTabs.value.some((item) => item.key === activeType.value)
      ) {
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

  function focusFailed() {
    caseStatus.value = 0
    reloadCases()
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
        list.length < loadedPageSize || (pagination.total > 0 && list.length >= pagination.total)
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
    const hasInProgress =
      (summary.value.stay_begin_count || 0) > 0 || (summary.value.proceed_count || 0) > 0
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
      onBeforeOk: () => {
        return getSystemTestSuiteDetailsRetry(id)
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
    background: var(--m-bg);
    color: var(--m-text);
  }

  .standalone-report-container {
    height: 100vh;
    overflow-x: hidden;
    overflow-y: auto;
  }

  .report-head,
  .overview-panel,
  .case-section {
    background: var(--m-surface);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    box-shadow: var(--m-shadow);
  }

  .report-detail-empty {
    min-height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
    font-size: 14px;
  }

  .report-head {
    position: relative;
    overflow: hidden;
    padding: 14px 16px 12px;
  }

  .report-head::before {
    position: absolute;
    inset: 0 auto 0 0;
    width: 3px;
    background: linear-gradient(180deg, var(--m-primary), var(--m-success));
    content: '';
  }

  .head-main {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 156px;
    gap: 16px;
    align-items: stretch;
  }

  .report-title {
    min-width: 0;
    padding-left: 2px;
  }

  .eyebrow {
    margin: 0 0 5px;
    color: var(--m-muted);
    font-size: 11px;
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
    font-size: 22px;
    line-height: 30px;
    color: var(--m-text);
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .report-subtitle {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
    color: var(--m-muted);
    font-size: 13px;
  }

  .report-subtitle i,
  .case-toolbar p i {
    width: 4px;
    height: 4px;
    display: inline-block;
    border-radius: 50%;
    background: var(--m-border-strong);
  }

  .status-console {
    display: flex;
    min-height: 88px;
    flex-direction: column;
    justify-content: center;
    gap: 7px;
    padding: 11px 12px;
    background: var(--m-surface-soft);
    border: 1px solid var(--m-primary-border);
    border-radius: var(--m-radius-lg);
  }

  .status-line,
  .status-console .success-rate {
    display: flex;
    width: 100%;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .status-line span,
  .status-console .success-rate span {
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }

  .status-console .success-rate strong {
    color: var(--m-primary);
    font-size: 14px;
    font-weight: 700;
    line-height: 20px;
    white-space: nowrap;
  }

  .success-rate-bar {
    height: 5px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--m-border);
  }

  .success-rate-bar i {
    display: block;
    height: 100%;
    min-width: 2px;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--m-primary), var(--m-success));
  }

  .meta-strip {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0;
    margin-top: 13px;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
  }

  .meta-strip.has-task-name {
    grid-template-columns: minmax(180px, 1.6fr) repeat(5, minmax(0, 1fr));
  }

  .report-meta-item {
    min-width: 0;
    padding: 8px 12px;
    background: var(--m-surface);
  }

  .report-meta-item + .report-meta-item {
    border-left: 1px solid var(--m-border);
  }

  .report-meta-item dt {
    display: block;
    color: var(--m-muted);
    font-size: 12px;
    margin-bottom: 4px;
  }

  .report-meta-item dd {
    overflow: hidden;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .overview-grid {
    display: grid;
    grid-template-columns: 480px minmax(640px, 780px) minmax(420px, 1fr);
    align-items: stretch;
    gap: 12px;
    margin-bottom: 12px;
    margin-top: 12px;
  }

  .overview-panel {
    height: 100%;
    min-height: 0;
    padding: 11px 13px;
  }

  .result-stack {
    display: grid;
    height: 100%;
    min-width: 0;
    grid-template-rows: minmax(0, 1fr) 126px;
    gap: 12px;
  }

  .result-panel {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .result-panel :deep(.status-chart) {
    height: 168px;
    flex: 0 0 auto;
    min-height: 0;
  }

  .failure-reason-panel {
    display: flex;
    height: 100%;
    min-width: 0;
    flex-direction: column;
  }

  .failure-reason-panel .panel-title em {
    color: var(--m-muted);
    font-style: normal;
    font-size: 12px;
    white-space: nowrap;
  }

  .reason-empty {
    display: flex;
    min-height: 112px;
    align-items: center;
    justify-content: center;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-lg);
    color: var(--m-muted);
    font-size: 13px;
  }

  .reason-list {
    display: flex;
    flex: 1;
    min-height: 0;
    flex-direction: column;
    justify-content: space-around;
    gap: 8px;
    margin-top: 12px;
    padding: 4px 0;
  }

  .reason-item {
    display: grid;
    width: 100%;
    min-height: 34px;
    grid-template-columns: minmax(0, 1fr) 36px;
    align-items: center;
    gap: 10px;
    padding: 6px 9px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    color: inherit;
    text-align: left;
  }

  .reason-main {
    min-width: 0;
  }

  .reason-main span {
    display: block;
    overflow: hidden;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .reason-main i {
    display: block;
    height: 4px;
    margin-top: 5px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--m-border);
  }

  .reason-main b {
    display: block;
    height: 100%;
    min-width: 2px;
    border-radius: inherit;
    background: color-mix(in srgb, var(--m-danger) 45%, transparent);
  }

  .reason-item strong {
    color: var(--m-danger);
    font-size: 16px;
    text-align: right;
  }

  .type-panel,
  .failure-panel {
    min-height: 0;
  }

  .panel-title,
  .case-toolbar,
  .type-row {
    display: flex;
    align-items: center;
  }

  .panel-title,
  .case-toolbar {
    justify-content: space-between;
    gap: 16px;
  }

  .panel-title span {
    color: var(--m-text);
    font-weight: 600;
  }

  .panel-title p {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .panel-title strong {
    font-size: 24px;
    color: var(--m-primary);
  }

  .type-progress + .type-progress {
    margin-top: 11px;
  }

  .type-row {
    justify-content: space-between;
    margin-bottom: 6px;
    color: var(--m-text-2);
  }

  .type-row div {
    min-width: 0;
  }

  .type-row span,
  .type-row small {
    display: block;
  }

  .type-row span {
    color: var(--m-text);
    font-weight: 600;
  }

  .type-row small {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .type-row em {
    font-style: normal;
    color: var(--m-primary);
    font-weight: 700;
  }

  .execution-progress {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 44px;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .execution-progress strong {
    color: var(--m-primary);
    font-size: 13px;
    text-align: right;
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
    padding: 12px 14px;
    background: color-mix(in srgb, var(--m-surface) 94%, transparent);
    border-bottom: 1px solid var(--m-border);
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
    color: var(--m-text);
    margin-bottom: 4px;
  }

  .case-toolbar p {
    display: flex;
    align-items: center;
    gap: 7px;
    color: var(--m-text-2);
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
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface-soft);
  }

  .failure-panel {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .failure-panel .panel-title strong {
    color: var(--m-danger);
  }

  .failure-body {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 92px;
    align-items: center;
    gap: 12px;
    margin-top: 8px;
  }

  .failure-body span {
    display: block;
    color: var(--m-muted);
    font-size: 12px;
  }

  .failure-body strong {
    color: var(--m-text);
    font-size: 28px;
    line-height: 32px;
  }

  .failure-body button {
    width: 100%;
    height: 32px;
    padding: 0 12px;
    border: 1px solid color-mix(in srgb, var(--m-danger) 34%, transparent);
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-danger) 10%, var(--m-surface));
    color: var(--m-danger);
    cursor: pointer;
    font-size: 13px;
    transition: border-color 0.2s ease, background-color 0.2s ease;
  }

  .failure-body button:hover {
    border-color: var(--m-danger);
    background: color-mix(in srgb, var(--m-danger) 14%, var(--m-surface));
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
    color: var(--m-text-2);
    cursor: pointer;
    line-height: 18px;
    transition: background-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
  }

  .type-switch-item:hover {
    background: var(--m-primary-soft);
    color: var(--m-primary);
  }

  .type-switch-item.active {
    background: var(--m-surface);
    color: var(--m-primary);
    box-shadow: var(--m-shadow);
  }

  .type-switch-item span {
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
  }

  .type-switch-item strong {
    min-width: 18px;
    padding: 0 5px;
    border: 1px solid var(--m-border);
    border-radius: 999px;
    background: var(--m-surface-soft);
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
    color: var(--m-muted);
  }

  @media (max-width: 1px) {
    .head-main {
      grid-template-columns: minmax(0, 1fr) 140px;
    }

    .meta-strip,
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

  @media (max-width: 1px) {
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
</style>
