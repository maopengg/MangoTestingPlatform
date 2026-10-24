<template>
  <TableBody
    ref="tableBody"
    plain
    class="mango-detail-workbench-page"
    :sticky-horizontal-scroll="false"
  >
    <template #header>
      <TableHeader title="执行报告" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        class="mango-report-workbench"
        contained-body
        show-modules
        :show-toolbar="false"
        :model-value="projectProductCondition?.value"
        :module-value="moduleCondition?.value"
        :reset-key="sidebarResetKey"
        @filter-change="onNavigationFilterChange"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="enumStore.task_status"
                  @change="doRefresh"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && ['tasks_id', 'tasks__task_group_id'].includes(item.key)">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="item.optionItems"
                  :loading="item.key === 'tasks_id' ? data.tasksLoading : data.taskGroupOptionsLoading"
                  :class="{ 'mango-report-task-group-filter': item.key === 'tasks__task_group_id' }"
                  :title="item.key === 'tasks__task_group_id' ? selectedTaskGroupTitle : undefined"
                  @change="doRefresh"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="item.optionItems"
                  :loading="data.userLoading"
                  @change="doRefresh"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="searchOptions(item.key)"
                  :field-names="fieldNames"
                  @change="doRefresh"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'date-range'">
                <a-range-picker
                  v-model="item.value"
                  value-format="YYYY-MM-DD"
                  :placeholder="['开始日期', '结束日期']"
                  allow-clear
                  @change="doRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
        <div class="mango-workbench-scroll-x report-chart-scroll">
          <div class="report-chart-grid">
            <section class="report-chart-card status-card mango-section-card">
              <Title title="执行报告结果分布" />
              <StatusChart
                :success="data.statusCounts.success"
                :fail="data.statusCounts.fail"
                :warning="data.statusCounts.warning"
                :pending="data.statusCounts.pending"
                :todo="data.statusCounts.todo"
                :stopped="data.statusCounts.stopped"
                :loading="data.chartLoading"
                total-label="报告总数"
              />
            </section>

            <section class="report-chart-card trend-card mango-section-card">
              <Title title="近 12 周执行报告趋势" />
              <ReportTrendChart
                :items="data.trend"
                :loading="data.chartLoading"
              />
            </section>
          </div>
        </div>
        <StickyHorizontalTable :scroll-x="2180" content-class="report-table-region">
          <a-table
            :bordered="false"
            :loading="table.tableLoading.value"
            :data="table.dataList"
            :columns="tableColumns"
            :pagination="false"
            :rowKey="rowKey"
            :scroll="{ x: 2180, y: '100%' }"
          >
            <template #columns>
              <a-table-column
                v-for="item of tableColumns"
                :key="item.key"
                :align="item.align"
                :title="item.title"
                :width="item.width"
                :data-index="item.key"
                :fixed="item.fixed"
                :ellipsis="item.ellipsis"
                :tooltip="item.tooltip"
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  <span class="report-id-cell">{{ record.id }}</span>
                </template>
                <template v-else-if="item.key === 'test_env'" #cell="{ record }">
                  <a-tag
                    :color="optionTagColor(enumStore.environment_type, record.test_env)"
                    size="small"
                    >{{ enumStore.environment_type.find((item) => String(item.key) === String(record.test_env))?.title }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'user'" #cell="{ record }">
                  {{ record.user?.name }}
                </template>
                <template v-else-if="item.key === 'tasks'" #cell="{ record }">
                  {{ reportExecutionName(record) }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ record.module ? formatModulePath(record.module) : '-' }}
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-tag :color="enumStore.status_colors[record.report_conclusion ?? record.status]" size="small"
                    >{{ enumStore.task_status[record.report_conclusion ?? record.status]?.title || '-' }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'excluded_count'" #cell="{ record }">
                  <a-tooltip v-if="record.execution_summary?.excluded_count" content="已排除的执行项不参与结果统计，原始执行结果保留">
                    <a-tag size="small" color="orange">已排除 {{ record.execution_summary.excluded_count }}</a-tag>
                  </a-tooltip>
                  <span v-else>-</span>
                </template>
                <template v-else-if="item.key === 'execution_summary'" #cell="{ record }">
                  <div class="mango-report-result-summary">
                    <span
                      v-for="summaryItem in reportResultSummaryItems"
                      :key="summaryItem.key"
                      :class="[
                        'mango-report-result-summary__item',
                        `mango-report-result-summary__item--${summaryItem.tone}`,
                        {
                          'mango-report-result-summary__item--zero': !reportResultCount(
                            record,
                            summaryItem.key,
                          ),
                        },
                      ]"
                    >
                      {{ summaryItem.label }}
                      <strong>{{ reportResultCount(record, summaryItem.key) }}</strong>
                    </span>
                  </div>
                </template>
                <template v-else-if="item.key === 'is_notice'" #cell="{ record }">
                  <a-tag :color="enumStore.colors[record.is_notice]" size="small"
                    >{{ enumStore.test_suite_notice[record.is_notice]?.title || '-' }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'execution_scenes'" #cell="{ record }">
                  <ExecutionSceneTagGrid
                    :values="record.execution_scenes"
                    :options="enumStore.automation_execution_scene"
                    :colors="enumStore.colors"
                  />
                </template>
                <template v-else-if="item.key === 'execution_scope'" #cell="{ record }">
                  <a-tag
                    :color="
                      optionTagColor(enumStore.automation_execution_scope, record.execution_scope)
                    "
                    size="small"
                  >
                    {{ optionTitle(enumStore.automation_execution_scope, record.execution_scope) }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'api_concurrency_limit'" #cell="{ record }">
                  {{ record.api_concurrency_limit ?? '使用全局并发' }}
                </template>
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ formatProjectProductPath(record.project_product) }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[
                      { permission: 'report:retry',
                        label: '重试',
                        hidden: record.automation_types?.includes(4),
                        priority: 0,
                        loading: data.retryLoading && data.retryRecord?.id === record.id,
                        onClick: () => onRetry(record),
                      },
                      { permission: 'report:retry',
                        label: '立即停止',
                        priority: 3,
                        danger: true,
                        hidden: !isReportRunning(record) || record.automation_types?.includes(4),
                        loading: data.stopLoadingId === record.id,
                        onClick: () => onStop(record),
                      },
                      { permission: 'report:detail', label: '明细', priority: 1, onClick: () => onClick(record) },
                      { permission: 'report:detail',
                        label: '排查结果',
                        priority: 2,
                        onClick: () => openReportDiagnostic(record),
                      },
                      { permission: 'report:notice',
                        label: '重发通知',
                        priority: 3,
                        loading: data.noticeSendingId === record.id,
                        onClick: () => onSendNotice(record),
                      },
                    ]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </StickyHorizontalTable>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <TestExecutionModal
    ref="retryModalRef"
    title="重试测试报告"
    :width="560"
    :platform-limit="data.apiPlatformLimit"
    concurrency-placeholder="留空则保留报告当前并发"
    concurrency-hint="留空则保留报告当前并发"
    @confirm="onConfirmRetryModal"
    @cancel="onCancelRetryModal"
  >
    <template #summary>
      <a-descriptions v-if="data.retryRecord" :column="2" bordered size="small" class="mango-report-retry-summary">
        <a-descriptions-item label="报告 ID" :span="2">{{ data.retryRecord.id }}</a-descriptions-item>
        <a-descriptions-item label="用例总数">{{ reportResultCount(data.retryRecord, 'total') }}</a-descriptions-item>
        <a-descriptions-item label="失败用例">{{ reportResultCount(data.retryRecord, 'fail') }}</a-descriptions-item>
        <a-descriptions-item label="通过用例">{{ reportResultCount(data.retryRecord, 'success') }}</a-descriptions-item>
        <a-descriptions-item label="告警用例">{{ reportResultCount(data.retryRecord, 'warning') }}</a-descriptions-item>
      </a-descriptions>
      <p class="mango-report-retry-hint">全量重试使用下方配置；只重试失败保留原环境、并发及通过结果，含失败子用例的场景会整体重试。</p>
    </template>
    <template #footer="{ confirm }">
      <a-space class="mango-modal-dialog-footer-actions">
        <a-button v-permission="'report:retry'" :loading="data.retryLoading"
          :disabled="data.failedRetryLoadingId !== null" @click="confirm">全量重试</a-button>
        <a-button v-permission="'report:retry'" type="primary" :loading="data.failedRetryLoadingId !== null"
          :disabled="data.retryLoading || !data.retryRecord || isReportRunning(data.retryRecord) || reportResultCount(data.retryRecord, 'fail') === 0"
          @click="onRetryFailed(data.retryRecord)">只重试失败</a-button>
      </a-space>
    </template>
  </TestExecutionModal>
  <a-modal
    v-model:visible="data.noticeModalVisible"
    title="发送通知"
    :confirm-loading="data.noticeSending"
    @cancel="onCancelNoticeModal"
    @before-ok="onConfirmNoticeModal"
  >
    <a-form :model="noticeForm">
      <a-form-item label="项目/产品">
        <ProjectProductSelect v-model="noticeForm.project_product" disabled />
      </a-form-item>
      <a-form-item label="通知组" required>
        <a-select
          v-model="noticeForm.notice_group"
          :options="data.noticeList"
          :loading="data.noticeLoading"
          placeholder="请选择通知组"
          allow-clear
          allow-search
          value-key="key"
          data-testid="qa-views-report-select-请选择通知组"
        />
      </a-form-item>
    </a-form>
  </a-modal>
  <DiagnosticMarkdownDrawer
    v-model:visible="diagnosticDrawer.visible"
    target-type="test_report"
    :target-id="diagnosticDrawer.targetId"
    :document-available="diagnosticDrawer.documentAvailable"
    :title="diagnosticDrawer.title"
  />
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { conditionItems, tableColumns } from './config'
  import {
    getSystemTestSuite,
    postSystemTestSuiteSendNotice,
    postSystemTestSuiteStop,
  } from '@/api/system/test_suite'
  import {
    getSystemTestSuiteDetailsAllRetry,
    retryFailedReportCases,
    getSystemTestSuiteDetailsExecutionOptions,
    getSystemTestSuiteDetailsReport,
  } from '@/api/system/test_sute_details'
  import { getScheduledTaskGroupOptions, getSystemTasks } from '@/api/system/tasks'
  import { useEnum } from '@/store/modules/get-enum'
  import { Message, Modal } from '@arco-design/web-vue'
  import Title from '@/views/index/components/Title.vue'
  import StatusChart from '@/components/chart/StatusChart.vue'
  import ReportTrendChart from './components/ReportTrendChart.vue'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import TestExecutionModal from '@/components/overlays/TestExecutionModal.vue'
  import DiagnosticMarkdownDrawer from '@/components/reports/DiagnosticMarkdownDrawer.vue'
  import { formatProjectProductPath, formatModulePath, getEnumTagColor, getOptionId } from '@/utils/business-format'
  import { getUserName } from '@/api/user/user'
  import { getSystemNoticeName } from '@/api/system/notice_group'

  const enumStore = useEnum()

  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const table = useTable()
  const rowKey = useRowKey('id')
  const router = useRouter()
  const route = useRoute()
  const retryModalRef = ref<InstanceType<typeof TestExecutionModal> | null>(null)
  const sidebarResetKey = ref(0)
  const sidebarModuleIds = ref<Array<string | number>>([])
  const projectProductCondition = computed(() => getConditionItem('project_product'))
  const moduleCondition = computed(() => getConditionItem('module'))
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => !['project_product', 'module'].includes(item.key))
  )
  const selectedTaskGroupTitle = computed(() => {
    const item = getConditionItem('tasks__task_group_id')
    const selectedValues = Array.isArray(item?.value) ? item.value.map(String) : []
    return (item?.optionItems || [])
      .filter((option: any) => selectedValues.includes(String(option.value)))
      .map((option: any) => option.label)
      .join('，')
  })
  const data: any = reactive({
    statusCounts: {
      success: 0,
      fail: 0,
      warning: 0,
      pending: 0,
      todo: 0,
      stopped: 0,
    },
    trend: [],
    chartLoading: false,
    tasksLoading: false,
    taskGroupOptionsLoading: false,
    userLoading: false,
    noticeLoading: false,
    noticeSending: false,
    noticeSendingId: null,
    noticeModalVisible: false,
    noticeList: [],
    noticeRecord: null,
    retryLoading: false,
    retryRecord: null,
    failedRetryLoadingId: null,
    stopLoadingId: null,
    apiPlatformLimit: 1,
  })
  const diagnosticDrawer = reactive({
    visible: false,
    targetId: '' as number | string,
    documentAvailable: false,
    title: '测试报告排查结果',
  })
  const reportResultSummaryItems = [
    { key: 'success', label: '通过', tone: 'success' },
    { key: 'fail', label: '失败', tone: 'danger' },
    { key: 'warning', label: '警告', tone: 'warning' },
    { key: 'proceed', label: '进行中', tone: 'primary' },
    { key: 'stay_begin', label: '待开始', tone: 'muted' },
    { key: 'stopped', label: '已停止', tone: 'muted' },
  ] as const
  const noticeForm = reactive({
    project_product: '' as any,
    notice_group: '' as any,
  })
  const pollingTimer = ref<ReturnType<typeof setTimeout> | null>(null)
  let chartRequestSequence = 0
  let tableRequestSequence = 0

  function getConditionItem(key: string) {
    return conditionItems.find((item) => item.key === key)
  }

  function currentProjectProductId() {
    return getOptionId(getConditionItem('project_product')?.value)
  }

  function clearEmptyFilter(value: Record<string, any>, key: string) {
    if (value[key] === null || value[key] === '' || value[key] === undefined) {
      delete value[key]
    }
  }

  function loadTaskGroupOptions(projectProductId?: number | string | null) {
    data.taskGroupOptionsLoading = true
    return getScheduledTaskGroupOptions(
      projectProductId === '' || projectProductId === undefined ? null : Number(projectProductId),
    )
      .then((res) => {
        const item = getConditionItem('tasks__task_group_id')
        if (item) {
          item.optionItems = (Array.isArray(res.data) ? res.data : []).map((option: any) => ({
            value: option.key,
            label: option.title,
          }))
        }
      })
      .catch((error) => {
        const item = getConditionItem('tasks__task_group_id')
        if (item) item.optionItems = []
        console.log(error)
      })
      .finally(() => {
        data.taskGroupOptionsLoading = false
      })
  }

  function searchOptions(key: string) {
    const configuredOptions = getConditionItem(key)?.optionItems || []
    if (configuredOptions.length) {
      return configuredOptions.map((item) => ({ key: item.value, title: item.label }))
    }
    if (key === 'test_env') return enumStore.environment_type || []
    if (key === 'case_type') return enumStore.test_case_type || []
    if (key === 'execution_scene') return enumStore.automation_execution_scene || []
    if (key === 'execution_scope') return enumStore.automation_execution_scope || []
    return []
  }

  function optionTagColor(
    options: Array<{ key: string | number; title: string }> | null,
    value: string | number
  ) {
    return getEnumTagColor(options, value, enumStore.colors)
  }

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearTimeout(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function isActiveReport(record: any) {
    return Number(record?.status) === 2 || Number(record?.status) === 3
  }

  function scheduleActiveReportPolling(reportIds: Array<number | string>, requestSequence: number) {
    clearPollingTimer()
    if (!reportIds.length || requestSequence !== tableRequestSequence) return
    pollingTimer.value = setTimeout(() => {
      pollActiveReports(reportIds, requestSequence)
    }, 3000)
  }

  async function pollActiveReports(
    reportIds: Array<number | string>,
    requestSequence: number,
  ) {
    if (!reportIds.length || requestSequence !== tableRequestSequence) return
    try {
      const res = await getSystemTestSuite({
        id__in: reportIds.join(','),
        page: 1,
        pageSize: reportIds.length,
      })
      if (requestSequence !== tableRequestSequence) return
      const updatedRecords = Array.isArray(res.data) ? res.data : []
      const updatedById = new Map(
        updatedRecords.map((record: any) => [String(record.id), record]),
      )
      table.dataList.forEach((record: any, index: number) => {
        const updatedRecord = updatedById.get(String(record.id))
        if (updatedRecord) table.dataList.splice(index, 1, updatedRecord)
      })
      scheduleActiveReportPolling(
        updatedRecords.filter(isActiveReport).map((record: any) => record.id),
        requestSequence,
      )
    } catch (error) {
      console.log(error)
      scheduleActiveReportPolling(reportIds, requestSequence)
    }
  }

  function buildFilterValue() {
    const value = getFormItems(conditionItems)
    const groupExecutionId = Array.isArray(route.query.group_execution_id)
      ? route.query.group_execution_id[0]
      : route.query.group_execution_id
    if (groupExecutionId) value.group_execution_id = groupExecutionId
    const testSuiteIds = Array.isArray(route.query.test_suite_ids)
      ? route.query.test_suite_ids[0]
      : route.query.test_suite_ids
    if (testSuiteIds) value.id__in = testSuiteIds
    value['project_product'] = getOptionId(value['project_product'])
    value['module'] = getOptionId(value['module'])
    if (sidebarModuleIds.value.length) {
      value['module__in'] = sidebarModuleIds.value.join(',')
      delete value['module']
    }
    clearEmptyFilter(value, 'project_product')
    clearEmptyFilter(value, 'module')
    clearEmptyFilter(value, 'tasks_id')
    clearEmptyFilter(value, 'tasks__task_group_id__in')
    if (value.report_source === 'scheduled') {
      value['tasks__isnull'] = false
    } else if (value.report_source === 'non_scheduled') {
      value['tasks__isnull'] = true
    }
    delete value.report_source
    clearEmptyFilter(value, 'user')
    const dateRange = Array.isArray(value.date_range) ? value.date_range : []
    if (dateRange.length === 2) {
      value['create_time__gte'] = `${dateRange[0]} 00:00:00`
      value['create_time__lte'] = `${dateRange[1]} 23:59:59`
    }
    delete value.date_range
    clearEmptyFilter(value, 'test_env')
    clearEmptyFilter(value, 'execution_scene')
    clearEmptyFilter(value, 'execution_scope')
    return value
  }

  function applyRouteFilters() {
    ;[
      'project_product',
      'module',
      'status',
      'tasks_id',
      'tasks__task_group_id',
      'report_source',
      'test_env',
      'execution_scene',
      'execution_scope',
    ].forEach((key) => {
      const value = route.query[key]
      const item = getConditionItem(key)
      if (item && value !== undefined) {
        const routeValues = Array.isArray(value) ? value : String(value).split(',')
        item.value = item.multiple ? routeValues : routeValues[0]
      }
    })
    const startDate = Array.isArray(route.query.start_date)
      ? route.query.start_date[0]
      : route.query.start_date
    const endDate = Array.isArray(route.query.end_date) ? route.query.end_date[0] : route.query.end_date
    if (startDate && endDate) {
      const dateItem = getConditionItem('date_range')
      if (dateItem) dateItem.value = [startDate, endDate]
    }
  }
  applyRouteFilters()

  function loadReportOverview(filters: Record<string, any>) {
    const requestSequence = ++chartRequestSequence
    data.chartLoading = true
    getSystemTestSuiteDetailsReport(filters)
      .then((res) => {
        if (requestSequence !== chartRequestSequence) return
        const statusDistribution = Array.isArray(res.data?.status_distribution)
          ? res.data.status_distribution
          : [
              { status: 1, value: res.data?.successSun || 0 },
              { status: 0, value: res.data?.failSun || 0 },
            ]
        const statusMap: Record<number, number> = Object.fromEntries(
          statusDistribution.map((item: any) => [
            Number(item.status),
            Number(item.value || 0),
          ])
        )
        data.statusCounts = {
          success: statusMap[1] || 0,
          fail: statusMap[0] || 0,
          warning: statusMap[4] || 0,
          pending: statusMap[3] || 0,
          todo: statusMap[2] || 0,
          stopped: statusMap[5] || 0,
        }
        data.trend = normalizeReportTrend(res.data)
      })
      .catch(console.log)
      .finally(() => {
        if (requestSequence === chartRequestSequence) data.chartLoading = false
      })
  }

  function normalizeReportTrend(payload: any) {
    if (Array.isArray(payload?.trend)) return payload.trend
    const success = Array.isArray(payload?.success) ? payload.success : []
    const fail = Array.isArray(payload?.fail) ? payload.fail : []
    const length = Math.max(success.length, fail.length, 12)
    const today = new Date()
    const monday = new Date(today)
    const day = monday.getDay() || 7
    monday.setDate(monday.getDate() - day + 1)
    return Array.from({ length }, (_, index) => {
      const weekStart = new Date(monday)
      weekStart.setDate(monday.getDate() - (length - 1 - index) * 7)
      const weekEnd = new Date(weekStart)
      weekEnd.setDate(weekStart.getDate() + 6)
      const successCount = Number(success[index] || 0)
      const failCount = Number(fail[index] || 0)
      const completed = successCount + failCount
      const dateLabel = (value: Date) =>
        `${String(value.getMonth() + 1).padStart(2, '0')}/${String(value.getDate()).padStart(2, '0')}`
      return {
        label: `${dateLabel(weekStart)}-${dateLabel(weekEnd)}`,
        batch_count: 0,
        scheduled_count: 0,
        other_count: completed,
        success_count: successCount,
        fail_count: failCount,
        warning_count: 0,
        pass_rate: completed ? Number(((successCount / completed) * 100).toFixed(2)) : null,
      }
    })
  }

  function doRefresh(refreshCharts: unknown = true) {
    clearPollingTimer()
    const requestSequence = ++tableRequestSequence
    const filters = buildFilterValue()
    if (refreshCharts !== false) loadReportOverview(filters)
    const tableFilters = {
      ...filters,
      page: pagination.page,
      pageSize: pagination.pageSize,
    }
    getSystemTestSuite(tableFilters)
      .then((res) => {
        if (requestSequence !== tableRequestSequence) return
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        const records = Array.isArray(res.data) ? res.data : []
        scheduleActiveReportPolling(
          records.filter(isActiveReport).map((record: any) => record.id),
          requestSequence,
        )
      })
      .catch(console.log)
  }

  function loadTaskOptions(projectProductId?: number | string | null) {
    data.tasksLoading = true
    const params: Record<string, any> = {}
    if (projectProductId !== null && projectProductId !== '' && projectProductId !== undefined) {
      params.project_product = projectProductId
    }
    return getSystemTasks(params)
      .then((res) => {
        const taskItem = getConditionItem('tasks_id')
        if (taskItem) {
          taskItem.optionItems = (Array.isArray(res.data) ? res.data : []).map((item: any) => ({
            label: item.name || String(item.id),
            value: item.id,
          }))
        }
      })
      .catch(console.log)
      .finally(() => {
        data.tasksLoading = false
      })
  }

  function loadUserOptions() {
    data.userLoading = true
    return getUserName()
      .then((res) => {
        const userItem = getConditionItem('user')
        if (userItem) {
          userItem.optionItems = (Array.isArray(res.data) ? res.data : []).map((item: any) => ({
            label: item.title || item.name || String(item.key || item.id),
            value: item.key ?? item.id,
          }))
        }
      })
      .catch(console.log)
      .finally(() => {
        data.userLoading = false
      })
  }

  function onNavigationFilterChange({
    projectProduct,
    module,
    moduleIds,
  }: {
    projectProduct: any
    module: any
    moduleIds?: Array<string | number>
  }) {
    const previousProjectProduct = currentProjectProductId()
    const projectProductItem = getConditionItem('project_product')
    const moduleItem = getConditionItem('module')
    const taskItem = getConditionItem('tasks_id')
    const taskGroupItem = getConditionItem('tasks__task_group_id')
    if (projectProductItem) {
      projectProductItem.value = projectProduct ?? ''
    }
    if (moduleItem) {
      moduleItem.value = module ?? ''
    }
    sidebarModuleIds.value = moduleIds || []
    const projectProductChanged =
      String(previousProjectProduct ?? '') !== String(projectProduct ?? '')
    if (projectProductChanged && taskItem) {
      taskItem.value = ''
    }
    if (projectProductChanged) {
      if (taskGroupItem) taskGroupItem.value = []
      Promise.all([
        loadTaskOptions(currentProjectProductId()),
        loadTaskGroupOptions(currentProjectProductId()),
      ]).finally(() => doRefresh())
      return
    }
    pagination.page = 1
    doRefresh()
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.type === 'date-range' || it.multiple ? [] : ''
    })
    sidebarModuleIds.value = []
    sidebarResetKey.value += 1
    Promise.all([loadTaskOptions(), loadTaskGroupOptions()]).finally(() => {
      doRefresh()
    })
  }

  function optionTitle(options: any[] | null, key: string | number) {
    return options?.find((item) => item.key === key)?.title || '未分类'
  }

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/report/system/details',
      query: {
        id: record.id,
      },
    })
  }

  function reportExecutionName(record: any) {
    return record?.tasks?.name || record?.execution_name || `测试报告 #${record?.id || '-'}`
  }

  function reportResultCount(record: any, key: string) {
    return Math.max(Number(record?.execution_summary?.[key] || 0), 0)
  }

  function openReportDiagnostic(record: any) {
    diagnosticDrawer.targetId = record.id
    diagnosticDrawer.documentAvailable = Boolean(record.diagnostic_file_path)
    diagnosticDrawer.title = `${reportExecutionName(record)} · 排查结果`
    diagnosticDrawer.visible = true
  }

  function isReportRunning(record: any) {
    return record?.status === 2 || record?.status === 3
  }

  function onStop(record: any) {
    Modal.confirm({
      title: '立即停止测试报告',
      content:
        '停止后，该报告中所有待开始和正在执行的任务都会终止，已经完成的结果会保留。确定继续吗？',
      cancelText: '取消',
      okText: '立即停止',
      okButtonProps: { status: 'danger' },
      onBeforeOk: async () => {
        data.stopLoadingId = record.id
        try {
          const res = await postSystemTestSuiteStop(record.id)
          Message.success(res.msg)
          doRefresh()
          return true
        } catch (error: any) {
          Message.error(error?.msg || '停止测试报告失败')
          return false
        } finally {
          data.stopLoadingId = null
        }
      },
    })
  }

  async function onRetryFailed(record: any) {
    if (!record || data.retryLoading || data.failedRetryLoadingId !== null || isReportRunning(record) || reportResultCount(record, 'fail') === 0) return false
    data.failedRetryLoadingId = record.id
    try {
      const response = await retryFailedReportCases(record.id)
      const count = Number(response.data?.retry_count || 0)
      if (count) Message.success(`已提交 ${count} 个失败执行项重试`)
      else Message.info('这份报告当前没有失败执行项')
      retryModalRef.value?.close()
      data.retryRecord = null
      doRefresh()
      return true
    } catch (error: any) {
      Message.error(error?.msg || '重试失败项失败')
      return false
    } finally {
      data.failedRetryLoadingId = null
    }
  }

  async function onRetry(record: any) {
    if (data.retryLoading || data.failedRetryLoadingId !== null) return
    data.retryRecord = record
    data.retryLoading = true
    try {
      const res = await getSystemTestSuiteDetailsExecutionOptions()
      data.apiPlatformLimit = Number(res.data?.api_platform_limit || 1)
      retryModalRef.value?.show({
        executionName: reportExecutionName(record),
        testEnv: Number(record.test_env),
        apiConcurrencyLimit:
          record.api_concurrency_limit === null || record.api_concurrency_limit === undefined
            ? null
            : Number(record.api_concurrency_limit),
      })
    } catch (error: any) {
      data.retryRecord = null
      Message.error(error?.msg || '获取平台并发配置失败')
    } finally {
      data.retryLoading = false
    }
  }

  function onCancelRetryModal() {
    data.retryRecord = null
  }

  async function onConfirmRetryModal(config: {
    executionName: string
    testEnv: number
    apiConcurrencyLimit: number | null
  }) {
    if (!data.retryRecord || data.retryLoading || data.failedRetryLoadingId !== null) return false
    data.retryLoading = true
    try {
      const res = await getSystemTestSuiteDetailsAllRetry(
        data.retryRecord.id,
        config.testEnv,
        config.apiConcurrencyLimit
      )
      Message.success(res.msg)
      retryModalRef.value?.close()
      data.retryRecord = null
      doRefresh()
      return true
    } catch (error: any) {
      Message.error(error?.msg || '重试失败')
      return false
    } finally {
      data.retryLoading = false
      retryModalRef.value?.setConfirmLoading(false)
    }
  }

  function reportProjectProductId(record: any) {
    return record?.project_product?.id || record?.project_product
  }

  function buildProjectProductValue(record: any) {
    const product = record?.project_product
    if (!product) return ''
    if (product.project?.id && product.id) return [product.project.id, product.id]
    return product.id || ''
  }

  function hasTaskNotice(record: any) {
    return Boolean(record?.tasks?.name && record?.tasks?.notice_group)
  }

  async function sendNotice(record: any, noticeGroup?: number | string) {
    data.noticeSending = true
    data.noticeSendingId = record.id
    try {
      const payload: Record<string, any> = { id: record.id }
      if (noticeGroup) payload.notice_group = noticeGroup
      const res = await postSystemTestSuiteSendNotice(payload)
      Message.success(res.msg)
      data.noticeModalVisible = false
      doRefresh()
      return true
    } catch (error: any) {
      Message.error(error?.msg || '发送通知失败')
      return false
    } finally {
      data.noticeSending = false
      data.noticeSendingId = null
    }
  }

  function confirmSendNotice(record: any, noticeGroup?: number | string) {
    return new Promise<boolean>((resolve) => {
      Modal.confirm({
        title: '确认发送通知',
        content: '确定要发送这份测试报告的通知吗？',
        cancelText: '取消',
        okText: '发送',
        onBeforeOk: () => {
          return sendNotice(record, noticeGroup).then((success) => {
            resolve(success)
            return success
          })
        },
        onCancel: () => {
          resolve(false)
        },
      })
    })
  }

  function onSendNotice(record: any) {
    if (hasTaskNotice(record)) {
      confirmSendNotice(record)
      return
    }
    data.noticeRecord = record
    noticeForm.project_product = buildProjectProductValue(record)
    noticeForm.notice_group = ''
    data.noticeModalVisible = true
    loadNoticeOptions(reportProjectProductId(record))
  }

  function loadNoticeOptions(projectProductId?: number | string | null) {
    if (!projectProductId) {
      data.noticeList = []
      return Promise.resolve()
    }
    data.noticeLoading = true
    return getSystemNoticeName(Number(projectProductId))
      .then((res) => {
        data.noticeList = Array.isArray(res.data) ? res.data : []
      })
      .catch(console.log)
      .finally(() => {
        data.noticeLoading = false
      })
  }

  function onCancelNoticeModal() {
    data.noticeModalVisible = false
    data.noticeRecord = null
    noticeForm.project_product = ''
    noticeForm.notice_group = ''
    data.noticeList = []
  }

  async function onConfirmNoticeModal() {
    if (!noticeForm.notice_group) {
      Message.error('请选择通知组')
      return false
    }
    if (!data.noticeRecord) return false
    return confirmSendNotice(data.noticeRecord, noticeForm.notice_group)
  }

  onMounted(() => {
    nextTick(async () => {
      await Promise.all([
        enumStore.getEnum(),
        loadTaskOptions(currentProjectProductId()),
        loadTaskGroupOptions(currentProjectProductId()),
        loadUserOptions(),
      ])
      doRefresh()
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>

<style lang="less" scoped>
  .mango-report-retry-summary {
    margin-bottom: var(--m-space-sm);
  }
  .mango-report-retry-hint {
    margin: 0 0 var(--m-space-md);
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-report-workbench :deep(.mango-report-task-group-filter .arco-select-view-inner) {
    display: flex;
    min-width: 0;
    flex-wrap: nowrap;
    align-items: center;
  }

  .mango-report-workbench :deep(.mango-report-task-group-filter .arco-select-view-tag) {
    max-width: 120px;
    overflow: hidden;
    white-space: nowrap;
    word-break: normal;
  }

  .report-chart-grid {
    display: grid;
    height: 280px;
    margin-bottom: var(--m-page-gap);
    grid-template-columns: minmax(360px, 0.8fr) minmax(520px, 1.2fr);
    gap: var(--m-page-gap);
  }

  .report-chart-scroll {
    --mango-workbench-min-width: 892px;
    flex: none;
    height: auto;
    margin-bottom: var(--m-page-gap);
    padding: var(--m-page-gap);
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .report-chart-scroll > .report-chart-grid {
    min-width: var(--mango-workbench-min-width);
    margin-bottom: 0;
  }

  .report-chart-card {
    display: flex;
    box-sizing: border-box;
    height: 280px;
    margin-top: 0;
    min-height: 0;
    overflow: hidden;
    border: 1px solid var(--m-border-strong);
    flex-direction: column;
  }

  .report-table-region {
    min-height: 0;
  }

  .report-id-cell {
    display: inline-block;
    width: 150px;
  }

  .mango-report-result-summary {
    display: inline-flex;
    min-width: 0;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }

  .mango-report-result-summary__item {
    display: inline-flex;
    min-width: 0;
    align-items: baseline;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;

    strong {
      margin-left: 1px;
      font-weight: 600;
    }

    &--success strong { color: var(--m-success); }
    &--danger strong { color: var(--m-danger); }
    &--warning strong { color: var(--m-warning); }
    &--primary strong { color: var(--m-primary); }
    &--muted strong,
    &--zero strong { color: var(--m-muted); }
  }

  .status-card :deep(.mango-status-chart),
  .trend-card :deep(.mango-report-source-trend) {
    flex: 1;
    width: 100%;
    height: auto;
    min-height: 0;
  }

  @media (max-width: 1px) {
    .report-chart-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
