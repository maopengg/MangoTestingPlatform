<template>
  <div class="report-lab mango-report-detail-page" :class="{ 'standalone-report-container': isShareReportRoute }">
    <a-alert v-if="reportInfo.retained_summary" type="info">本次执行成功，已按保留策略清理完整报告，仅保留执行质量摘要。</a-alert>
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
            v-if="reportInfo.diagnostic_file_path"
            class="mango-report-diagnostic-button"
            size="small"
            @click="diagnosticDrawer.visible = true"
          >查看排查结果</a-button>
        </div>

        <div class="status-console">
          <div class="status-line">
            <span>报告状态</span>
            <a-tag v-if="summary.excluded_count" size="small" color="orange">已排除 {{ summary.excluded_count }} 个用例</a-tag>
            <a-tag :color="statusColor(reportInfo.report_conclusion ?? reportInfo.status)" size="small">
              {{ statusText(reportInfo.report_conclusion ?? reportInfo.status) }}
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
        <div class="report-meta-item">
          <dt>报告ID</dt>
          <dd>{{ reportInfo.id || reportId }}</dd>
        </div>
        <div class="report-meta-item">
          <dt>被测环境</dt>
          <dd>{{ envText(reportInfo.test_env) }}</dd>
        </div>
        <div v-if="summary.api_count" class="report-meta-item">
          <dt>API 执行并发</dt>
          <dd>{{ reportInfo.api_concurrency_limit || '平台默认' }}</dd>
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
        <div class="report-meta-item mango-report-meta-time">
          <dt>执行时间</dt>
          <dd>{{ reportInfo.create_time || '-' }}</dd>
        </div>
      </dl>
    </section>

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
            <div v-if="failureReasons.length === 0" class="reason-empty">
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
              <a-button v-permission="'report:export'"
                v-if="activeType === '1'"
                type="primary"
                size="small"
                :loading="apiExport.loading"
                @click="startApiExport"
                data-testid="qa-views-report-details-button-导出-excel"
              >
                导出 Excel
              </a-button>
            </div>
          </div>
        </div>

        <mango-panel-spin :loading="caseLoading" class="case-spin">
          <div v-if="cases.length === 0" class="empty-state">
            {{ caseLoading ? '正在加载用例结果' : '暂无用例结果' }}
          </div>
          <UiCaseTable
            v-else-if="activeType === '0'"
            :cases="cases"
            :enum-store="enumStore"
            :can-retry="canRetry"
            @open-case-detail="openCaseDetail"
            @show-details="showDetails"
            @retry="onRetry"
            @disposition-saved="refreshDisposition"
          />
          <ApiCaseTable
            v-else-if="activeType === '1'"
            :cases="cases"
            :enum-store="enumStore"
            :can-retry="canRetry"
            @open-case-detail="openCaseDetail"
            @show-details="showDetails"
            @show-history="showCaseHistory"
            @disposition-saved="refreshDisposition"
            @retry="onRetry"
          />
          <PytestCaseTable
            v-else-if="activeType === '2'"
            :cases="cases"
            :enum-store="enumStore"
            :can-retry="canRetry"
            @show-details="showDetails"
            @disposition-saved="refreshDisposition"
            @retry="onRetry"
          />
          <EvaluationCaseTable v-else-if="activeType === '4'" :cases="cases" :enum-store="enumStore" />
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

    <a-drawer
      v-model:visible="drawerVisible"
      :width="'min(1280px, 80vw)'"
      :footer="false"
      title="测试用例详情"
      class="mango-report-result-drawer"
      unmount-on-close
    >
      <div class="mango-report-result-history">
        <ExecutionHistoryList
          :items="detailHistoryItems"
          :selected-id="selectedResultId"
          :loading="detailHistoryLoading"
          @select="changeDetailResult"
        />
        <mango-panel-spin
          :loading="detailLoading"
          class="report-detail-spin"
          :class="{ 'report-detail-spin--api': selectedCase.case_type === 1 }"
        >
          <div v-if="!selectedCaseHasDetail" class="report-detail-empty">
            <a-alert
              v-if="selectedCase?.error_message"
              type="error"
              class="report-detail-empty__alert"
            >
              {{ selectedCase.error_message }}
            </a-alert>
            <span>本次执行没有生成测试结果</span>
          </div>
          <template v-else-if="selectedCase.case_type === 0">
            <ElementTestReport :resultData="selectedCase" />
          </template>
          <template v-else-if="selectedCase.case_type === 1">
            <ApiTestReport :resultData="selectedCase" contained />
          </template>
          <template v-else-if="selectedCase.case_type === 2">
            <PytestTestReport :resultData="selectedCase" />
          </template>
        </mango-panel-spin>
      </div>
    </a-drawer>

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

    <a-drawer v-model:visible="traceDrawer.visible" :width="860" title="API 执行链路">
      <mango-panel-spin :loading="traceDrawer.loading" class="mango-trace-drawer-spin">
        <div v-if="!traceDrawer.trace" class="mango-trace-empty">
          本次执行没有链路记录，请重试该 API 用例后再查看
        </div>
        <div v-else class="mango-trace-panel">
          <div class="mango-trace-summary">
            <div>
              <span>Trace ID</span>
              <strong>{{ traceDrawer.trace.trace_id }}</strong>
            </div>
            <div>
              <span>状态</span>
              <a-tag :color="traceStatusColor(traceDrawer.trace.status)" size="small">
                {{ traceStatusText(traceDrawer.trace.status) }}
              </a-tag>
            </div>
            <div>
              <span>耗时</span>
              <strong>{{ traceDrawer.trace.duration_ms || 0 }} ms</strong>
            </div>
            <div>
              <span>触发时间</span>
              <strong>{{ traceDrawer.trace.started_at || '-' }}</strong>
            </div>
            <div>
              <span>完成时间</span>
              <strong>{{ traceDrawer.trace.finished_at || '-' }}</strong>
            </div>
            <div>
              <span>执行来源</span>
              <strong>{{ traceSourceText(traceDrawer.trace.source_type) }}</strong>
            </div>
            <div>
              <span>执行节点</span>
              <strong>{{ traceDrawer.trace.worker_name || '-' }}</strong>
            </div>
          </div>
          <div class="mango-trace-flow-layout">
            <div class="mango-trace-flow">
              <button
                v-for="node in visibleTraceNodes"
                :key="node.id"
                type="button"
                class="mango-trace-node"
                :class="[
                  traceNodeClass(node.status),
                  { 'is-active': traceDrawer.selectedNode?.id === node.id },
                ]"
                :style="{ marginLeft: `${scaleDensityPixels(traceNodeDepth(node) * 18)}px` }"
                @click="selectTraceNode(node)"
              >
                <span
                  class="mango-trace-node__toggle"
                  :class="{
                    'is-visible': traceNodeHasChildren(node),
                    'is-expanded': traceNodeExpanded(node),
                  }"
                  @click.stop="toggleTraceNode(node)"
                ></span>
                <span class="mango-trace-node__dot"></span>
                <span class="mango-trace-node__body">
                  <strong>{{ node.label }}</strong>
                  <span>{{ node.step_type }} / {{ node.duration_ms || 0 }} ms</span>
                </span>
              </button>
            </div>
            <div class="mango-trace-node-detail">
              <template v-if="traceDrawer.selectedNode">
                <div class="mango-trace-node-detail__title">
                  <strong>{{ traceDrawer.selectedNode.label }}</strong>
                  <a-tag :color="traceStatusColor(traceDrawer.selectedNode.status)" size="small">
                    {{ traceStatusText(traceDrawer.selectedNode.status) }}
                  </a-tag>
                </div>
                <div v-if="traceDrawer.selectedNode.error_message" class="mango-trace-step__error">
                  {{ traceDrawer.selectedNode.error_message }}
                </div>
                <div class="mango-trace-node-detail__meta">
                  <span
                    >引用：{{ traceDrawer.selectedNode.detail_ref_type || '-' }} /
                    {{ traceDrawer.selectedNode.detail_ref_id || '-' }}</span
                  >
                </div>
                <pre class="mango-trace-json">{{
                  formatTraceSummary(traceDrawer.selectedNode.summary)
                }}</pre>
              </template>
              <div v-else class="mango-trace-empty">选择节点查看摘要</div>
            </div>
          </div>
        </div>
      </mango-panel-spin>
    </a-drawer>

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
      :target-id="reportInfo.id || reportId"
      :title="`${reportTitle} · 排查结果`"
    />
  </div>
</template>

<script lang="ts" setup>
  import {
    computed,
    onActivated,
    onDeactivated,
    onMounted,
    onUnmounted,
    reactive,
    ref,
  } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import {
    downloadSystemTestSuiteDetailsApiExport,
    getSystemTestSuiteDetailsApiExportStatus,
    getSystemTestSuiteDetailsExecutionTrace,
    getSystemTestSuiteDetailsFailureReasonsShare,
    getSystemTestSuiteDetailsResultOptionsShare,
    getSystemTestSuiteDetailsResultShare,
    getSystemTestSuiteDetailsRetry,
    getSystemTestSuiteDetailsShare,
    getSystemTestSuiteDetailsSummaryShare,
    postSystemTestSuiteDetailsApiExport,
  } from '@/api/system/test_sute_details'
  import { getSystemTestSuiteShare } from '@/api/system/test_suite'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePageData } from '@/store/page-data'
  import { useUserStoreContext } from '@/store/modules/user'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import ElementTestReport from '@/components/reports/ElementTestReport.vue'
  import ApiTestReport from '@/components/reports/ApiTestReport.vue'
  import PytestTestReport from '@/components/reports/PytestTestReport.vue'
  import ExecutionHistoryList from '@/components/business/ExecutionHistoryList.vue'
  import type { ExecutionHistoryItem } from '@/components/business/execution-history'
  import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ApiCaseDetails from '@/views/apitest/case/details/index.vue'
  import UiCaseDetails from '@/views/uitest/case/details/index.vue'
  import UiCaseTable from './UiCaseTable.vue'
  import ApiCaseTable from './ApiCaseTable.vue'
  import PytestCaseTable from './PytestCaseTable.vue'
  import EvaluationCaseTable from './EvaluationCaseTable.vue'
  import StatusChart from '@/components/chart/StatusChart.vue'
  import DiagnosticMarkdownDrawer from '@/components/reports/DiagnosticMarkdownDrawer.vue'

  const route = useRoute()
  const enumStore = useEnum()
  const pageData: any = usePageData()
  const userStore = useUserStoreContext()
  const isShareReportRoute = computed(() => route.path === '/report/details')

  if (!pageData.record) {
    pageData.setRecord({})
  }

  const reportInfo = ref<any>({})
  const canRetry = computed(() => !!userStore.token && !reportInfo.value.retained_summary && !summary.value.evaluation_count)
  const diagnosticDrawer = reactive({ visible: false })
  const summary = ref<any>({})
  const cases = ref<any[]>([])
  const activeType = ref('0')
  const caseStatus = ref<number | 'all'>('all')
  const caseKeyword = ref('')
  const lastSearchedCaseKeyword = ref('')
  const summaryLoading = ref(false)
  const failureReasonLoading = ref(false)
  const failureReasonSummary = ref<any>({
    items: [],
    category_count: 0,
    failure_count: 0,
  })
  const caseLoading = ref(false)
  const detailLoading = ref(false)
  const detailHistoryLoading = ref(false)
  const drawerVisible = ref(false)
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
  const selectedCase = ref<any>({})
  const selectedCaseSourceRecord = ref<any>({})
  const detailResultOptions = ref<any[]>([])
  const selectedResultId = ref<any>('')
  const detailHistoryItems = computed<ExecutionHistoryItem[]>(() =>
    detailResultOptions.value.map((item) => ({
      id: item.id,
      title: detailAttemptTitle(item),
      statusText: item.status_text || '未知',
      statusColor: detailResultStatusColor(item.status_text),
      time: item.update_time || item.create_time || '-',
      actor: item.trigger_user_name || '',
      latest: Boolean(item.is_case_latest),
      sourceText: item.source_scope_name || 'Case执行',
      sourceColor: detailHistorySourceColor(item.source_scope),
    }))
  )
  const caseDetailDrawer = reactive({
    visible: false,
    caseId: '',
    caseType: -1,
  })
  const apiExport = reactive({
    loading: false,
    taskId: '',
  })
  const isPolling = ref(false)
  const pollingTimer = ref<ReturnType<typeof setInterval> | null>(null)
  const reportPageActive = ref(true)
  const apiExportTimer = ref<ReturnType<typeof setTimeout> | null>(null)
  const traceDrawer = reactive({
    visible: false,
    loading: false,
    trace: null as any,
    steps: [] as any[],
    nodes: [] as any[],
    edges: [] as any[],
    selectedNode: null as any,
    expandedNodeIds: [] as string[],
  })
  const traceNodeMap = computed(
    () => new Map(traceDrawer.nodes.map((node: any) => [String(node.id), node]))
  )
  const visibleTraceNodes = computed(() =>
    traceDrawer.nodes.filter((node: any) => {
      let parent = node.parent_step_id ? traceNodeMap.value.get(String(node.parent_step_id)) : null
      while (parent) {
        if (
          parent.step_type === 'retry_round' &&
          !traceDrawer.expandedNodeIds.includes(String(parent.id))
        ) {
          return false
        }
        parent = parent.parent_step_id
          ? traceNodeMap.value.get(String(parent.parent_step_id))
          : null
      }
      return true
    })
  )

  const pagination = reactive({
    page: 1,
    pageSize: 20,
    total: 0,
  })

  // 报告页可能被 keep-alive 缓存，不能让其他页面的 route.query.id 覆盖当前报告 ID。
  const reportId = ref(String(route.query.id || pageData.record?.id || ''))
  const totalCount = computed(() => summary.value.count || 0)
  const excludedFilter = ref('all')
  const failRatio = computed(() => ratio(summary.value.fail_count, totalCount.value))
  const passRate = computed(() => !totalCount.value && summary.value.excluded_count ? 100 : ratio(summary.value.success_count, totalCount.value))
  const reportExecutionName = computed(
    () => reportInfo.value.tasks?.name || reportInfo.value.execution_name || ''
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
  const caseStatusOptions: Array<{ label: string; value: number | 'all' }> = [
    { label: '全部', value: 'all' },
    { label: '失败', value: 0 },
    { label: '成功', value: 1 },
    { label: '警告', value: 4 },
    { label: '进行中', value: 3 },
    { label: '待开始', value: 2 },
  ]
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

  function statusColor(status: number) {
    return enumStore.status_colors?.[status] || 'gray'
  }

  function statusText(status: number) {
    return enumStore.task_status?.[status]?.title || '未知'
  }

  function detailAttemptTitle(item: any) {
    const attemptNo = Number(item?.attempt_no || 0)
    if (attemptNo <= 1) return '首次执行'
    return `第${attemptNo - 1}次重试`
  }

  function detailResultStatusColor(statusTextValue: unknown) {
    const value = String(statusTextValue || '')
    if (value.includes('成功') || value.includes('通过')) return 'green'
    if (value.includes('失败')) return 'red'
    if (value.includes('警告')) return 'orange'
    if (value.includes('执行中') || value.includes('进行中')) return 'arcoblue'
    return 'gray'
  }

  function detailHistorySourceColor(sourceScope: unknown) {
    if (sourceScope === 'current_report') return 'arcoblue'
    if (sourceScope === 'other_report') return 'purple'
    return 'gray'
  }

  function envText(env: number) {
    return enumStore.environment_type.find((item) => String(item.key) === String(env))?.title || '-'
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

  async function showDetails(record: any) {
    if (record?.__isWarningRow) {
      Message.warning('该用例前置步骤失败，未被执行')
      return
    }
    const detailId = record?.test_suite_detail_id || record?.__caseSourceId
    if (!detailId) return
    if (Number(record?.case_type ?? activeType.value) === 1) {
      const caseId = record?.__caseId || record?.case_id
      const historyTargetName =
        record?.__caseName || record?.name || (caseId ? `Case ${caseId}` : `明细 ${detailId}`)
      apiHistoryDrawer.title = `用例执行历史：${historyTargetName}`
      apiHistoryDrawer.caseId = ''
      apiHistoryDrawer.testSuiteDetailId = detailId
      apiHistoryDrawer.preferredParameterId = record?.parameter_id
      apiHistoryDrawer.visible = true
      return
    }
    selectedCaseSourceRecord.value = record
    detailResultOptions.value = []
    selectedResultId.value = ''
    selectedCase.value = {
      ...record,
      case_type: record?.case_type ?? Number(activeType.value),
    }
    drawerVisible.value = true
    detailLoading.value = true
    detailHistoryLoading.value = true
    try {
      const [optionsRes, detailRes] = await Promise.all([
        getSystemTestSuiteDetailsResultOptionsShare(detailId),
        getSystemTestSuiteDetailsResultShare(detailId),
      ])
      detailResultOptions.value = optionsRes.data || []
      selectedResultId.value = detailResultOptions.value[0]?.id || ''
      const res = detailRes
      selectedCase.value = buildFullDetailRecord(record, res.data || {})
    } catch (error: any) {
      Message.error(error?.msg || error?.message || '加载详细报告失败')
    } finally {
      detailLoading.value = false
      detailHistoryLoading.value = false
    }
  }

  function showCaseHistory(record: any) {
    const caseId = record?.__caseId || record?.case_id
    if (!caseId || caseId === '-') {
      Message.error('当前报告明细缺少 API Case ID，无法查询历史报告')
      return
    }
    apiHistoryDrawer.title = `用例执行历史：${record?.__caseName || record?.name || `Case ${caseId}`}`
    apiHistoryDrawer.caseId = caseId
    apiHistoryDrawer.testSuiteDetailId = ''
    apiHistoryDrawer.preferredParameterId = undefined
    apiHistoryDrawer.visible = true
  }

  async function changeDetailResult(resultId: any) {
    const record = selectedCaseSourceRecord.value || {}
    const detailId = record?.test_suite_detail_id || record?.__caseSourceId
    if (!detailId || !resultId) return
    selectedResultId.value = resultId
    detailLoading.value = true
    try {
      const res = await getSystemTestSuiteDetailsResultShare(detailId, resultId)
      selectedCase.value = buildFullDetailRecord(record, res.data || {})
    } catch (error: any) {
      Message.error(error?.msg || error?.message || '切换执行记录失败')
    } finally {
      detailLoading.value = false
    }
  }

  function buildFullDetailRecord(sourceRecord: any, detailRecord: any) {
    const caseType = Number(sourceRecord?.case_type ?? detailRecord?.type ?? activeType.value)
    const children = Array.isArray(detailRecord?.children) ? detailRecord.children : []
    const matched = findMatchedDetailChild(sourceRecord, children) || children[0] || detailRecord
    const baseRecord = {
      ...matched,
      case_type: caseType,
      name: matched?.name || sourceRecord?.name || detailRecord?.case_name || detailRecord?.name,
      status: matched?.status ?? sourceRecord?.status ?? detailRecord?.status,
      error_message:
        matched?.error_message ||
        matched?.statusDetails?.message ||
        sourceRecord?.error_message ||
        detailRecord?.error_message,
      test_suite_detail_id: detailRecord?.id || sourceRecord?.test_suite_detail_id,
      __caseSourceId: detailRecord?.id || sourceRecord?.__caseSourceId,
    }
    if (caseType === 0) {
      return {
        ...baseRecord,
        test_time: baseRecord?.test_time || detailRecord?.test_time,
        test_object: baseRecord?.test_object || detailRecord?.test_object,
        video_path: baseRecord?.video_path || detailRecord?.video_path,
        cache_data: baseRecord?.cache_data || detailRecord?.cache_data,
        data_factory_cache_data:
          baseRecord?.data_factory_cache_data || detailRecord?.data_factory_cache_data,
        element_result_list: [baseRecord],
        children: [baseRecord],
      }
    }
    return baseRecord
  }

  function findMatchedDetailChild(sourceRecord: any, children: any[]) {
    if (!children.length) return null
    const parameterId = sourceRecord?.parameter_id
    if (parameterId !== undefined && parameterId !== null) {
      const item = children.find((child) => String(child?.parameter_id) === String(parameterId))
      if (item) return item
    }
    const id = sourceRecord?.id
    if (id !== undefined && id !== null) {
      const item = children.find((child) => String(child?.id) === String(id))
      if (item) return item
    }
    const name = sourceRecord?.name
    if (name) {
      const item = children.find((child) => String(child?.name || '') === String(name))
      if (item) return item
    }
    return null
  }

  async function showExecutionTrace(query: {
    result_id?: number | string
    trace_id?: string
    test_suite_detail_id?: number | string
    case_id?: number | string
  }) {
    if (!query.result_id && !query.trace_id && !query.test_suite_detail_id && !query.case_id) return
    traceDrawer.visible = true
    traceDrawer.loading = true
    traceDrawer.trace = null
    traceDrawer.steps = []
    traceDrawer.nodes = []
    traceDrawer.edges = []
    traceDrawer.selectedNode = null
    traceDrawer.expandedNodeIds = []
    try {
      const res = await getSystemTestSuiteDetailsExecutionTrace({
        ...query,
        include_list: true,
      })
      traceDrawer.trace = res.data?.trace || null
      traceDrawer.steps = res.data?.steps || []
      traceDrawer.nodes = res.data?.nodes || []
      traceDrawer.edges = res.data?.edges || []
      traceDrawer.selectedNode =
        traceDrawer.nodes.find((node: any) => Number(node.status) === 0) ||
        traceDrawer.nodes[0] ||
        null
      if (!traceDrawer.trace) {
        Message.warning('本次执行没有链路记录，请重试该 API 用例后再查看')
      }
    } catch (error: any) {
      Message.error(error?.msg || error?.message || '执行链路查询失败')
    } finally {
      traceDrawer.loading = false
    }
  }

  function traceStatusText(status: number) {
    if (Number(status) === 1) return '通过'
    if (Number(status) === 0) return '失败'
    if (Number(status) === 3) return '进行中'
    if (Number(status) === 5) return '跳过'
    if (Number(status) === 4) return '清理失败'
    return '待开始'
  }

  function traceStatusColor(status: number) {
    return enumStore.status_colors?.[Number(status)] || 'gray'
  }

  function selectTraceNode(node: any) {
    traceDrawer.selectedNode = node
  }

  function traceNodeHasChildren(node: any) {
    return (
      node.step_type === 'retry_round' &&
      traceDrawer.nodes.some((item: any) => String(item.parent_step_id || '') === String(node.id))
    )
  }

  function traceNodeExpanded(node: any) {
    return traceDrawer.expandedNodeIds.includes(String(node.id))
  }

  function toggleTraceNode(node: any) {
    if (!traceNodeHasChildren(node)) return
    const id = String(node.id)
    if (traceNodeExpanded(node)) {
      traceDrawer.expandedNodeIds = traceDrawer.expandedNodeIds.filter((item) => item !== id)
      if (String(traceDrawer.selectedNode?.parent_step_id || '') === id) {
        traceDrawer.selectedNode = node
      }
    } else {
      traceDrawer.expandedNodeIds = [...traceDrawer.expandedNodeIds, id]
    }
  }

  function traceNodeDepth(node: any) {
    let depth = 0
    let parent = node.parent_step_id ? traceNodeMap.value.get(String(node.parent_step_id)) : null
    while (parent && depth < 3) {
      depth += 1
      parent = parent.parent_step_id ? traceNodeMap.value.get(String(parent.parent_step_id)) : null
    }
    return depth
  }

  function traceSourceText(sourceType: number) {
    const sourceMap: Record<number, string> = {
      1: '测试报告',
      2: '定时任务',
      3: 'MCP',
      4: '单 Case 执行',
      5: '调试执行',
      6: '其他',
    }
    return sourceMap[Number(sourceType)] || '未知'
  }

  function traceNodeClass(status: number) {
    if (Number(status) === 1) return 'is-success'
    if (Number(status) === 0) return 'is-fail'
    if (Number(status) === 3) return 'is-running'
    if (Number(status) === 5) return 'is-skip'
    if (Number(status) === 4) return 'is-warning'
    return 'is-pending'
  }

  function formatTraceSummary(value: any) {
    return JSON.stringify(value || {}, null, 2)
  }

  function openCaseDetail(record: any) {
    const caseId = record?.__caseId || record?.case_id || record?.id
    if (!caseId || caseId === '-') {
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
    const data: any = {
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

  async function refreshDisposition() {
    await Promise.all([loadSummary(), loadReportInfo(), refreshLoadedCases()])
  }

  async function loadFailureReasons() {
    if (!reportId.value || failureReasonLoading.value) return
    failureReasonLoading.value = true
    try {
      const res = await getSystemTestSuiteDetailsFailureReasonsShare(reportId.value)
      failureReasonSummary.value = {
        items: res.data?.items || [],
        category_count: Number(res.data?.category_count || 0),
        failure_count: Number(res.data?.failure_count || 0),
      }
    } catch (error: any) {
      Message.error(error?.msg || error?.message || '加载失败原因统计失败')
    } finally {
      failureReasonLoading.value = false
    }
  }

  async function loadCases(reset = false) {
    if (!reportId.value || caseLoading.value) return
    if (reset) {
      cases.value = []
      pagination.page = 1
      pagination.total = 0
    }

    caseLoading.value = true
    try {
      const res = await getSystemTestSuiteDetailsShare(buildCaseQuery())
      const list = Array.isArray(res.data) ? res.data : []
      cases.value = list
      pagination.total = getTotal(res)
    } catch (error: any) {
      Message.error(error?.msg || '加载报告失败')
    } finally {
      caseLoading.value = false
    }
  }

  function reloadCases() {
    loadCases(true)
  }

  function searchCases() {
    const normalizedKeyword = caseKeyword.value.trim()
    if (normalizedKeyword === lastSearchedCaseKeyword.value) return
    lastSearchedCaseKeyword.value = normalizedKeyword
    reloadCases()
  }

  function searchCasesOnBlur() {
    window.setTimeout(searchCases, 0)
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

  async function refreshLoadedCases() {
    if (!reportId.value || caseLoading.value) return
    const currentPage = pagination.page
    caseLoading.value = true
    try {
      const query = buildCaseQuery()
      const res = await getSystemTestSuiteDetailsShare(query)
      const list = Array.isArray(res.data) ? res.data : []
      cases.value = list
      pagination.total = getTotal(res)
    } catch (error) {
      pagination.page = currentPage
      throw error
    } finally {
      caseLoading.value = false
    }
  }

  function handlePolling() {
    if (!reportPageActive.value) {
      stopPolling()
      return
    }
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
    if (!reportPageActive.value || !reportId.value) return
    const pollingReportId = reportId.value
    isPolling.value = true
    pollingTimer.value = setInterval(async () => {
      if (!reportPageActive.value || reportId.value !== pollingReportId) {
        stopPolling()
        return
      }
      await loadSummary()
      if (!reportPageActive.value || reportId.value !== pollingReportId) return
      await refreshLoadedCases()
      const hasInProgress =
        (summary.value.stay_begin_count || 0) > 0 || (summary.value.proceed_count || 0) > 0
      if (!hasInProgress) {
        await loadFailureReasons()
      }
    }, 5000)
  }

  function stopPolling() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
    isPolling.value = false
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

  async function startApiExport() {
    if (!reportId.value || apiExport.loading) return
    apiExport.loading = true
    try {
      const res = await postSystemTestSuiteDetailsApiExport({
        test_suite_id: reportId.value,
        status: caseStatus.value,
      })
      apiExport.taskId = res.data?.task_id
      if (!apiExport.taskId) {
        throw new Error('导出任务创建失败')
      }
      Message.success('导出任务已创建，完成后将自动下载')
      pollApiExport()
    } catch (error: any) {
      apiExport.loading = false
      Message.error(error?.message || '导出任务创建失败')
    }
  }

  async function pollApiExport() {
    if (!apiExport.taskId) {
      apiExport.loading = false
      return
    }
    try {
      const res = await getSystemTestSuiteDetailsApiExportStatus(apiExport.taskId)
      const task = res.data || {}
      if (task.status === 'success') {
        await downloadApiExport(task.file_name)
        Message.success('API报告导出完成')
        apiExport.loading = false
        apiExport.taskId = ''
        return
      }
      if (task.status === 'fail') {
        Message.error(task.message || 'API报告导出失败')
        apiExport.loading = false
        apiExport.taskId = ''
        return
      }
      apiExportTimer.value = setTimeout(pollApiExport, 1500)
    } catch (error: any) {
      apiExport.loading = false
      Message.error(error?.message || '查询导出任务失败')
    }
  }

  async function downloadApiExport(fileName?: string) {
    const res: any = await downloadSystemTestSuiteDetailsApiExport(apiExport.taskId)
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = fileName || `API测试报告_${reportId.value}_${Date.now()}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  onMounted(async () => {
    if (!enumStore.task_status?.length) {
      enumStore.getEnumShare()
    }
    await loadReportInfo()
    await loadSummary()
    void loadFailureReasons()
    const [firstVisibleType] = visibleTypeTabs.value
    if (firstVisibleType) {
      activeType.value = firstVisibleType.key
    }
    await loadCases(true)
  })

  onActivated(() => {
    reportPageActive.value = true
    handlePolling()
  })

  onDeactivated(() => {
    reportPageActive.value = false
    stopPolling()
  })

  onUnmounted(() => {
    reportPageActive.value = false
    stopPolling()
    if (apiExportTimer.value) {
      clearTimeout(apiExportTimer.value)
      apiExportTimer.value = null
    }
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

  .report-detail-empty {
    min-height: 180px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: var(--m-muted);
    font-size: 14px;
  }

  .report-detail-empty__alert {
    width: min(720px, calc(100% - 32px));
  }

  .report-detail-spin {
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

  .report-detail-spin :deep(> .mango-panel-spin__content) {
    box-sizing: border-box;
    min-height: 100%;
    padding: var(--m-card-padding);
    overflow: visible;
  }

  .report-detail-spin--api {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .report-detail-spin--api :deep(> .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-report-result-history {
    display: grid;
    height: 100%;
    min-width: 0;
    min-height: 0;
    grid-template-columns: 300px minmax(0, 1fr);
    gap: 12px;
  }

  :deep(.mango-report-result-drawer .arco-drawer-body) {
    padding: var(--m-page-gap);
    overflow: hidden;
    background: var(--m-bg);
  }

  @media (max-width: 900px) {
    :deep(.mango-report-result-drawer .arco-drawer) {
      width: 92vw !important;
    }

    .mango-report-result-history {
      grid-template-columns: 1fr;
      grid-template-rows: minmax(180px, 28%) minmax(0, 1fr);
    }
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
    grid-template-columns: repeat(5, minmax(0, 1fr)) minmax(0, 1.4fr);
    align-items: center;
    gap: var(--m-space-md) var(--m-space-lg);
    margin: var(--m-space-md) 0 0;
    padding: var(--m-space-md) 0 0;
    border-top: 1px solid var(--m-border);
  }

  .meta-strip.has-task-name {
    grid-template-columns: minmax(0, 1.6fr) repeat(5, minmax(0, 1fr)) minmax(0, 1.4fr);
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

  @container mango-report-detail (max-width: 68rem) {
    .meta-strip,
    .meta-strip.has-task-name {
      grid-template-columns: repeat(3, minmax(0, 1fr));
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
