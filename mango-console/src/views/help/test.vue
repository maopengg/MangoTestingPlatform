<template>
  <div class="report-lab">
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

      <dl class="meta-strip">
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
      <div class="case-toolbar">
        <div>
          <h2>测试套用例列表</h2>
          <p>
            <span>{{ currentTypeLabel }}</span>
            <i></i>
            <span>{{ currentStatusLabel }}</span>
            <i></i>
            <span>已加载 {{ cases.length }} / {{ pagination.total || '未知' }}</span>
          </p>
        </div>
        <div class="toolbar-actions">
          <a-tabs
            v-if="visibleTypeTabs.length > 0"
            v-model:active-key="activeType"
            class="type-tabs"
            type="rounded"
            @change="reloadCases"
          >
            <a-tab-pane
              v-for="item in visibleTypeTabs"
              :key="item.key"
              :title="`${item.label} (${item.total})`"
            />
          </a-tabs>
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
        <a-table
          v-else
          :bordered="false"
          :data="flatCaseRows"
          :pagination="false"
          :scroll="{ x: summaryTableScrollX }"
          :span-method="caseSpanMethod"
          class="case-table case-summary-table"
          row-key="__rowKey"
        >
          <template #columns>
            <a-table-column
              title="用例ID"
              data-index="__caseId"
              key="__caseId"
              :width="78"
              align="center"
            >
              <template #cell="{ record }">
                <span class="case-id-cell">{{ record.__caseId }}</span>
              </template>
            </a-table-column>
            <a-table-column
              title="用例名称"
              data-index="__caseName"
              key="__caseName"
              :width="220"
              align="left"
              :ellipsis="true"
              :tooltip="true"
            >
              <template #cell="{ record }">
                <span class="case-name-cell">{{ record.__caseName }}</span>
              </template>
            </a-table-column>
            <a-table-column
              v-if="activeType === '1'"
              title="接口名称"
              data-index="__apiInfoName"
              key="__apiInfoName"
              :width="180"
              align="left"
              :ellipsis="true"
              :tooltip="true"
            >
              <template #cell="{ record }">
                <span class="case-name-cell">{{ record.__apiInfoName || '-' }}</span>
              </template>
            </a-table-column>
            <a-table-column
              title="数量"
              data-index="__caseCount"
              key="__caseCount"
              :width="92"
              align="center"
            >
              <template #cell="{ record }">
                <span class="case-count">共 {{ record.__caseCount }} 条</span>
              </template>
            </a-table-column>
            <a-table-column
              v-for="itemRow of displayColumns"
              :key="itemRow.key || itemRow.dataIndex"
              :align="itemRow.align ? itemRow.align : 'center'"
              :data-index="itemRow.dataIndex"
              :fixed="itemRow.fixed"
              :title="itemRow.title"
              :width="itemRow.width"
              :ellipsis="itemRow.ellipsis"
              :tooltip="itemRow.tooltip"
            >
              <template v-if="itemRow.key === 'id'" #cell="{ record }">
                <span>{{ activeType === '1' ? record.api_info_id : record.id }}</span>
              </template>
              <template v-else-if="itemRow.key === 'status'" #cell="{ record }">
                <a-tag :color="statusColor(record.status)" size="small">
                  {{ statusText(record.status) }}
                </a-tag>
              </template>
              <template v-else-if="itemRow.key === 'request_url'" #cell="{ record }">
                <span>{{ record?.request?.url }}</span>
              </template>
              <template v-else-if="itemRow.key === 'response_time'" #cell="{ record }">
                <span>{{ formatDuration(record?.response?.time) }}</span>
              </template>
              <template v-else-if="itemRow.key === 'start'" #cell="{ record }">
                <span>{{ formatDateTime(record.start) }}</span>
              </template>
              <template v-else-if="itemRow.key === 'stop'" #cell="{ record }">
                <span>{{ formatDateTime(record.stop) }}</span>
              </template>
              <template v-else-if="itemRow.key === 'error_message'" #cell="{ record }">
                <span class="error-message-cell" :title="errorMessage(record)">
                  {{ errorMessage(record) }}
                </span>
              </template>
              <template v-else-if="itemRow.key === 'actions'" #cell="{ record }">
                <a-button
                  v-if="!record.children"
                  class="detail-action"
                  type="text"
                  size="mini"
                  @click="showDetails(record)"
                >
                  查看详细报告
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-spin>

      <div ref="loadMoreRef" class="load-more">
        <a-spin v-if="caseLoading && cases.length > 0" size="small" />
        <span v-else-if="pagination.finished && cases.length > 0">没有更多了</span>
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
  import { Message } from '@arco-design/web-vue'
  import {
    getSystemTestSuiteDetailsShare,
    getSystemTestSuiteDetailsSummaryShare,
  } from '@/api/system/test_sute_details'
  import { getSystemTestSuiteShare } from '@/api/system/test_suite'
  import { useEnum } from '@/store/modules/get-enum'
  import ElementTestReport from '@/components/ElementTestReport.vue'
  import ApiTestReport from '@/components/ApiTestReport.vue'
  import PytestTestReport from '@/components/PytestTestReport.vue'
  import { apiColumns, pytestColumns, uiColumns } from '@/views/report/details/config'

  const reportId = '327944931111'
  const enumStore = useEnum()
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
  let observer: IntersectionObserver | null = null

  const pagination = reactive({
    page: 1,
    pageSize: 20,
    total: 0,
    finished: false,
  })

  const unfinishedCount = computed(
    () => (summary.value.stay_begin_count || 0) + (summary.value.proceed_count || 0)
  )
  const totalCount = computed(() => summary.value.count || 0)
  const successRatio = computed(() => ratio(summary.value.success_count, totalCount.value))
  const failRatio = computed(() => ratio(summary.value.fail_count, totalCount.value))
  const runningRatio = computed(() => ratio(unfinishedCount.value, totalCount.value))
  const passRate = computed(() => ratio(summary.value.success_count, totalCount.value))

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

  const currentColumns = computed(() => {
    if (activeType.value === '1') return apiColumns
    if (activeType.value === '2') return pytestColumns
    return uiColumns
  })
  const displayColumns = computed(() => {
    const columns = activeType.value === '1'
      ? currentColumns.value
      .filter((item: any) => !['id', 'request_url'].includes(item.key))
      .map((item: any) => {
        if (item.key === 'name') return { ...item, title: '场景名称' }
        if (item.key === 'response_time') return { ...item, title: '响应时间(秒)' }
        return item
      })
      : currentColumns.value

    return columns.map((item: any) => normalizeColumnWidth(item))
  })
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
  const summaryTableScrollX = computed(() => '100%')
  const flatCaseRows = computed(() =>
    cases.value.flatMap((item) => {
      const children = caseChildren(item)
      const rows = children.length > 0 ? children : [item]
      const rowSpan = rows.length
      const caseId = item?.case_id || item?.id || '-'
      const caseName = item?.case_name || item?.name || '未命名用例'
      const apiInfoName = item?.api_info_name || rows.find((row: any) => row?.api_info_name)?.api_info_name
      return rows.map((row: any, index: number) => ({
        ...row,
        case_type: row?.case_type ?? Number(activeType.value),
        name: row?.name || item?.case_name || item?.name,
        __rowKey: `${item?.id || caseId}-${row?.id || index}-${index}`,
        __caseId: caseId,
        __caseName: caseName,
        __apiInfoName: row?.api_info_name || apiInfoName || '-',
        __caseCount: caseChildCount(item) || rowSpan,
        __caseRowSpan: index === 0 ? rowSpan : 0,
      }))
    })
  )

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

  function normalizeColumnWidth(item: any) {
    const column = { ...item }
    const widthMap: Record<string, number> = {
      id: activeType.value === '1' ? 0 : 82,
      name: activeType.value === '1' ? 170 : 180,
      test_time: 142,
      stop_time: 142,
      start: 142,
      stop: 142,
      response_time: 112,
      status: 94,
      actions: 116,
      test_object: 160,
    }

    if (column.key === 'error_message' || column.dataIndex === 'error_message') {
      delete column.width
      column.ellipsis = true
      column.tooltip = true
      return column
    }

    if (widthMap[column.key]) {
      column.width = widthMap[column.key]
    }
    return column
  }

  function getTotal(res: any) {
    return Number(res?.totalSize || res?.total || res?.count || 0)
  }

  function formatDateTime(timestamp: number | string) {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  }

  function formatDuration(value: number | string) {
    if (value === undefined || value === null || value === '') return ''
    const duration = Number(value)
    if (Number.isNaN(duration)) return `${value} 秒`
    return `${duration.toFixed(2)} 秒`
  }

  function errorMessage(record: any) {
    return activeType.value === '2' ? record?.statusDetails?.message : record?.error_message
  }

  function caseChildren(item: any) {
    return Array.isArray(item?.children) ? item.children : []
  }

  function caseChildCount(item: any) {
    return Number(item?.case_sum || caseChildren(item).length || 0)
  }

  function caseSpanMethod({ record, columnIndex }: any) {
    const mergedColumnCount = activeType.value === '1' ? 4 : 3
    if (columnIndex >= mergedColumnCount) return undefined
    return {
      rowspan: record.__caseRowSpan,
      colspan: record.__caseRowSpan > 0 ? 1 : 0,
    }
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
      test_suite_id: reportId,
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
    const res = await getSystemTestSuiteShare(reportId)
    reportInfo.value = res.data || {}
  }

  async function loadSummary() {
    summaryLoading.value = true
    try {
      const res = await getSystemTestSuiteDetailsSummaryShare(reportId)
      summary.value = res.data || {}
      const [firstVisibleType] = visibleTypeTabs.value
      if (firstVisibleType) {
        activeType.value = firstVisibleType.key
      }
    } finally {
      summaryLoading.value = false
    }
  }

  async function loadCases(reset = false) {
    if (caseLoading.value) return
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

  function initObserver() {
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

  onMounted(async () => {
    if (!enumStore.task_status?.length) {
      enumStore.getEnumShare()
    }
    await Promise.all([loadReportInfo(), loadSummary()])
    await loadCases(true)
    nextTick(initObserver)
  })

  onUnmounted(() => {
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
    border-top: 0;
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

  .report-subtitle i {
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
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0;
    margin-top: 14px;
    overflow: hidden;
    border: 1px solid #e5ebf5;
    border-radius: 8px;
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
    position: relative;
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
  .legend-row,
  .case-header {
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
    padding: 0 14px 14px;
  }

  .case-toolbar {
    position: sticky;
    top: 0;
    z-index: 5;
    margin: 0 -14px 10px;
    padding: 11px 14px;
    background: rgba(251, 252, 255, 0.97);
    border-bottom: 1px solid #e2e8f0;
    backdrop-filter: blur(8px);
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

  .case-toolbar p i {
    width: 4px;
    height: 4px;
    display: inline-block;
    border-radius: 50%;
    background: #cbd5e1;
  }

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .toolbar-actions :deep(.arco-btn),
  .detail-action {
    cursor: pointer;
  }

  .type-tabs {
    margin-bottom: 0;
  }

  .type-tabs :deep(.arco-tabs-nav) {
    background: #f7f9fc;
    border: 1px solid #e5ebf5;
    border-radius: 8px;
    padding: 2px 6px 0;
  }

  .type-tabs :deep(.arco-tabs-nav-tab) {
    padding-bottom: 0;
  }

  .type-tabs :deep(.arco-tabs-content) {
    display: none;
  }

  .case-spin {
    width: 100%;
    min-height: 220px;
  }

  .case-header {
    display: grid;
    grid-template-columns: max-content minmax(240px, 460px) max-content minmax(180px, 1fr);
    align-items: center;
    width: 100%;
    gap: 10px;
    min-width: 0;
    cursor: pointer;
  }

  .case-header :deep(.arco-tag) {
    width: max-content;
    justify-self: start;
  }

  .case-header strong {
    min-width: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    color: #0f172a;
  }

  .case-count {
    width: max-content;
    justify-self: start;
    padding: 2px 8px;
    border-radius: 999px;
    background: #f1f5f9;
    color: #475569;
    font-size: 12px;
    white-space: nowrap;
  }

  .case-error {
    min-width: 0;
    max-width: 100%;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    color: #dc2626;
    font-size: 12px;
  }

  :deep(.arco-collapse-item) {
    overflow: hidden;
    border: 1px solid #e5ebf5;
    border-radius: 8px;
    background: #fff;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.03);
  }

  :deep(.arco-collapse-item-header) {
    min-height: 44px;
    background: #fff;
    transition:
      background-color 0.2s ease,
      color 0.2s ease;
  }

  :deep(.arco-collapse-item-header:hover) {
    background: #f7faff;
  }

  :deep(.arco-collapse-item-active > .arco-collapse-item-header) {
    background: #f7faff;
    border-bottom: 1px solid #e5ebf5;
  }

  .case-table {
    overflow-x: auto;
    padding: 8px 10px 10px;
    background: #fbfcff;

    :deep(.arco-table-th) {
      background: #f2f5fa;
      color: #334155;
      font-weight: 600;
    }

    :deep(.arco-table-td) {
      color: #475569;
      transition: background-color 0.2s ease;
    }

    :deep(.arco-table-tr:hover .arco-table-td) {
      background: #f7faff;
    }

    :deep(.arco-table-cell) {
      white-space: nowrap;
    }
  }

  .case-summary-table {
    padding: 0;
    border: 0;
    border-radius: 0;
    background: #fff;

    :deep(.arco-table-container) {
      border: 0;
      border-radius: 0;
    }

    :deep(.arco-table),
    :deep(.arco-table-element) {
      width: 100%;
      table-layout: fixed;
    }

    :deep(.arco-table-border .arco-table-container) {
      border: 0;
    }

    :deep(.arco-table-th),
    :deep(.arco-table-td) {
      border-right: 0;
      border-bottom-color: transparent;
    }

    :deep(.arco-table-td:first-child),
    :deep(.arco-table-td:nth-child(2)),
    :deep(.arco-table-td:nth-child(3)) {
      background: #fbfcff;
      vertical-align: top;
    }
  }

  .case-id-cell {
    color: #4e5969;
  }

  .case-name-cell {
    display: block;
    min-width: 0;
    overflow: hidden;
    color: #0f172a;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .error-message-cell {
    display: block;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

    .report-title,
    .toolbar-actions {
      align-items: flex-start;
      flex-direction: column;
    }

    .meta-strip,
    .metric-strip,
    .overview-grid {
      grid-template-columns: 1fr;
    }

    h1 {
      font-size: 18px;
      line-height: 25px;
    }

    .case-header {
      grid-template-columns: max-content minmax(0, 1fr);
      align-items: start;
    }

    .case-header strong {
      min-width: 0;
    }

    .case-count,
    .case-error {
      grid-column: 2;
      max-width: 100%;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .metric-item,
    :deep(.arco-collapse-item-header),
    .case-table :deep(.arco-table-td) {
      transition: none;
    }
  }
</style>
