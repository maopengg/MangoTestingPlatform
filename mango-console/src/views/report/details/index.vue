<template>
  <div class="report-lab mango-report-detail-page" :class="{ 'standalone-report-container': isShareReportRoute }">
    <a-alert v-if="reportInfo?.retained_summary" type="info">本次执行成功，已按保留策略清理完整报告，仅保留执行质量摘要。</a-alert>
    
    <mango-panel-spin :loading="reportInfoLoading" class="mango-report-head-spin">
    <section class="report-head">
      <div class="head-main">
        <div class="report-title">
          <p class="eyebrow">TEST REPORT WORKBENCH</p>
          <h1>{{ reportTitle }}</h1>
          <p class="report-subtitle">
            <span>{{ currentTypeLabel }}</span>
            <i></i>
            <span>{{ currentStatusLabel }}</span>
            <i></i>
            <span>通过率 {{ passRate }}%</span>
          </p>
          <a-button
            v-if="reportInfo?.diagnostic_file_path"
            class="mango-report-diagnostic-button"
            size="small"
            @click="diagnosticDrawer.visible = true"
          >查看排查结果</a-button>
        </div>

        <div class="status-console">
          <div class="status-line">
            <span>报告状态</span>
            <a-tag v-if="summary.excluded_count" size="small" color="orange">已排除 {{ summary.excluded_count }} 个用例</a-tag>
            <a-tag :color="statusColor(reportInfo?.report_conclusion ?? reportInfo?.status)" size="small">
              {{ statusText(reportInfo?.report_conclusion ?? reportInfo?.status) }}
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
          <dd>
            <a-tooltip :content="reportExecutionName">
              <span class="mango-report-meta-value" tabindex="0">{{ reportExecutionName }}</span>
            </a-tooltip>
          </dd>
        </div>
        <div class="report-meta-item mango-report-meta-id">
          <dt>报告ID</dt>
          <dd>{{ reportInfo?.id || reportId }}</dd>
        </div>
        <div class="report-meta-item">
          <dt>被测环境</dt>
          <dd>{{ envText(reportInfo?.test_env) }}</dd>
        </div>
        <div v-if="summary.api_count" class="report-meta-item">
          <dt>API 执行并发</dt>
          <dd>{{ reportInfo?.api_concurrency_limit || '平台默认' }}</dd>
        </div>
        <div class="report-meta-item">
          <dt>执行人</dt>
          <dd>{{ reportInfo?.user?.name || '-' }}</dd>
        </div>
        <div class="report-meta-item">
          <dt>通知状态</dt>
          <dd>
            <a-tag :color="noticeColor(reportInfo?.is_notice)" size="small">
              {{ noticeText(reportInfo?.is_notice) }}
            </a-tag>
          </dd>
        </div>
        <div class="report-meta-item mango-report-meta-time">
          <dt>执行时间</dt>
          <dd>{{ reportInfo?.create_time || '-' }}</dd>
        </div>
      </dl>
    </section>
    </mango-panel-spin>

    
    <div class="mango-workbench-scroll-x report-overview-scroll">
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
              :loading="summaryLoading && !totalCount"
              :success="summary.success_count || 0"
              :fail="summary.fail_count || 0"
              :warning="summary.warning_count || 0"
              :pending="summary.proceed_count || 0"
              :todo="summary.stay_begin_count || 0"
              :stopped="summary.stopped_count || 0"
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
              <button
                type="button"
                @click="focusFailed"
                data-testid="qa-views-report-details-button-只看失败"
                >只看失败</button
              >
            </div>
          </div>
        </div>

        <div class="overview-panel failure-reason-panel">
          <div class="panel-title">
            <div>
              <span>失败原因 Top</span>
              <p>基于整份报告失败明细聚合</p>
            </div>
            <em>{{ failureReasonSummary.category_count }} 类</em>
          </div>
          <mango-panel-spin :loading="failureReasonLoading" class="mango-failure-reason-spin">
            <template v-if="failureReasonError"></template>
            <div v-else-if="failureReasons.length === 0" class="reason-empty">
              整份报告中暂无失败原因
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
          </mango-panel-spin>
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
    </div>

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
                <span>共 {{ currentTypeCaseTotal }} 条</span>
              </p>
            </div>
            <div class="case-title-actions">
              <div class="case-keyword-search">
                <a-input-search
                  v-model="caseKeyword"
                  size="small"
                  allow-clear
                  class="case-keyword-search__control"
                  placeholder="请输入明细ID、用例ID或Case名称"
                  aria-label="按报告明细ID、用例ID或Case名称搜索"
                  @search="searchCases"
                  @blur="searchCasesOnBlur"
                  @clear="clearCaseKeyword"
                  data-testid="qa-views-report-details-input-search-按用例id或case名称搜索"
                />
              </div>
              <div v-if="visibleTypeTabs.length > 0" class="mango-report-filter-group">
                <span id="mango-report-type-label" class="case-type-label">自动化类型：</span>
                <a-checkbox-group
                  v-model="activeTypeSelection"
                  class="case-type-checkbox-group"
                  aria-labelledby="mango-report-type-label"
                >
                  <a-checkbox v-for="item in visibleTypeTabs" :key="item.key" :value="item.key">
                    {{ item.label }}({{ item.total }})
                  </a-checkbox>
                </a-checkbox-group>
              </div>
              <div class="mango-report-filter-group">
                <span class="case-status-label">统计范围：</span>
                <div class="case-status-select">
                  <a-select v-model="excludedFilter" size="small" class="case-status-select__control"
                    aria-label="统计范围" @change="reloadCases"
                    :options="[{ value: 'all', label: '全部统计项' }, { value: 'false', label: '参与统计' }, { value: 'true', label: '已排除' }]" />
                </div>
              </div>
              <div class="mango-report-filter-group">
                <span class="case-status-label">测试结果：</span>
                <div class="case-status-select">
                  <a-select
                    v-model="caseStatus"
                    size="small"
                    class="case-status-select__control"
                    aria-label="测试结果"
                    @change="reloadCases"
                  >
                    <a-option
                      v-for="item in caseStatusOptions"
                      :key="String(item.value)"
                      :value="item.value"
                    >
                      {{ item.label }}
                    </a-option>
                  </a-select>
                </div>
              </div>
              <a-button
                v-if="activeType === '1'"
                type="primary"
                size="small"
                :loading="apiExportLoading"
                @click="startApiExport"
                data-testid="qa-views-report-details-button-导出-excel"
              >
                导出 Excel
              </a-button>
            </div>
          </div>
        </div>

        <a-alert v-if="apiExportError" type="error">
          {{ apiExportError }}
          <a-button size="small" :loading="apiExportLoading" @click="startApiExport">重试导出</a-button>
          <a-button v-if="apiExportCanRestart" size="small" :loading="apiExportLoading" @click="restartApiExport">重新导出</a-button>
        </a-alert>

        <mango-panel-spin :loading="caseLoading" class="case-spin">
          <template v-if="caseError"></template>
          <div v-else-if="cases.length === 0" class="empty-state">
            {{ caseLoading ? '正在加载用例结果' : '暂无用例结果' }}
          </div>
          <UiCaseTable
            v-else-if="activeType === '0'"
            :cases="cases"
            :status-options="enumStore.task_status"
            :status-colors="enumStore.status_colors"
            :can-retry="canRetry"
            :retrying-ids="retryingIds"
            @open-case-detail="openCaseDetail"
            @show-details="showDetails"
            @retry="onRetry"
            @disposition-saved="refreshDisposition"
          />
          <ApiCaseTable
            v-else-if="activeType === '1'"
            :cases="cases"
            :status-options="enumStore.task_status"
            :status-colors="enumStore.status_colors"
            :phase-options="enumStore.report_execution_phase"
            :can-retry="canRetry"
            :retrying-ids="retryingIds"
            @open-case-detail="openCaseDetail"
            @show-details="showDetails"
            @show-history="showCaseHistory"
            @disposition-saved="refreshDisposition"
            @retry="onRetry"
          />
          <PytestCaseTable
            v-else-if="activeType === '2'"
            :cases="cases"
            :status-options="enumStore.task_status"
            :status-colors="enumStore.status_colors"
            :can-retry="canRetry"
            :retrying-ids="retryingIds"
            @show-details="showDetails"
            @disposition-saved="refreshDisposition"
            @retry="onRetry"
          />
          <EvaluationCaseTable v-else-if="activeType === '4'" :cases="cases"
            :status-options="enumStore.task_status" :status-colors="enumStore.colors" />
        </mango-panel-spin>

        <div class="case-pagination">
          <a-pagination
            v-model:current="pagination.page"
            v-model:page-size="pagination.pageSize"
            :page-size-options="[20, 50, 100]"
            :total="pagination.total"
            show-total
            show-page-size
            size="small"
            @change="onCasePageChange"
            @page-size-change="onCasePageSizeChange"
          />
        </div>
      </div>
    </section>

    <ReportExecutionResultDrawer ref="executionResultDrawer" :report-id="reportId" />

    <ExecutionResultHistoryDrawer
      v-model:visible="apiHistoryDrawer.visible"
      :title="apiHistoryDrawer.title"
      :case-id="apiHistoryDrawer.caseId"
      :test-suite-detail-id="apiHistoryDrawer.testSuiteDetailId"
      :current-test-suite-id="reportId"
      :preferred-parameter-id="apiHistoryDrawer.preferredParameterId"
      description="查看本测试报告、其他测试报告及 Case 单独执行的历史结果"
      @show-trace="showExecutionTrace"
    />

    <ReportExecutionTraceDrawer ref="executionTraceDrawer" :report-id="reportId" />

    <BaseSidePanel
      :visible="caseDetailDrawer.visible"
      title="用例详情"
      width="calc(92vw - 150px)"
      mode="page"
      @update:visible="
        (val) => {
          caseDetailDrawer.visible = val
        }
      "
      @cancel="caseDetailDrawer.visible = false"
    >
      <div class="mango-report-case-detail-panel">
        <ApiCaseDetails
          v-if="
            caseDetailDrawer.visible && caseDetailDrawer.caseType === 1 && caseDetailDrawer.caseId
          "
          :key="`api-${caseDetailDrawer.caseId}`"
          embedded
          :case-id="caseDetailDrawer.caseId"
          @close="caseDetailDrawer.visible = false"
        />
        <UiCaseDetails
          v-else-if="
            caseDetailDrawer.visible && caseDetailDrawer.caseType === 0 && caseDetailDrawer.caseId
          "
          :key="`ui-${caseDetailDrawer.caseId}`"
          embedded
          :case-id="caseDetailDrawer.caseId"
          @close="caseDetailDrawer.visible = false"
        />
      </div>
    </BaseSidePanel>
    <DiagnosticMarkdownDrawer
      v-model:visible="diagnosticDrawer.visible"
      target-type="test_report"
      :target-id="reportInfo?.id || reportId"
      :title="`${reportTitle} · 排查结果`"
    />
  </div>
</template>

<script lang="ts" setup>
import { runLoadRequest } from '@/utils/load-error'

  import { usePagePolling, isPendingExecution, type PollingContext } from '@/hooks/use-page-polling'
  import { createReportReadSession } from './report-read-session'
  import { caseStatusOptions } from './config'
  import { reportResultTarget, type ReportResultTarget } from './report-result'
  import ReportExecutionResultDrawer from './components/ReportExecutionResultDrawer.vue'
  import { emptyReportSummary, emptyReportFailureReasons, parseReportOverview, parseReportSummary, parseReportFailureReasons, parseReportCasePage, reportIdentifier, reportObject, type ReportOverview } from './report-overview'
  import {
    computed,
    onActivated,
    onDeactivated,
    onMounted,
    onUnmounted,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { useReportApiExport } from './composables/useReportApiExport'
  import { useReportCaseRetry } from './composables/useReportCaseRetry'
  import {
    getSystemTestSuiteDetailsFailureReasonsShare,
    getSystemTestSuiteDetailsShare,
    getSystemTestSuiteDetailsSummaryShare,
  } from '@/api/system/test_sute_details'
  import { getSystemTestSuiteShare } from '@/api/system/test_suite'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePageData } from '@/store/page-data'
  import { useUserStoreContext } from '@/store/modules/user'
  import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ApiCaseDetails from '@/views/apitest/case/details/index.vue'
  import UiCaseDetails from '@/views/uitest/case/details/index.vue'
  import UiCaseTable from './UiCaseTable.vue'
  import ApiCaseTable from './ApiCaseTable.vue'
  import PytestCaseTable from './PytestCaseTable.vue'
  import EvaluationCaseTable from './EvaluationCaseTable.vue'
  import ReportExecutionTraceDrawer from './components/ReportExecutionTraceDrawer.vue'
  import type { ReportTraceQuery } from './execution-trace'
  import StatusChart from '@/components/chart/StatusChart.vue'
  import DiagnosticMarkdownDrawer from '@/components/reports/DiagnosticMarkdownDrawer.vue'

  const route = useRoute()
  const enumStore = useEnum()
  const pageData = usePageData()
  const userStore = useUserStoreContext()
  const isShareReportRoute = computed(() => route.path === '/report/details')

  const reportInfo = ref<ReportOverview | null>(null)
  const canRetry = computed(() => !reportInfo.value?.retained_summary && !summary.value.evaluation_count)
  const diagnosticDrawer = reactive({ visible: false })
  const summary = ref(emptyReportSummary())
  const cases = ref<unknown[]>([])
  const activeType = ref('0')
  const caseStatus = ref<number | 'all'>('all')
  const caseKeyword = ref('')
  const lastSearchedCaseKeyword = ref('')
  const summaryLoading = ref(false)
  const failureReasonLoading = ref(false)
  const failureReasonSummary = ref(emptyReportFailureReasons())
  const reportInfoLoading = ref(false)
  const reportInfoError = ref('')
  const summaryError = ref('')
  const failureReasonError = ref('')
  const caseError = ref('')
  const caseLoading = ref(false)
  const apiHistoryDrawer = reactive<{
    visible: boolean
    title: string
    caseId: number | string
    testSuiteDetailId: number | string
    preferredParameterId?: number | string
  }>({
    visible: false,
    title: 'API 用例执行历史',
    caseId: '',
    testSuiteDetailId: '',
  })
  const caseDetailDrawer = reactive({
    visible: false,
    caseId: '',
    caseType: -1,
  })
  const isPolling = ref(false)
  const pagePolling = usePagePolling(async context => {
    if (!reportPageActive.value || !reportId.value) return
    const id = reportId.value
    const currentVersion = pageVersion
    const currentContext = { isCurrent: () => context.isCurrent() && currentVersion === pageVersion && reportId.value === id }
    await Promise.all([loadSummary(true, currentContext), loadReportInfo(true, currentContext)])
    if (!currentContext.isCurrent()) return
    await refreshLoadedCases(true, currentContext)
    if (!currentContext.isCurrent()) return
    if (!hasPendingReport()) {
      await loadFailureReasons(true, currentContext)
      if (currentContext.isCurrent()) stopPolling()
    }
  }, () => {
    invalidateReportReads()
  })
  const reportPageActive = ref(true)
  const executionResultDrawer = ref<{ open(target: ReportResultTarget): Promise<void>; close(): void } | null>(null)
  const executionTraceDrawer = ref<{ open(query: ReportTraceQuery): Promise<void>; close(): void } | null>(null)

  const pagination = reactive({
    page: 1,
    pageSize: 20,
    total: 0,
  })

  // 报告页可能被 keep-alive 缓存，不能让其他页面的 route.query.id 覆盖当前报告 ID。
  const reportId = ref(reportIdentifier(route.query.id) ?? reportIdentifier(reportObject(pageData.record)?.id) ?? '')
  const reportPaths = ['/report/details', '/report/system/details']
  let disposed = false, mounted = false, pageVersion = 0
  let reportEntryFullPath = route.fullPath
  const reportAvailable = () => !disposed && reportPageActive.value && reportPaths.includes(route.path) && document.visibilityState === 'visible' && reportId.value !== ''
  const infoReads = createReportReadSession(reportAvailable)
  const summaryReads = createReportReadSession(reportAvailable)
  const failureReads = createReportReadSession(reportAvailable)
  const caseReads = createReportReadSession(reportAvailable)
  let searchBlurTimer: ReturnType<typeof setTimeout> | undefined
  const totalCount = computed(() => summary.value.count || 0)
  const excludedFilter = ref('all')
  const { loading: apiExportLoading, error: apiExportError, canRestart: apiExportCanRestart, start: startApiExport, restart: restartApiExport } = useReportApiExport({
    reportId: () => reportId.value, status: () => caseStatus.value, available: reportAvailable,
  })
  const { busyIds: retryingIds, confirm: onRetry } = useReportCaseRetry({
    reportId: () => reportId.value, available: reportAvailable,
    onSuccess: async () => { await Promise.allSettled([loadSummary(), loadReportInfo(), loadCases(true)]) },
  })
  const failRatio = computed(() => ratio(summary.value.fail_count, totalCount.value))
  const passRate = computed(() => !totalCount.value && summary.value.excluded_count ? 100 : ratio(summary.value.success_count, totalCount.value))
  const reportExecutionName = computed(
    () => reportInfo.value?.tasks?.name || reportInfo.value?.execution_name || ''
  )
  const reportTitle = computed(() => reportExecutionName.value || `测试报告 #${reportId.value}`)
  const hasTaskName = computed(() => !!reportExecutionName.value)
  const failureReasons = computed(() => failureReasonSummary.value.items || [])

  const typeProgress = computed(() =>
    [
      {
        key: 'ui',
        type: '0',
        label: 'UI 自动化',
        tabLabel: 'UI',
        total: summary.value.raw_ui_count ?? summary.value.ui_count ?? 0,
        done: summary.value.ui_in_progress_count || 0,
        percent: ratioValue(summary.value.ui_in_progress_count, summary.value.ui_count) / 100,
      },
      {
        key: 'api',
        type: '1',
        label: 'API 自动化',
        tabLabel: 'API',
        total: summary.value.raw_api_count ?? summary.value.api_count ?? 0,
        done: summary.value.api_in_progress_count || 0,
        percent: ratioValue(summary.value.api_in_progress_count, summary.value.api_count) / 100,
      },
      {
        key: 'pytest',
        type: '2',
        label: 'Pytest',
        tabLabel: 'Pytest',
        total: summary.value.raw_pytest_count ?? summary.value.pytest_count ?? 0,
        done: summary.value.pytest_in_progress_count || 0,
        percent:
          ratioValue(summary.value.pytest_in_progress_count, summary.value.pytest_count) / 100,
      },
      {
        key: 'evaluation', type: '4', label: '效果测试', tabLabel: '效果测试',
        total: summary.value.raw_evaluation_count ?? summary.value.evaluation_count ?? 0,
        done: summary.value.evaluation_in_progress_count || 0,
        percent: ratioValue(summary.value.evaluation_in_progress_count, summary.value.evaluation_count) / 100,
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
  const currentTypeCaseTotal = computed(() => {
    return typeProgress.value.find((item) => item.type === activeType.value)?.total || 0
  })
  const activeTypeSelection = computed<string[]>({
    get() {
      return activeType.value ? [activeType.value] : []
    },
    set(values) {
      const selectedValues = values.map(String)
      const nextType =
        selectedValues.find((item) => item !== activeType.value) ||
        activeType.value ||
        visibleTypeTabs.value[0]?.key
      if (!nextType || nextType === activeType.value) return
      selectType(nextType)
    },
  })
  const currentTypeLabel = computed(() => {
    if (activeType.value === '1') return 'API 自动化'
    if (activeType.value === '2') return 'Pytest'
    if (activeType.value === '4') return '效果测试'
    return 'UI 自动化'
  })
  const currentStatusLabel = computed(() => {
    const map: Record<number, string> = {
      0: '只看失败',
      1: '只看成功',
      2: '只看待开始',
      3: '只看进行中',
      4: '只看警告',
    }
    return caseStatus.value === 'all' ? '全部结果' : map[caseStatus.value] || '全部结果'
  })

  function ratioValue(value = 0, total = 0) {
    if (!total) return 0
    return (Number(value || 0) / Number(total)) * 100
  }

  function ratio(value = 0, total = 0) {
    return ratioValue(value, total).toFixed(2)
  }

  function statusColor(status: number | null | undefined) {
    return status == null ? 'gray' : enumStore.status_colors?.[status] || 'gray'
  }

  function statusText(status: number | null | undefined) {
    return status == null ? '未知' : enumStore.task_status.find(item => Number(item.key) === status)?.title || '未知'
  }


  function envText(env: number | null | undefined) {
    return enumStore.environment_type.find((item) => String(item.key) === String(env))?.title || '-'
  }

  function noticeText(status: number | null | undefined) {
    return status == null ? '-' : enumStore.test_suite_notice.find(item => Number(item.key) === status)?.title || '-'
  }

  function noticeColor(status: number | null | undefined) {
    return status == null ? 'gray' : enumStore.colors?.[status] || 'gray'
  }


  async function showDetails(value: unknown) {
    if (!reportAvailable()) return
    const record = reportObject(value)
    if (!record) return
    if (record?.__isWarningRow) {
      Message.warning('该用例前置步骤失败，未被执行')
      return
    }
    const detailId = reportIdentifier(record.test_suite_detail_id ?? record.__caseSourceId)
    if (detailId === null) return
    if (Number(record?.case_type ?? activeType.value) === 1) {
      const caseId = reportIdentifier(record.__caseId ?? record.case_id)
      const historyTargetName =
        record?.__caseName || record?.name || (caseId !== null ? `Case ${caseId}` : `明细 ${detailId}`)
      apiHistoryDrawer.title = `用例执行历史：${historyTargetName}`
      apiHistoryDrawer.caseId = ''
      apiHistoryDrawer.testSuiteDetailId = detailId
      apiHistoryDrawer.preferredParameterId = typeof record.parameter_id === 'string' || typeof record.parameter_id === 'number' ? record.parameter_id : undefined
      apiHistoryDrawer.visible = true
      return
    }
    const target = reportResultTarget(record, activeType.value)
    if (target) await executionResultDrawer.value?.open(target)
  }

  function showCaseHistory(value: unknown) {
    if (!reportAvailable()) return
    const record = reportObject(value)
    const caseId = reportIdentifier(record?.__caseId ?? record?.case_id)
    if (caseId === null) {
      Message.error('当前报告明细缺少 API Case ID，无法查询历史报告')
      return
    }
    apiHistoryDrawer.title = `用例执行历史：${record?.__caseName || record?.name || `Case ${caseId}`}`
    apiHistoryDrawer.caseId = caseId
    apiHistoryDrawer.testSuiteDetailId = ''
    apiHistoryDrawer.preferredParameterId = undefined
    apiHistoryDrawer.visible = true
  }


  function showExecutionTrace(query: ReportTraceQuery) {
    return executionTraceDrawer.value?.open(query)
  }

  function openCaseDetail(value: unknown) {
    if (!reportAvailable()) return
    const record = reportObject(value)
    const caseId = reportIdentifier(record?.__caseId ?? record?.case_id ?? record?.id)
    if (caseId === null) {
      Message.error('未找到用例ID')
      return
    }
    const caseType = Number(record?.case_type ?? activeType.value)
    if (![0, 1].includes(caseType)) {
      Message.error('当前用例类型暂不支持打开用例详情')
      return
    }
    caseDetailDrawer.caseId = String(caseId)
    caseDetailDrawer.caseType = caseType
    caseDetailDrawer.visible = true
  }

  function buildCaseQuery() {
    const data: Record<string, string | number> = {
      test_suite_id: reportId.value,
      type: activeType.value,
      page: pagination.page,
      pageSize: pagination.pageSize,
    }
    if (caseStatus.value !== 'all') {
      data.status = caseStatus.value
    }
    if (excludedFilter.value !== 'all') data.is_excluded = excludedFilter.value
    const normalizedKeyword = caseKeyword.value.trim()
    if (normalizedKeyword) {
      data.case_keyword = normalizedKeyword
    }
    return data
  }

  function loadReportInfo(silent = false, context?: PollingContext) {
    const id = reportId.value
    return infoReads.run({ key: id, silent, loading: reportInfoLoading, error: reportInfoError,
      message: '报告信息加载失败，请重试',
      isCurrent: context?.isCurrent,
      read: async () => parseReportOverview(await runLoadRequest(silent, () => getSystemTestSuiteShare(id, silent)), id),
      apply: value => { reportInfo.value = value; if (!silent) handlePolling() },
    })
  }

  function loadSummary(silent = false, context?: PollingContext) {
    const id = reportId.value
    return summaryReads.run({ key: id, silent, loading: summaryLoading, error: summaryError,
      message: '报告统计加载失败，请重试', isCurrent: context?.isCurrent,
      read: async () => parseReportSummary(await runLoadRequest(silent, () => getSystemTestSuiteDetailsSummaryShare(id, silent))),
      apply: value => {
        summary.value = value
        const firstVisibleType = visibleTypeTabs.value[0]
        if (firstVisibleType && !visibleTypeTabs.value.some(item => item.key === activeType.value)) {
          activeType.value = firstVisibleType.key
          pagination.page = 1
          cases.value = []
          void refreshLoadedCases(silent, context).catch(() => {})
        }
        if (!silent) handlePolling()
      },
    })
  }

  async function refreshDisposition() {
    await Promise.allSettled([loadSummary(), loadReportInfo(), refreshLoadedCases()])
  }

  function loadFailureReasons(silent = false, context?: PollingContext) {
    const id = reportId.value
    return failureReads.run({ key: id, silent, loading: failureReasonLoading, error: failureReasonError,
      message: '失败原因加载失败，请重试', isCurrent: context?.isCurrent,
      read: async () => parseReportFailureReasons(await runLoadRequest(silent, () => getSystemTestSuiteDetailsFailureReasonsShare(id, silent))),
      apply: value => { failureReasonSummary.value = value },
    })
  }

  function loadCases(reset = false) {
    if (reset) {
      cases.value = []
      pagination.page = 1
      pagination.total = 0
    }
    return refreshLoadedCases()
  }

  function reloadCases() {
    return loadCases(true)
  }

  function searchCases() {
    const normalizedKeyword = caseKeyword.value.trim()
    if (normalizedKeyword === lastSearchedCaseKeyword.value && !caseError.value) return
    lastSearchedCaseKeyword.value = normalizedKeyword
    reloadCases()
  }

  function searchCasesOnBlur() {
    if (searchBlurTimer !== undefined) clearTimeout(searchBlurTimer)
    const currentVersion = pageVersion
    searchBlurTimer = setTimeout(() => {
      searchBlurTimer = undefined
      if (pageVersion === currentVersion && reportAvailable()) searchCases()
    }, 0)
  }

  function clearCaseKeyword() {
    caseKeyword.value = ''
    searchCases()
  }

  function onCasePageChange(page: number) {
    pagination.page = page
    loadCases()
  }

  function onCasePageSizeChange(pageSize: number) {
    pagination.pageSize = pageSize
    reloadCases()
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

  function refreshLoadedCases(silent = false, context?: PollingContext) {
    const query = buildCaseQuery(), key = JSON.stringify(query)
    return caseReads.run({ key, silent, loading: caseLoading, error: caseError,
      message: '用例结果加载失败，请重试',
      isCurrent: () => key === JSON.stringify(buildCaseQuery()) && (context?.isCurrent() ?? true),
      read: async () => parseReportCasePage(await runLoadRequest(silent, () => getSystemTestSuiteDetailsShare(query, silent))),
      apply: value => { cases.value = value.rows; pagination.total = value.total },
    })
  }

  function handlePolling() {
    if (!reportPageActive.value) {
      stopPolling()
      return
    }
    const hasInProgress = hasPendingReport()
    if (hasInProgress && !isPolling.value) {
      startPolling()
    } else if (!hasInProgress && isPolling.value) {
      stopPolling()
    }
  }

  function hasPendingReport() {
    return summary.value.stay_begin_count > 0 || summary.value.proceed_count > 0 || isPendingExecution(reportInfo.value)
  }

  function startPolling() {
    if (!reportPageActive.value || !reportId.value) return
    isPolling.value = true
    pagePolling.start()
  }

  function stopPolling() {
    pagePolling.stop()
    isPolling.value = false
  }

  function invalidateReportReads(clear = false) {
    pageVersion += 1
    infoReads.invalidate(); summaryReads.invalidate(); failureReads.invalidate(); caseReads.invalidate()
    if (searchBlurTimer !== undefined) clearTimeout(searchBlurTimer)
    searchBlurTimer = undefined
    apiHistoryDrawer.visible = false
    caseDetailDrawer.visible = false
    diagnosticDrawer.visible = false
    executionTraceDrawer.value?.close()
    executionResultDrawer.value?.close()
    if (clear) {
      reportInfo.value = null
      summary.value = emptyReportSummary()
      failureReasonSummary.value = emptyReportFailureReasons()
      cases.value = []
      pagination.total = 0
      reportInfoError.value = ''; summaryError.value = ''; failureReasonError.value = ''; caseError.value = ''
    }
  }

  async function initializeReport() {
    if (!reportAvailable()) return
    const currentVersion = pageVersion
    void loadReportInfo()
    void loadFailureReasons()
    await loadSummary()
    if (pageVersion !== currentVersion || !reportAvailable()) return
    if (summaryError.value) startPolling()
    await loadCases()
  }

  function onReportVisibilityChange() {
    if (document.visibilityState === 'visible') {
      if (reportPageActive.value) void initializeReport()
    } else invalidateReportReads()
  }

  watch(() => JSON.stringify(buildCaseQuery()), () => caseReads.invalidate(), { flush: 'sync' })
  watch(() => [route.fullPath, userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment], () => {
    stopPolling()
    invalidateReportReads(true)
    if (!reportPaths.includes(route.path)) return
    const sameEntry = route.fullPath === reportEntryFullPath
    reportEntryFullPath = route.fullPath
    reportId.value = reportIdentifier(route.query.id) ?? (sameEntry && route.query.id === undefined ? reportId.value : '')
    pagination.page = 1
    activeType.value = '0'
    caseStatus.value = 'all'
    excludedFilter.value = 'all'
    caseKeyword.value = ''
    lastSearchedCaseKeyword.value = ''
    if (mounted) void initializeReport()
  }, { flush: 'sync' })

  onMounted(() => {
    mounted = true
    document.addEventListener('visibilitychange', onReportVisibilityChange)
    if (!enumStore.task_status?.length) void enumStore.getEnumShare()
    void initializeReport()
  })

  onActivated(() => {
    const resume = !reportPageActive.value
    reportPageActive.value = true
    if (resume) void initializeReport()
  })

  onDeactivated(() => {
    reportPageActive.value = false
    stopPolling()
    invalidateReportReads(true)
  })

  onUnmounted(() => {
    disposed = true
    reportPageActive.value = false
    stopPolling()
    invalidateReportReads(true)
    document.removeEventListener('visibilitychange', onReportVisibilityChange)
  })
</script>

<style scoped lang="less">
  .report-lab {
    box-sizing: border-box;
    min-width: 0;
    width: 100%;
    min-height: 100%;
    padding: var(--m-page-gap);
    background: var(--m-bg);
    color: var(--m-text);
  }

  .mango-report-detail-page {
    container: mango-report-detail / inline-size;
  }

  .mango-report-head-spin {
    display: block;
    width: 100%;
    min-width: 0;
  }

  .standalone-report-container {
    height: 100vh;
    padding: var(--m-space-lg);
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


  .report-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 190px;
    column-gap: var(--m-space-lg);
    position: relative;
    overflow: hidden;
    padding: var(--m-card-padding);
  }

  .report-head::before {
    position: absolute;
    inset: 0 auto 0 0;
    width: 3px;
    background: linear-gradient(180deg, var(--m-primary), var(--m-success));
    content: '';
  }

  .head-main {
    display: contents;
  }

  .report-title {
    min-width: 0;
    padding-left: 2px;
  }

  .mango-report-diagnostic-button {
    margin-top: 10px;
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
    grid-column: 2;
    grid-row: 1 / span 2;
    align-self: stretch;
    min-width: 0;
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
    grid-column: 1;
    grid-row: 2;
    min-width: 0;
    display: grid;
    grid-template-columns: minmax(230px, 1.4fr) repeat(4, minmax(0, 1fr)) minmax(240px, 1.4fr);
    align-items: center;
    gap: var(--m-space-md) var(--m-space-lg);
    margin: var(--m-space-md) 0 0;
    padding: var(--m-space-md) 0 0;
    border-top: 1px solid var(--m-border);
  }

  .meta-strip.has-task-name {
    grid-template-columns: minmax(0, 1.6fr) minmax(230px, 1.4fr) repeat(4, minmax(0, 1fr)) minmax(240px, 1.4fr);
  }

  .report-meta-item {
    display: flex;
    min-width: 0;
    min-height: 32px;
    justify-content: center;
    align-items: center;
    gap: var(--m-space-xs);
    text-align: center;
  }

  .report-meta-item dt {
    margin: 0;
    flex: none;
    color: var(--m-muted);
    font-size: var(--m-font-caption);
    line-height: var(--m-line-caption);
    white-space: nowrap;
  }

  .report-meta-item dt::after {
    content: '：';
  }

  .report-meta-item dd {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    min-height: var(--m-line-subtitle);
    margin: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: var(--m-font-body);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    line-height: var(--m-line-subtitle);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-report-meta-value {
    display: block;
    min-width: 0;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-report-meta-id dd {
    flex-shrink: 0;
  }

  .mango-report-meta-value:focus-visible {
    outline: 1px solid var(--m-primary);
    outline-offset: 1px;
  }

  .report-meta-item dd :deep(.arco-tag) {
    margin: 0;
  }

  .overview-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(0, 1.35fr) minmax(0, 1fr);
    align-items: stretch;
    gap: var(--m-page-gap);
    margin-bottom: var(--m-page-gap);
    margin-top: var(--m-page-gap);
  }

  .report-overview-scroll {
    --mango-workbench-min-width: 0px;
    height: auto;
    margin-top: var(--m-page-gap);
    margin-bottom: var(--m-page-gap);
  }

  .report-overview-scroll > .overview-grid {
    min-width: var(--mango-workbench-min-width);
    margin: 0;
  }

  .overview-panel {
    height: 100%;
    min-height: 0;
    padding: var(--m-card-padding);
  }

  .result-stack {
    display: grid;
    height: 100%;
    min-width: 0;
    grid-template-rows: minmax(0, 1fr) auto;
    gap: var(--m-page-gap);
  }

  .result-panel {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .result-panel :deep(.mango-status-chart) {
    height: 190px;
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

  .mango-failure-reason-spin {
    display: block;
    min-height: 112px;
    flex: 1;
  }

  .mango-failure-reason-spin :deep(> .mango-panel-spin__content) {
    height: 100%;
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
    overflow: visible;
    padding: 0;
  }

  .case-toolbar {
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-space-md);
    padding: var(--m-card-padding);
    background: color-mix(in srgb, var(--m-surface) 94%, transparent);
    border-bottom: 1px solid var(--m-border);
    backdrop-filter: blur(8px);
  }

  .case-toolbar-main {
    display: flex;
    align-items: center;
    gap: var(--m-space-md);
    flex-wrap: wrap;
    min-width: 0;
    width: 100%;
    justify-content: space-between;
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

  .case-title-actions {
    display: flex;
    align-items: center;
    gap: var(--m-space-sm) var(--m-space-md);
    flex: 1 1 720px;
    min-width: 0;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .case-keyword-search {
    flex: 1 1 220px;
    max-width: 320px;
    min-width: min(220px, 100%);
  }

  .case-keyword-search__control {
    width: 100%;
  }

  .case-type-checkbox-group {
    display: flex;
    align-items: center;
    gap: var(--m-space-sm);
    flex-wrap: wrap;
    white-space: nowrap;
  }

  .mango-report-filter-group {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    min-width: 0;
    gap: var(--m-space-sm);
  }

  .case-type-label,
  .case-status-label {
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }

  .case-status-select {
    flex: 0 0 160px;
    width: 160px;
    min-width: 0;
  }

  .case-status-select__control {
    width: 100%;
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

  .case-main {
    min-width: 0;
  }

  .case-spin {
    width: 100%;
    min-height: 220px;
  }

  .empty-state {
    min-height: 46px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
  }

  .case-pagination {
    position: sticky;
    z-index: 20;
    bottom: 0;
    display: flex;
    min-height: 48px;
    align-items: center;
    justify-content: flex-end;
    padding: var(--m-space-sm) var(--m-card-padding);
    border-top: 1px solid var(--m-border);
    background: var(--m-surface);
    box-shadow: 0 -6px 12px color-mix(in srgb, var(--m-surface) 86%, transparent);
  }

  .mango-report-case-detail-panel {
    height: 100%;
    min-height: 0;

    :deep(.mango-detail-workbench-page) {
      height: 100%;
      min-height: 0;
    }
  }

  @container mango-report-detail (max-width: 90rem) {
    .meta-strip,
    .meta-strip.has-task-name {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  @container mango-report-detail (max-width: 68rem) {
    .meta-strip,
    .meta-strip.has-task-name {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .overview-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .type-panel {
      grid-column: 1 / -1;
    }

    .case-toolbar-main {
      align-items: flex-start;
      flex-direction: column;
      width: 100%;
    }

    .case-title-actions {
      flex-basis: auto;
      width: 100%;
      justify-content: flex-start;
    }
  }

  @container mango-report-detail (max-width: 44rem) {
    .report-head {
      grid-template-columns: minmax(0, 1fr);
      row-gap: var(--m-space-md);
    }

    .meta-strip,
    .meta-strip.has-task-name {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .meta-strip.has-task-name .mango-report-meta-time {
      grid-column: 1 / -1;
    }

    .status-console {
      grid-column: 1;
      grid-row: 3;
      min-height: 72px;
      padding: 10px 12px;
    }

    .status-console strong {
      font-size: 24px;
      line-height: 28px;
    }

    .overview-grid {
      grid-template-columns: minmax(0, 1fr);
    }

    .type-panel {
      grid-column: auto;
    }

    .case-keyword-search {
      flex-basis: 100%;
      max-width: none;
    }

    h1 {
      font-size: 18px;
      line-height: 25px;
    }
  }
</style>
