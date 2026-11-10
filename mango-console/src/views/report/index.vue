<template>
  <TableBody
    ref="tableBody"
    plain
    class="mango-detail-workbench-page"
    :sticky-horizontal-scroll="false"
  >
    <template #header>
      <TableHeader title="执行报告">
        <template #header-extra>
          <a-button v-if="groupExportId !== null" size="small" @click="openOfflineExport('group', groupExportId)">导出任务组 HTML</a-button>
        </template>
      </TableHeader>
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
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form layout="inline" :model="{}" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="onSearchRefresh" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="enumStore.task_status"
                  @change="onSearchRefresh"
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
                  :loading="item.key === 'tasks_id' ? searchLoading.tasks : searchLoading.groups"
                  :class="{ 'mango-report-task-group-filter': item.key === 'tasks__task_group_id' }"
                  :title="item.key === 'tasks__task_group_id' ? selectedTaskGroupTitle : undefined"
                  @change="onSearchRefresh"
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
                  :loading="searchLoading.users"
                  @change="onSearchRefresh"
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
                  @change="onSearchRefresh"
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
                  @change="onSearchRefresh"
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
                :success="charts.counts.success"
                :fail="charts.counts.fail"
                :warning="charts.counts.warning"
                :pending="charts.counts.pending"
                :todo="charts.counts.todo"
                :stopped="charts.counts.stopped"
                :loading="charts.loading"
                total-label="报告总数"
              />
            </section>

            <section class="report-chart-card trend-card mango-section-card">
              <Title title="近 12 周执行报告趋势" />
              <ReportTrendChart
                :items="charts.trend"
                :loading="charts.loading"
              />
            </section>
          </div>
        </div>
        
        <StickyHorizontalTable :scroll-x="2180" content-class="report-table-region">
          <a-table
            :bordered="false"
            :loading="listLoading"
            :data="rows"
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
                  <a-tooltip :content="reportResultSummaryText(record)">
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
                  </a-tooltip>
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
    {
        label: '重试',
        hidden: record.automation_types?.includes(4),
        priority: 0,
        loading: retryState.loading && retryState.record?.id === record.id,
        onClick: () => onRetry(record), },
    {
        label: '立即停止',
        priority: 3,
        danger: true,
        hidden: !isReportRunning(record) || record.automation_types?.includes(4),
        loading: stopLoadingId === record.id,
        onClick: () => onStop(record), },
    { label: '明细', priority: 1, onClick: () => onClick(record) },
    { label: '导出离线 HTML', priority: 4, hidden: isReportRunning(record), onClick: () => openOfflineExport('suite', record.id) },
    {
        label: '排查结果',
        priority: 2,
        onClick: () => openReportDiagnostic(record), },
    {
        label: '重发通知',
        priority: 3,
        loading: noticeState.sendingId === record.id,
        onClick: () => onSendNotice(record), },
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
    :platform-limit="retryState.platformLimit"
    concurrency-placeholder="留空则保留报告当前并发"
    concurrency-hint="留空则保留报告当前并发"
    @confirm="onConfirmRetryModal"
    @cancel="onCancelRetryModal"
  >
    <template #summary>
      <a-descriptions v-if="retryState.record" :column="2" bordered size="small" class="mango-report-retry-summary">
        <a-descriptions-item label="报告 ID" :span="2">{{ retryState.record.id }}</a-descriptions-item>
        <a-descriptions-item label="用例总数">{{ reportResultCount(retryState.record, 'total') }}</a-descriptions-item>
        <a-descriptions-item label="失败用例">{{ reportResultCount(retryState.record, 'fail') }}</a-descriptions-item>
        <a-descriptions-item label="通过用例">{{ reportResultCount(retryState.record, 'success') }}</a-descriptions-item>
        <a-descriptions-item label="告警用例">{{ reportResultCount(retryState.record, 'warning') }}</a-descriptions-item>
      </a-descriptions>
      <p class="mango-report-retry-hint">全量重试使用下方配置；只重试失败保留原环境、并发及通过结果，含失败子用例的场景会整体重试。</p>
    </template>
    <template #footer="{ confirm }">
      <a-space class="mango-modal-dialog-footer-actions">
        <a-button  :loading="retryState.loading"
          :disabled="retryState.failedId !== null" @click="confirm">全量重试</a-button>
        <a-button  type="primary" :loading="retryState.failedId !== null"
          :disabled="retryState.loading || !retryState.record || isReportRunning(retryState.record) || reportResultCount(retryState.record, 'fail') === 0"
          @click="onRetryFailed(retryState.record)">只重试失败</a-button>
      </a-space>
    </template>
  </TestExecutionModal>
  <a-modal :width="560" modal-class="mango-simple-form-modal"
    v-model:visible="noticeState.visible"
    title="发送通知"
    :ok-loading="noticeState.sending"
    @cancel="onCancelNoticeModal"
    @before-ok="onConfirmNoticeModal"
  >
    <a-form auto-label-width layout="horizontal" class="mango-simple-form" :model="noticeForm">
      <a-form-item class="mango-simple-form-item" label="项目/产品">
        <ProjectProductSelect v-model="noticeForm.project_product" disabled />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="通知组" required>
        <a-select
          v-model="noticeForm.notice_group"
          :options="noticeState.options"
          :loading="noticeState.loading"
          :disabled="noticeState.sending"
          placeholder="请选择通知组"
          allow-clear
          allow-search
          value-key="key"
          data-testid="qa-views-report-select-请选择通知组"
        />
        <template v-if="noticeState.error" #extra>
          {{ noticeState.error }} <a-button size="small" :loading="noticeState.loading" @click="loadNoticeOptions(noticeState.record?.project_product?.id ?? null)">重试</a-button>
        </template>
      </a-form-item>
    </a-form>
  </a-modal>
  <OfflineReportExportDialog v-model:visible="offlineExport.visible" :source-kind="offlineExport.kind" :source-id="offlineExport.id" />
  <DiagnosticMarkdownDrawer
    v-model:visible="diagnosticDrawer.visible"
    target-type="test_report"
    :target-id="diagnosticDrawer.targetId"
    :document-available="diagnosticDrawer.documentAvailable"
    :title="diagnosticDrawer.title"
  />
</template>

<script lang="ts" setup>
import { runLoadRequest } from '@/utils/load-error'

  import { usePagePolling, isPendingExecution, type PollingContext } from '@/hooks/use-page-polling'
  import { useRowKey } from '@/hooks/table'
  import { computed, onMounted, onBeforeUnmount, onActivated, onDeactivated, reactive, ref, toRef, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { usePageData } from '@/store/page-data'
  import { createConditionItems, tableColumns } from './config'
  import { applyReportRouteFilters, buildReportFilters, resetReportConditions } from './filters'
  import type { ReportFilters } from './filters'
  import { createReportQuery } from './report-query'
  import { createReportCounts, parseReportList, parseReportOptions, parseReportOverview, parseReportRow, reportEnvelope, reportObject, reportText, reportId, reportNumber, type ReportId, type ReportRow, type ReportOption, type ReportSummaryKey, type ReportTrendItem } from './report-list'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
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
  import OfflineReportExportDialog from '@/components/reports/OfflineReportExportDialog.vue'
  import type { ReportSource } from '@/api/system/offline_report'
  import { formatProjectProductPath, formatModulePath, getEnumTagColor, getOptionId } from '@/utils/business-format'
  import { getUserName } from '@/api/user/user'
  import { getSystemNoticeName } from '@/api/system/notice_group'

  const enumStore = useEnum()
  const conditionItems = reactive(createConditionItems())

  const listLoading = ref(false), listError = ref(''), rows = ref<ReportRow[]>([])
  const pagination = reactive({ page: 1, pageSize: 20, pageCount: 0, showSizePicker: true, pageSizes: [10, 20, 50, 100],
    onChange: () => doRefresh(), setTotalSize: (total: number) => { pagination.pageCount = total } })
  const rowKey = useRowKey('id')
  const router = useRouter()
  const route = useRoute()
  const userStore = useUserStore(), permissionStore = usePermissionStore(), pagePath = route.path
  let mounted = false, active = true, disposed = false, needsLoad = true
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const identityKey = () => JSON.stringify([route.path, route.fullPath, userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment, permissionStore.permissionKeys])
  const listQuery = createReportQuery(available, () => JSON.stringify([identityKey(), buildFilterValue(), pagination.page, pagination.pageSize]))
  const chartQuery = createReportQuery(available, () => JSON.stringify([identityKey(), buildFilterValue()]))
  const taskQuery = createReportQuery(available, () => JSON.stringify([identityKey(), currentProjectProductId()]))
  const groupQuery = createReportQuery(available, () => JSON.stringify([identityKey(), currentProjectProductId()]))
  const userQuery = createReportQuery(available, identityKey)
  const offlineExport = reactive<{ visible: boolean; kind: ReportSource; id: string | number }>({ visible: false, kind: 'suite', id: '' })
  const groupExportId = computed(() => reportId(Array.isArray(route.query.group_execution_id) ? route.query.group_execution_id[0] : route.query.group_execution_id))
  function openOfflineExport(kind: ReportSource, id: unknown) {
    const target = reportId(id)
    if (available() && target !== null) Object.assign(offlineExport, { visible: true, kind, id: target })
  }
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
    const value = item?.value
    const selectedValues = Array.isArray(value) ? value.map(String) : []
    return (item?.optionItems || [])
      .filter((option) => selectedValues.includes(String(option.value)))
      .map((option) => option.label)
      .join('，')
  })
  const charts = reactive<{ counts: ReturnType<typeof createReportCounts>; trend: ReportTrendItem[]; loading: boolean; error: string }>({ counts: createReportCounts(), trend: [], loading: false, error: '' })
  const searchLoading = reactive({ tasks: false, groups: false, users: false })
  const searchErrors = reactive({ tasks: '', groups: '', users: '' })
  const noticeState = reactive<{ loading: boolean; error: string; sending: boolean; sendingId: ReportId | null; visible: boolean; options: ReportOption[]; record: ReportRow | null }>({ loading: false, error: '', sending: false, sendingId: null, visible: false, options: [], record: null })
  const retryState = reactive<{ loading: boolean; record: ReportRow | null; failedId: ReportId | null; platformLimit: number }>({ loading: false, record: null, failedId: null, platformLimit: 1 })
  const stopLoadingId = ref<ReportId | null>(null)
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
  const noticeForm = reactive<{ project_product: ReportId | ReportId[] | null; notice_group: ReportId | null }>({ project_product: null, notice_group: null })
  const activeReportIds = computed(() => rows.value.filter(isPendingExecution).map(record => record.id))
  const pagePolling = usePagePolling(
    context => pollActiveReports(context),
    () => {
      invalidateReads()
    },
  )

  function getConditionItem(key: string) {
    return conditionItems.find((item) => item.key === key)
  }

  function currentProjectProductId() {
    return reportId(getOptionId(getConditionItem('project_product')?.value))
  }

  function searchOptions(key: string) {
    const configuredOptions = getConditionItem(key)?.optionItems || []
    if (configuredOptions.length) return configuredOptions.map(item => ({ key: item.value, title: item.label }))
    if (key === 'test_env') return enumStore.environment_type || []
    if (key === 'case_type') return enumStore.test_case_type || []
    if (key === 'execution_scene') return enumStore.automation_execution_scene || []
    if (key === 'execution_scope') return enumStore.automation_execution_scope || []
    return []
  }
  function optionTagColor(options: Array<{ key: string | number; title: string }> | null, value: string | number) {
    return getEnumTagColor(options, value, enumStore.colors)
  }
  function buildFilterValue() { return buildReportFilters(conditionItems, sidebarModuleIds.value, route.query) }
  function applyRouteFilters() { applyReportRouteFilters(conditionItems, route.query) }
  applyRouteFilters()

  const enumLoading = ref(false), enumError = ref('')
  const enumQuery = createReportQuery(available, identityKey)
  let initialized = false
  function ensureEnums() {
    if (initialized) return Promise.resolve(true)
    return enumQuery.run({ key: 'enums', loading: enumLoading, error: enumError, message: '搜索选项加载失败，请重试',
      read: async () => { await enumStore.getEnum() }, apply: () => { initialized = true } })
  }
  function invalidateReads() {
    for (const query of [listQuery, chartQuery, taskQuery, groupQuery, userQuery, enumQuery]) query.invalidate()
    needsLoad = true
  }
  function loadReportOverview(filters: ReportFilters, silent = false) {
    const snapshot = { ...filters }
    return chartQuery.run({ key: JSON.stringify(snapshot), silent, loading: toRef(charts, 'loading'), error: toRef(charts, 'error'),
      message: '报告统计加载失败，请重试', read: async () => parseReportOverview(await runLoadRequest(silent, () => getSystemTestSuiteDetailsReport(snapshot))),
      apply: value => { charts.counts = value.counts; charts.trend = value.trend },
      fail: () => { charts.counts = createReportCounts(); charts.trend = [] },
    })
  }
  function readReportList(filters: ReportFilters, silent = false) {
    const params = { ...filters, page: pagination.page, pageSize: pagination.pageSize }
    return listQuery.run({ key: JSON.stringify(params), silent, loading: listLoading, error: listError,
      message: '执行报告加载失败，请重试', read: async () => parseReportList(await runLoadRequest(silent, () => getSystemTestSuite(params))),
      apply: value => {
        rows.value = value.rows
        pagination.setTotalSize(value.total)
        if (activeReportIds.value.length) pagePolling.start()
        else pagePolling.stop()
      }, fail: () => { rows.value = []; pagination.setTotalSize(0) },
    }).then(ok => {
      if (!ok && available() && listError.value) pagePolling.start()
      return ok
    })
  }
  async function doRefresh(refreshCharts: unknown = true) {
    if (!available()) return
    if (!await ensureEnums() || !available()) return
    const filters = buildFilterValue()
    await Promise.all([readReportList(filters), refreshCharts === false ? Promise.resolve() : loadReportOverview(filters)])
  }
  async function pollActiveReports(context: PollingContext) {
    if (!available() || !context.isCurrent()) return
    const filters = buildFilterValue()
    await Promise.all([readReportList(filters, true), loadReportOverview(filters, true)])
  }
  function onSearchRefresh() {
    pagination.page = 1
    return doRefresh()
  }
  function loadTaskOptions(projectProductId: ReportId | null = currentProjectProductId()) {
    const params = projectProductId === null ? {} : { project_product: projectProductId }
    return taskQuery.run({ key: JSON.stringify(params), loading: toRef(searchLoading, 'tasks'), error: toRef(searchErrors, 'tasks'),
      message: '定时任务加载失败，请重试', read: async () => parseReportOptions(await getSystemTasks(params)),
      apply: options => { const item = getConditionItem('tasks_id'); if (item) item.optionItems = options },
      fail: () => { const item = getConditionItem('tasks_id'); if (item) item.optionItems = [] },
    })
  }
  function loadTaskGroupOptions(projectProductId: ReportId | null = currentProjectProductId()) {
    return groupQuery.run({ key: JSON.stringify(projectProductId), loading: toRef(searchLoading, 'groups'), error: toRef(searchErrors, 'groups'),
      message: '任务组加载失败，请重试', read: async () => parseReportOptions(await getScheduledTaskGroupOptions(projectProductId)),
      apply: options => { const item = getConditionItem('tasks__task_group_id'); if (item) item.optionItems = options },
      fail: () => { const item = getConditionItem('tasks__task_group_id'); if (item) item.optionItems = [] },
    })
  }
  function loadUserOptions() {
    return userQuery.run({ key: 'users', loading: toRef(searchLoading, 'users'), error: toRef(searchErrors, 'users'),
      message: '执行人加载失败，请重试', read: async () => parseReportOptions(await getUserName()),
      apply: options => { const item = getConditionItem('user'); if (item) item.optionItems = options },
      fail: () => { const item = getConditionItem('user'); if (item) item.optionItems = [] },
    })
  }
  function onNavigationFilterChange({ projectProduct, module, moduleIds }: {
    projectProduct: ReportId | null; module: ReportId | null; moduleIds?: ReportId[]
  }) {
    const previous = currentProjectProductId(), product = reportId(projectProduct), selectedModule = reportId(module)
    const productItem = getConditionItem('project_product'), moduleItem = getConditionItem('module')
    if (productItem) productItem.value = product ?? ''
    if (moduleItem) moduleItem.value = selectedModule ?? ''
    sidebarModuleIds.value = (moduleIds || []).map(reportId).filter((id): id is ReportId => id !== null)
    pagination.page = 1
    if (String(previous ?? '') !== String(product ?? '')) {
      taskQuery.invalidate(); groupQuery.invalidate()
      const task = getConditionItem('tasks_id'), group = getConditionItem('tasks__task_group_id')
      if (task) { task.value = ''; task.optionItems = [] }
      if (group) { group.value = []; group.optionItems = [] }
      void loadTaskOptions(); void loadTaskGroupOptions()
    }
    return doRefresh()
  }
  function onResetSearch() {
    resetReportConditions(conditionItems)
    pagination.page = 1
    sidebarModuleIds.value = []
    sidebarResetKey.value++
    taskQuery.invalidate(); groupQuery.invalidate()
    for (const key of ['tasks_id', 'tasks__task_group_id']) { const item = getConditionItem(key); if (item) item.optionItems = [] }
    void loadTaskOptions(null); void loadTaskGroupOptions(null)
    return doRefresh()
  }

  function optionTitle(options: Array<{ key: ReportId; title: string }> | null, key: ReportId | null) {
    return options?.find(item => String(item.key) === String(key))?.title || '未分类'
  }
  function onClick(record: ReportRow) {
    const snapshot = parseReportRow(record)
    if (!available() || !snapshot) return
    usePageData().setRecord(snapshot)
    void router.push({ path: '/report/system/details', query: { id: snapshot.id } })
  }
  function reportExecutionName(record: ReportRow) { return record.tasks?.name || record.execution_name || `测试报告 #${record.id}` }
  function reportResultCount(record: ReportRow, key: ReportSummaryKey) { return record.execution_summary[key] }
  function reportResultSummaryText(record: ReportRow) {
    return reportResultSummaryItems.map(item => `${item.label} ${reportResultCount(record, item.key)}`).join('；')
  }
  function openReportDiagnostic(record: ReportRow) {
    if (!available() || reportId(record.id) === null) return
    Object.assign(diagnosticDrawer, { targetId: record.id, documentAvailable: Boolean(record.diagnostic_file_path), title: `${reportExecutionName(record)} · 排查结果`, visible: true })
  }
  function isReportRunning(record: ReportRow) { return isPendingExecution(record) }
  let actionVersion = 0, retryGeneration = 0, noticeGeneration = 0
  let stopConfirmation: ReturnType<typeof Modal.confirm> | null = null
  let noticeConfirmation: ReturnType<typeof Modal.confirm> | null = null
  let settleNotice: ((value: boolean) => void) | null = null
  const noticeQuery = createReportQuery(available, () => JSON.stringify([identityKey(), noticeState.visible, noticeState.record?.id, noticeGeneration]))
  function actionCurrent(version: number, key: string) { return available() && version === actionVersion && key === identityKey() }
  function closeNoticeConfirmation() {
    const confirmation = noticeConfirmation
    noticeConfirmation = null
    settleNotice?.(false); settleNotice = null
    confirmation?.close()
  }
  function closeActionWindows() {
    actionVersion++
    onCancelRetryModal(); retryModalRef.value?.close()
    onCancelNoticeModal()
    const confirmation = stopConfirmation; stopConfirmation = null; confirmation?.close()
    diagnosticDrawer.visible = false; diagnosticDrawer.targetId = ''; offlineExport.visible = false; offlineExport.id = ''
  }
  function onStop(record: ReportRow) {
    const snapshot = parseReportRow(record)
    if (!available() || !snapshot || !isReportRunning(snapshot) || snapshot.automation_types.includes(4) || stopLoadingId.value !== null || stopConfirmation) return
    const version = actionVersion, key = identityKey()
    const current = () => actionCurrent(version, key) && stopConfirmation === confirmation
    const confirmation = Modal.confirm({
      title: '立即停止测试报告', content: '停止后，该报告中所有待开始和正在执行的任务都会终止，已经完成的结果会保留。确定继续吗？',
      cancelText: '取消', okText: '立即停止', okButtonProps: { status: 'danger' },
      onCancel: () => { if (stopConfirmation === confirmation) stopConfirmation = null },
      onBeforeOk: async () => {
        if (!current() || stopLoadingId.value !== null) return false
        stopLoadingId.value = snapshot.id
        try {
          const response = reportEnvelope(await postSystemTestSuiteStop(snapshot.id))
          if (!current()) return false
          Message.success(reportText(response.msg) || '已提交停止')
          stopConfirmation = null; void doRefresh()
          return true
        } catch (error: unknown) {
          if (current()) Message.error(reportText(reportObject(error).msg) || '停止测试报告失败')
          return false
        } finally { stopLoadingId.value = null }
      },
    })
    stopConfirmation = confirmation
  }
  async function onRetry(record: ReportRow) {
    const snapshot = parseReportRow(record)
    if (!available() || !snapshot || snapshot.automation_types.includes(4) || retryState.loading || retryState.failedId !== null) return
    retryState.record = snapshot; retryState.loading = true
    const generation = ++retryGeneration, version = actionVersion, key = identityKey()
    const current = () => actionCurrent(version, key) && generation === retryGeneration
    try {
      const response = reportEnvelope(await getSystemTestSuiteDetailsExecutionOptions())
      const limit = reportNumber(reportObject(response.data).api_platform_limit)
      if (limit === null || !Number.isInteger(limit) || limit < 1) throw new Error('Invalid execution options')
      if (!current()) return
      retryState.platformLimit = limit
      retryModalRef.value?.show({ executionName: reportExecutionName(snapshot), testEnv: snapshot.test_env, apiConcurrencyLimit: snapshot.api_concurrency_limit })
    } catch (error: unknown) {
      if (current()) { retryState.record = null; Message.error(reportText(reportObject(error).msg) || '获取平台并发配置失败') }
    } finally { retryState.loading = false }
  }
  function onCancelRetryModal() { retryGeneration++; retryState.record = null }
  async function onConfirmRetryModal(config: { executionName: string; testEnv: number | null; apiConcurrencyLimit: number | null }) {
    const snapshot = retryState.record
    if (!available() || !snapshot || retryState.loading || retryState.failedId !== null) {
      retryModalRef.value?.setConfirmLoading(false)
      return false
    }
    if (config.testEnv === null || !Number.isInteger(config.testEnv) || config.testEnv < 0 ||
      (config.apiConcurrencyLimit !== null && (!Number.isInteger(config.apiConcurrencyLimit) || config.apiConcurrencyLimit < 1 || config.apiConcurrencyLimit > retryState.platformLimit))) {
      retryModalRef.value?.setConfirmLoading(false)
      return false
    }
    const generation = retryGeneration, version = actionVersion, key = identityKey(), id = snapshot.id
    const environment = config.testEnv, concurrency = config.apiConcurrencyLimit
    const current = () => actionCurrent(version, key) && generation === retryGeneration
    retryState.loading = true
    try {
      const response = reportEnvelope(await getSystemTestSuiteDetailsAllRetry(id, environment, concurrency))
      if (!current()) return false
      Message.success(reportText(response.msg) || '已提交重试')
      retryModalRef.value?.close(); onCancelRetryModal(); void doRefresh()
      return true
    } catch (error: unknown) {
      if (current()) Message.error(reportText(reportObject(error).msg) || '重试失败')
      return false
    } finally {
      retryState.loading = false
      if (current()) retryModalRef.value?.setConfirmLoading(false)
    }
  }
  async function onRetryFailed(record: ReportRow | null) {
    if (!available() || !record || retryState.loading || retryState.failedId !== null || isReportRunning(record) || record.automation_types.includes(4) || reportResultCount(record, 'fail') === 0) return false
    const id = record.id, version = actionVersion, key = identityKey(), generation = retryGeneration
    const current = () => actionCurrent(version, key) && generation === retryGeneration
    retryState.failedId = id
    try {
      const response = reportEnvelope(await retryFailedReportCases(id)), count = reportNumber(reportObject(response.data).retry_count)
      if (count === null || !Number.isInteger(count)) throw new Error('Invalid retry result')
      if (!current()) return false
      if (count) Message.success(`已提交 ${count} 个失败执行项重试`)
      else Message.info('这份报告当前没有失败执行项')
      retryModalRef.value?.close(); onCancelRetryModal(); void doRefresh()
      return true
    } catch (error: unknown) {
      if (current()) Message.error(reportText(reportObject(error).msg) || '重试失败项失败')
      return false
    } finally { retryState.failedId = null }
  }
  function buildProjectProductValue(record: ReportRow) {
    const product = record.project_product
    if (!product) return null
    if (product.project?.id !== null && product.project?.id !== undefined) return [product.project.id, product.id]
    return product.id
  }
  function hasTaskNotice(record: ReportRow) { return Boolean(record.tasks?.name && record.tasks.notice_group !== null) }
  async function sendNotice(record: ReportRow, noticeGroup?: ReportId) {
    if (!available() || noticeState.sending) return false
    const id = record.id, generation = noticeGeneration, version = actionVersion, key = identityKey()
    const current = () => actionCurrent(version, key) && generation === noticeGeneration
    const payload: { id: ReportId; notice_group?: ReportId } = { id }
    if (noticeGroup !== undefined) payload.notice_group = noticeGroup
    noticeState.sending = true; noticeState.sendingId = id
    try {
      const response = reportEnvelope(await postSystemTestSuiteSendNotice(payload))
      if (!current()) return false
      Message.success(reportText(response.msg) || '通知发送成功')
      noticeState.visible = false; noticeState.record = null; void doRefresh()
      return true
    } catch (error: unknown) {
      if (current()) Message.error(reportText(reportObject(error).msg) || '发送通知失败')
      return false
    } finally { noticeState.sending = false; noticeState.sendingId = null }
  }
  function confirmSendNotice(record: ReportRow, noticeGroup?: ReportId) {
    if (!available() || noticeConfirmation || noticeState.sending) return Promise.resolve(false)
    const generation = noticeGeneration, version = actionVersion, key = identityKey()
    return new Promise<boolean>(resolve => {
      settleNotice = resolve
      const confirmation = Modal.confirm({ title: '确认发送通知', content: '确定要发送这份测试报告的通知吗？', cancelText: '取消', okText: '发送',
        onBeforeOk: async () => {
          if (!actionCurrent(version, key) || generation !== noticeGeneration) return false
          const success = await sendNotice(record, noticeGroup)
          if (success) { if (noticeConfirmation === confirmation) noticeConfirmation = null; settleNotice = null; resolve(true) }
          return success
        },
        onCancel: () => { if (noticeConfirmation === confirmation) noticeConfirmation = null; settleNotice = null; resolve(false) },
      })
      noticeConfirmation = confirmation
    })
  }
  function onSendNotice(record: ReportRow) {
    const snapshot = parseReportRow(record)
    if (!available() || !snapshot || noticeState.sending || noticeConfirmation) return
    onCancelNoticeModal()
    noticeState.record = snapshot
    if (hasTaskNotice(snapshot)) { void confirmSendNotice(snapshot); return }
    noticeForm.project_product = buildProjectProductValue(snapshot); noticeForm.notice_group = null
    noticeState.visible = true
    void loadNoticeOptions(snapshot.project_product?.id ?? null)
  }
  function loadNoticeOptions(projectProductId: ReportId | null) {
    if (projectProductId === null) { noticeState.options = []; return Promise.resolve(false) }
    return noticeQuery.run({ key: JSON.stringify([projectProductId, noticeState.record?.id]), loading: toRef(noticeState, 'loading'), error: toRef(noticeState, 'error'),
      message: '通知组加载失败，请重试', read: async () => parseReportOptions(await getSystemNoticeName(projectProductId)),
      apply: options => { noticeState.options = options }, fail: () => { noticeState.options = [] },
    })
  }
  function onCancelNoticeModal() {
    noticeGeneration++; noticeQuery.invalidate(); closeNoticeConfirmation()
    noticeState.visible = false; noticeState.record = null; noticeState.options = []; noticeState.error = ''
    noticeForm.project_product = null; noticeForm.notice_group = null
  }
  function onConfirmNoticeModal() {
    const group = reportId(noticeForm.notice_group), record = noticeState.record
    if (group === null) { Message.error('请选择通知组'); return Promise.resolve(false) }
    if (!record || noticeState.loading || noticeState.error || !noticeState.options.some(option => String(option.value) === String(group))) return Promise.resolve(false)
    return confirmSendNotice(record, group)
  }

  function resume() {
    if (!available() || !needsLoad) return
    needsLoad = false
    void loadTaskOptions(); void loadTaskGroupOptions(); void loadUserOptions()
    void doRefresh()
  }
  function pause() {
    invalidateReads()
    pagePolling.stop()
    closeActionWindows()
  }
  function onVisibility() { if (document.visibilityState === 'visible') resume(); else pause() }
  watch(identityKey, () => {
    pause()
    initialized = false
    rows.value = []; pagination.setTotalSize(0); pagination.page = 1
    charts.counts = createReportCounts(); charts.trend = []; charts.error = ''; listError.value = ''; enumError.value = ''
    resetReportConditions(conditionItems); applyRouteFilters()
    sidebarModuleIds.value = []; sidebarResetKey.value++
    for (const item of conditionItems) if (['tasks_id', 'tasks__task_group_id', 'user'].includes(item.key)) item.optionItems = []
    searchErrors.tasks = ''; searchErrors.groups = ''; searchErrors.users = ''
    resume()
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', onVisibility); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => {
    disposed = true; pause()
    document.removeEventListener('visibilitychange', onVisibility)
  })
</script>

<style lang="less" scoped>
  .mango-report-search-errors {
    display: flex;
    flex-wrap: wrap;
    gap: var(--m-page-gap);
  }
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
    display: block;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-report-result-summary__item {
    display: inline-flex;
    margin-right: 6px;
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
