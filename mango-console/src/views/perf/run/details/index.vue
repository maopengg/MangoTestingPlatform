<template>
  <TableBody plain class="mango-detail-workbench-page mango-perf-page">
    <template #header>
      <TableHeader :title="`性能运行 #${id} / ${overview.name || ''}`">
        <template #header-extra>
          <a-space>
            <a-button class="mango-back-button" size="small" @click="router.back()">返回</a-button>
            <a-button size="small" :loading="refreshing" @click="refreshAll">刷新</a-button>
            <a-button v-permission="'perf.run:export'" size="small" :loading="exporting" @click="exportReport">导出报告</a-button>
            <a-button v-permission="'perf.run:execute'" v-if="!activeRunStatuses.has(overview.status)" size="small" @click="rerun"
              >按当前配置重跑</a-button
            >
            <a-button v-permission="'perf.run:stop'"
              v-if="activeRunStatuses.has(overview.status)"
              status="danger"
              size="small"
              :loading="stopping"
              @click="stop"
              >停止运行</a-button
            >
            <a-button
              v-if="overview.verdict === 'passed'"
              size="small"
              :loading="baselineSaving"
              @click="baseline"
              >设为基线</a-button
            >
          </a-space>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <a-alert
        v-if="overview.error_message"
        type="error"
        class="mango-perf-run-error-alert"
        :title="overview.error_code ? `运行失败（${overview.error_code}）` : '运行失败'"
        >{{ overview.error_message }}</a-alert
      >
      <mango-panel-spin :loading="loading" class="mango-perf-detail-spin"
        ><div class="mango-detail-workbench mango-perf-run-workbench">
          <section
            class="mango-section-card mango-perf-run-summary"
            :class="`is-${overview.verdict}`"
          >
            <div class="mango-perf-run-conclusion">
              <span class="mango-perf-run-conclusion-mark">{{ conclusion.mark }}</span>
              <div>
                <span>本次性能测试结论</span>
                <h2>{{ conclusion.title }}</h2>
                <p>{{ conclusion.description }}</p>
              </div>
            </div>
            <div class="mango-perf-run-meta">
              <div
                ><span>测试环境</span
                ><strong>{{ overview.test_env_title || environmentTitle }}</strong></div
              >
              <div
                ><span>执行引擎</span
                ><strong
                  >{{ String(overview.engine || 'k6').toUpperCase() }}
                  {{ overview.engine_version || '' }}</strong
                ></div
              >
              <div
                ><span>实际耗时</span><strong>{{ actualDuration }}</strong></div
              >
              <div
                ><span>执行节点</span
                ><strong
                  >{{ overview.actual_node_count || 0 }} /
                  {{ overview.requested_node_count || 0 }}</strong
                ></div
              >
              <div
                ><span>开始时间</span
                ><strong>{{ overview.started_at || '-' }}</strong></div
              >
              <div
                ><span>结束时间</span
                ><strong>{{ overview.finished_at || '-' }}</strong></div
              >
            </div>
          </section>
          <section class="mango-perf-kpi-grid">
            <div class="mango-soft-panel" v-for="item in kpis" :key="item.label"
              ><span>{{ item.label }}</span
              ><strong>{{ item.value }}</strong
              ><small>{{ item.hint }}</small></div
            >
          </section>
          <section class="mango-section-card">
            <div class="mango-section-title">
              <div
                ><h2>客户端指标总览</h2
                ><p
                  >覆盖延迟分布、执行可靠性、客户端流量和发压端资源，未采集的指标显示为“-”。</p
                ></div
              >
            </div>
            <div class="mango-perf-metric-groups">
              <article
                v-for="group in clientMetricGroups"
                :key="group.title"
                class="mango-soft-panel mango-perf-metric-group"
              >
                <div class="mango-perf-metric-group-head"
                  ><strong>{{ group.title }}</strong
                  ><span>{{ group.description }}</span></div
                >
                <dl>
                  <div v-for="item in group.items" :key="item.label"
                    ><dt>{{ item.label }}</dt
                    ><dd>{{ item.value }}</dd></div
                  >
                </dl>
              </article>
            </div>
          </section>
          <section class="mango-section-card">
            <div class="mango-section-title mango-perf-chart-title">
              <div
                ><h2>客户端指标趋势</h2><p>吞吐、响应时间和实际负载均来自执行器客户端采样。</p></div
              >
              <span class="mango-perf-live-indicator"
                ><i></i
                >{{
                  activeRunStatuses.has(overview.status)
                    ? '每 2 秒刷新'
                    : `共 ${points.length} 个采样窗口`
                }}</span
              >
            </div>
            <div v-if="points.length" class="mango-perf-chart-grid">
              <div class="mango-soft-panel mango-perf-chart-panel"
                ><div><strong>吞吐与响应时间</strong><span>RPS / 平均响应时间</span></div
                ><div ref="chartRef" class="mango-perf-chart"></div
              ></div>
              <div class="mango-soft-panel mango-perf-chart-panel"
                ><div><strong>负载达成与失败</strong><span>目标用户 / 活跃用户 / 失败数</span></div
                ><div ref="loadChartRef" class="mango-perf-chart"></div
              ></div>
              <div
                v-if="hasGeneratorMetrics"
                class="mango-soft-panel mango-perf-chart-panel mango-perf-resource-chart-panel"
                ><div><strong>发压端资源</strong><span>CPU 峰值 / 内存占用</span></div
                ><div
                  ref="resourceChartRef"
                  class="mango-perf-chart mango-perf-resource-chart"
                ></div
              ></div>
            </div>
            <div v-else class="mango-empty-state">尚未收到客户端指标</div>
          </section>
          <section v-if="stages.length" class="mango-section-card">
            <div class="mango-section-title"
              ><div
                ><h2>负载阶段</h2><p>按执行顺序查看每个阶段的目标、达成情况和响应表现。</p></div
              ></div
            >
            <div class="mango-perf-stage-flow">
              <article
                v-for="(stage, index) in stages"
                :key="stage.id || stage.stage_key"
                class="mango-soft-panel mango-perf-stage-card"
              >
                <div class="mango-perf-stage-head"
                  ><span>{{ index + 1 }}</span
                  ><div
                    ><strong>{{ stage.stage_name }}</strong
                    ><small>{{ stage.duration_seconds }} 秒</small></div
                  ></div
                >
                <div class="mango-perf-stage-target"
                  ><span>目标 / 实际用户</span
                  ><strong
                    >{{ stage.target_load?.users ?? '-' }} /
                    {{ stage.actual_load?.users ?? '-' }}</strong
                  ></div
                >
                <div class="mango-perf-stage-stats"
                  ><span>{{ stage.rps }} RPS</span><span>P95 {{ stage.p95_ms }} ms</span
                  ><span>{{ stage.failure_count }} 失败</span></div
                >
              </article>
            </div>
          </section>
          <section class="mango-section-card"
            ><a-tabs v-model:active-key="activeTab" class="mango-tabs-nav-only">
              <a-tab-pane key="requests" :title="`请求统计 ${requests.length}`"
                ><RunRequestTable :rows="requests" :loading="!loading && detailLoading"
              /></a-tab-pane>
              <a-tab-pane key="nodes" :title="`执行节点 ${nodes.length}`"
                ><a-table
                  :columns="nodeColumns"
                  :data="nodes"
                  :loading="!loading && detailLoading"
                  :pagination="false"
                  :scroll="{ x: NODE_TABLE_SCROLL_X }"
                  ><template #columns
                    ><a-table-column v-for="column in nodeColumns" :key="column.key" v-bind="column"
                      ><template v-if="column.key === 'status'" #cell="{ record }"
                        ><a-tag :color="nodeStatusColor(record.status)" size="small">{{
                          nodeStatusTitle(record.status)
                        }}</a-tag></template>
                        <template v-else-if="column.key === 'capture'" #cell="{ record }">
                          <a-button v-permission="'perf.run:download'"
                            v-if="record.capture?.status === 'uploaded'"
                            size="mini"
                            type="text"
                            :loading="captureDownloadingNodeId === record.id"
                            @click="downloadCapture(record.id)"
                          >下载 CSV（{{ formatBytes(record.capture.bytes) }}）</a-button>
                          <span v-else :title="record.capture?.message || ''">{{ captureStatusText(record.capture?.status) }}</span>
                        </template>
                      ></a-table-column
                    ></template
                  ></a-table
                ></a-tab-pane
              >
              <a-tab-pane key="validity" :title="`有效性门禁 ${validity.length}`">
                <RunValidityGrid :rows="validity" />
              </a-tab-pane>
              <a-tab-pane key="thresholds" title="性能目标"
                ><div v-if="performanceGoalResults.length" class="mango-perf-goal-result"
                  ><div class="mango-perf-goal-result-head"
                    ><div
                      ><strong>本次性能目标</strong
                      ><span>P95、错误率、负载达成率必须同时通过</span></div
                    ><a-tag
                      :color="performanceGoalResults.every((item) => item.passed) ? 'green' : 'red'"
                      size="small"
                      >{{
                        performanceGoalResults.every((item) => item.passed) ? '已达标' : '未达标'
                      }}</a-tag
                    ></div
                  ><div class="mango-perf-goal-result-grid"
                    ><div
                      v-for="item in performanceGoalResults"
                      :key="item.metric"
                      class="mango-soft-panel mango-perf-goal-result-item"
                      ><span>{{ performanceGoalMetricTitle(item.metric) }}</span
                      ><strong>{{ formatGoalActual(item) }}</strong
                      ><small>目标 {{ item.operator }} {{ formatGoalExpected(item) }}</small
                      ><a-tag :color="item.passed ? 'green' : 'red'" size="small">{{
                        item.passed ? '通过' : '未通过'
                      }}</a-tag></div
                    ></div
                  ></div
                ><div v-else class="mango-empty-state">暂无性能目标判定结果</div></a-tab-pane
              >
              <a-tab-pane key="comparison" title="基线对比"
                ><a-alert
                  v-if="comparison.available && !comparison.same_snapshot"
                  type="warning"
                  class="mango-perf-compare-alert"
                  >当前运行与基线快照不同，对比结果仅供趋势参考。</a-alert
                ><RunComparisonTable
                  v-if="comparison.available"
                  :rows="comparison.metrics || []"
                  :loading="!loading && detailLoading"
                />
                ><div v-if="!comparison.available" class="mango-empty-state"
                  >尚未设置可用基线</div
                ></a-tab-pane
              >
              <a-tab-pane key="errors" :title="`错误 ${errors.length}`"
                ><div v-if="errors.length" class="mango-perf-error-list"
                  ><div v-for="item in errors" :key="item.id" class="mango-soft-panel"
                    ><div class="mango-perf-error-head"
                      ><strong>{{ item.error_type }} · {{ item.count }} 次</strong
                      ><span>影响 {{ item.node_count }} 个节点</span></div
                    ><span>{{ item.message_template }}</span
                    ><div v-if="item.samples?.length" class="mango-perf-error-sample"
                      ><small>样本响应</small
                      ><code
                        >{{ item.samples[0].response_status || '-' }} ·
                        {{ item.samples[0].response_excerpt || '无响应摘要' }}</code
                      ></div
                    ></div
                  ></div
                ><div v-else class="mango-empty-state">暂无错误</div></a-tab-pane
              >
            </a-tabs></section
          >
        </div></mango-panel-spin
      >
    </template>
  </TableBody>
</template>

<script setup lang="ts">
  import { Message, Modal } from '@arco-design/web-vue'
  import * as echarts from 'echarts'
  import { makeChartDensityAware } from '@/utils/chartDensity'
  import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import {
    exportPerfRun,
    getPerfRunComparison,
    getPerfRunErrors,
    getPerfRunMetrics,
    getPerfRunNodes,
    getPerfRunOverview,
    getPerfRunCaptureDownload,
    getPerfRunRequests,
    getPerfRunStages,
    getPerfRunThresholds,
    getPerfRunValidity,
    setPerfRunBaseline,
    stopPerfRun,
    subscribePerfRun,
    unsubscribePerfRun,
  } from '@/api/perf'
  import { activeRunStatuses } from '../../types'
  import { NODE_TABLE_SCROLL_X, nodeColumns } from './config'
  import RunComparisonTable from './components/RunComparisonTable.vue'
  import RunRequestTable from './components/RunRequestTable.vue'
  import RunValidityGrid from './components/RunValidityGrid.vue'
  const route = useRoute()
  const router = useRouter()
  const id = String(route.query.id || '')
  const loading = ref(false)
  const refreshing = ref(false)
  const detailLoading = ref(false)
  const stopping = ref(false)
  const baselineSaving = ref(false)
  const exporting = ref(false)
  const captureDownloadingNodeId = ref<number | null>(null)
  const activeTab = ref('requests')
  const chartRef = ref<HTMLElement>()
  const loadChartRef = ref<HTMLElement>()
  const resourceChartRef = ref<HTMLElement>()
  let chart: echarts.ECharts | null = null
  let loadChart: echarts.ECharts | null = null
  let resourceChart: echarts.ECharts | null = null
  let chartResizeObserver: ResizeObserver | undefined
  let timer: number | undefined
  let subscriptionTimer: number | undefined
  let cursor = ''
  let websocketTimer: number | undefined
  const overview = reactive<any>({ status: 'created', verdict: 'not_evaluated', summary: {} })
  const comparison = reactive<any>({ available: false, metrics: [] })
  const requests = ref<any[]>([])
  const stages = ref<any[]>([])
  const nodes = ref<any[]>([])
  const validity = ref<any[]>([])
  const thresholds = ref<any[]>([])
  const errors = ref<any[]>([])
  const points = ref<any[]>([])
  const conclusion = computed(() => {
    if (activeRunStatuses.has(overview.status))
      return {
        mark: 'LIVE',
        title: '测试正在运行',
        description: '客户端指标正在持续汇总，最终结论将在运行结束后生成。',
      }
    if (overview.verdict === 'passed')
      return {
        mark: 'PASS',
        title: '性能目标已达成',
        description: '运行有效，且性能目标中的三项客户端指标全部通过。',
      }
    if (overview.verdict === 'failed')
      return {
        mark: 'FAIL',
        title: '性能目标未达成',
        description: '运行数据有效，但性能目标中至少一项客户端指标未通过，请查看目标和请求统计。',
      }
    if (overview.verdict === 'invalid')
      return {
        mark: 'INVALID',
        title: '测试结果无效',
        description: '发压端、负载达成或指标完整性未满足要求，本次结果不适合作为性能结论。',
      }
    return {
      mark: 'WAIT',
      title: '尚未生成结论',
      description: '运行尚未完成或没有足够数据进行结果判定。',
    }
  })
  const environmentTitle = computed(() =>
    Number(overview.test_env) === 2
      ? '生产环境'
      : Number(overview.test_env) === 1
      ? '测试环境'
      : '开发环境'
  )
  const actualDuration = computed(() => {
    if (!overview.started_at) return '-'
    const start = new Date(String(overview.started_at).replace(' ', 'T')).getTime()
    const end = overview.finished_at
      ? new Date(String(overview.finished_at).replace(' ', 'T')).getTime()
      : Date.now()
    if (!Number.isFinite(start) || !Number.isFinite(end)) return '-'
    const seconds = Math.max(0, Math.round((end - start) / 1000))
    return formatDuration(seconds)
  })
  const sampledSummary = computed(() => {
    const result = {
      request_count: 0,
      failure_count: 0,
      response_time_sum_ms: 0,
      iteration_count: 0,
      dropped_count: 0,
      bytes_sent: 0,
      bytes_received: 0,
      connection_count: 0,
      connect_error_count: 0,
      min_ms: undefined as number | undefined,
      max_ms: undefined as number | undefined,
      max_rps: 0,
      actual_peak_concurrency: 0,
      peak_generator_cpu_percent: undefined as number | undefined,
      peak_generator_memory_bytes: undefined as number | undefined,
      peak_event_loop_lag_ms: undefined as number | undefined,
      timing_weighted_sums: {} as Record<string, number>,
      timing_weights: {} as Record<string, number>,
      duration_seconds: 0,
    }
    points.value.forEach((item) => {
      const requests = Number(item.request_count || 0)
      const windowSeconds = Number(item.window_seconds || 1)
      result.request_count += requests
      result.failure_count += Number(item.failure_count || 0)
      result.response_time_sum_ms += Number(item.response_time_sum_ms || 0)
      result.iteration_count += Number(item.iteration_count || 0)
      result.dropped_count += Number(item.dropped_count || 0)
      result.bytes_sent += Number(item.bytes_sent || 0)
      result.bytes_received += Number(item.bytes_received || 0)
      result.connection_count += Number(item.connection_count || 0)
      result.connect_error_count += Number(item.connect_error_count || 0)
      Object.entries(item.timing_breakdown || {}).forEach(([field, value]) => {
        if (value === null || value === undefined || !requests) return
        result.timing_weighted_sums[field] =
          Number(result.timing_weighted_sums[field] || 0) + Number(value) * requests
        result.timing_weights[field] = Number(result.timing_weights[field] || 0) + requests
      })
      result.duration_seconds += windowSeconds
      result.max_rps = Math.max(result.max_rps, requests / windowSeconds)
      result.actual_peak_concurrency = Math.max(
        result.actual_peak_concurrency,
        Number(item.actual_load?.users || 0)
      )
      if (item.min_response_time_ms !== null && item.min_response_time_ms !== undefined)
        result.min_ms =
          result.min_ms === undefined
            ? Number(item.min_response_time_ms)
            : Math.min(result.min_ms, Number(item.min_response_time_ms))
      if (item.max_response_time_ms !== null && item.max_response_time_ms !== undefined)
        result.max_ms = Math.max(result.max_ms || 0, Number(item.max_response_time_ms))
      if (item.generator_metrics?.cpu_percent != null)
        result.peak_generator_cpu_percent = Math.max(
          result.peak_generator_cpu_percent || 0,
          Number(item.generator_metrics.cpu_percent)
        )
      if (item.generator_metrics?.memory_bytes != null)
        result.peak_generator_memory_bytes = Math.max(
          result.peak_generator_memory_bytes || 0,
          Number(item.generator_metrics.memory_bytes)
        )
      if (item.generator_metrics?.event_loop_lag_ms != null)
        result.peak_event_loop_lag_ms = Math.max(
          result.peak_event_loop_lag_ms || 0,
          Number(item.generator_metrics.event_loop_lag_ms)
        )
    })
    return {
      ...result,
      avg_ms: result.request_count ? result.response_time_sum_ms / result.request_count : undefined,
      rps: result.duration_seconds ? result.request_count / result.duration_seconds : undefined,
      timing_breakdown: Object.fromEntries(
        Object.entries(result.timing_weights).map(([field, weight]) => [
          field,
          weight ? result.timing_weighted_sums[field] / weight : undefined,
        ])
      ),
    }
  })
  function summaryValue(key: string) {
    const globalRequestSummary = requests.value.find((item) => !item.step_key)
    return (
      overview.summary?.[key] ?? globalRequestSummary?.[key] ?? (sampledSummary.value as any)[key]
    )
  }
  function timingValue(field: string) {
    return (
      overview.summary?.timing_breakdown?.[field] ?? sampledSummary.value.timing_breakdown[field]
    )
  }
  const hasGeneratorMetrics = computed(() =>
    points.value.some(
      (item) =>
        item.generator_metrics?.cpu_percent != null || item.generator_metrics?.memory_bytes != null
    )
  )
  const kpis = computed(() => {
    const requestCount = Number(summaryValue('request_count') || 0)
    const failureCount = Number(summaryValue('failure_count') || 0)
    return [
      {
        label: '请求总数',
        value: formatNumber(requestCount),
        hint: `${formatNumber(summaryValue('iteration_count'))} 次业务迭代`,
      },
      {
        label: '平均吞吐',
        value: formatRps(summaryValue('rps')),
        hint: `峰值 ${formatRps(summaryValue('max_rps') ?? overview.summary?.actual_peak_rps)}`,
      },
      {
        label: '成功率',
        value: requestCount ? formatPercent(1 - ratio(failureCount, requestCount)) : '-',
        hint: `${formatNumber(failureCount)} 次失败`,
      },
      {
        label: '平均响应时间',
        value: formatMs(summaryValue('avg_ms')),
        hint: `P50 ${formatMs(summaryValue('p50_ms'))}`,
      },
      {
        label: 'P95 响应时间',
        value: formatMs(summaryValue('p95_ms')),
        hint: `P90 ${formatMs(summaryValue('p90_ms'))}`,
      },
      {
        label: 'P99 响应时间',
        value: formatMs(summaryValue('p99_ms')),
        hint: `最大 ${formatMs(summaryValue('max_ms'))}`,
      },
      {
        label: '实际峰值并发',
        value: formatNumber(summaryValue('actual_peak_concurrency')),
        hint: `目标 ${formatNumber(overview.peak_target_users)} 用户`,
      },
      {
        label: '丢弃迭代',
        value: formatNumber(summaryValue('dropped_count')),
        hint: `丢弃率 ${formatPercent(
          ratio(summaryValue('dropped_count'), summaryValue('iteration_count'))
        )}`,
      },
    ]
  })
  const clientMetricGroups = computed(() => {
    const requestCount = Number(summaryValue('request_count') || 0)
    const failureCount = Number(summaryValue('failure_count') || 0)
    return [
      {
        title: '延迟分布',
        description: '客户端端到端耗时',
        items: [
          { label: '最小响应时间', value: formatMs(summaryValue('min_ms')) },
          { label: 'P50 响应时间', value: formatMs(summaryValue('p50_ms')) },
          { label: 'P90 响应时间', value: formatMs(summaryValue('p90_ms')) },
          { label: '最大响应时间', value: formatMs(summaryValue('max_ms')) },
        ],
      },
      {
        title: '执行可靠性',
        description: '请求、连接和迭代',
        items: [
          { label: '成功请求', value: formatNumber(Math.max(0, requestCount - failureCount)) },
          { label: '失败请求', value: formatNumber(failureCount) },
          {
            label: '错误率',
            value: requestCount ? formatPercent(ratio(failureCount, requestCount)) : '-',
          },
          { label: '完成迭代', value: formatNumber(summaryValue('iteration_count')) },
          { label: '丢弃迭代', value: formatNumber(summaryValue('dropped_count')) },
          {
            label: '迭代丢弃率',
            value: formatPercent(
              ratio(summaryValue('dropped_count'), summaryValue('iteration_count'))
            ),
          },
        ],
      },
      {
        title: '网络分段',
        description: '客户端连接与传输阶段',
        items: [
          { label: '新建连接', value: formatNumber(summaryValue('connection_count')) },
          { label: '连接错误', value: formatNumber(summaryValue('connect_error_count')) },
          { label: 'TCP 连接', value: formatMs(timingValue('connect_ms')) },
          { label: 'TLS 握手', value: formatMs(timingValue('tls_ms')) },
          { label: '等待首字节', value: formatMs(timingValue('ttfb_ms')) },
          { label: '响应下载', value: formatMs(timingValue('download_ms')) },
        ],
      },
      {
        title: '客户端流量',
        description: '执行器实际收发',
        items: [
          { label: '发送数据', value: formatBytes(summaryValue('bytes_sent')) },
          { label: '接收数据', value: formatBytes(summaryValue('bytes_received')) },
          { label: '平均吞吐', value: formatRps(summaryValue('rps')) },
          {
            label: '峰值吞吐',
            value: formatRps(summaryValue('max_rps') ?? overview.summary?.actual_peak_rps),
          },
        ],
      },
      {
        title: '发压端健康度',
        description: '判断压测结果可信度',
        items: [
          {
            label: 'CPU 峰值',
            value: formatOptionalPercent(summaryValue('peak_generator_cpu_percent')),
          },
          { label: '内存峰值', value: formatBytes(summaryValue('peak_generator_memory_bytes')) },
          { label: '事件循环延迟', value: formatMs(summaryValue('peak_event_loop_lag_ms')) },
          { label: '指标采样窗口', value: `${formatNumber(points.value.length)} 个` },
        ],
      },
    ]
  })
  const performanceGoalResults = computed(() =>
    ['p95_ms', 'error_rate', 'load_achievement_rate']
      .map((metric) => thresholds.value.find((item) => item.metric === metric))
      .filter(Boolean)
  )
  function css(name: string) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  }
  function formatNumber(value: unknown, digits = 0) {
    if (value === null || value === undefined || value === '') return '-'
    return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(Number(value))
  }
  function ratio(numerator: unknown, denominator: unknown) {
    return Number(denominator || 0) ? Number(numerator || 0) / Number(denominator) : 0
  }
  function formatPercent(value: unknown) {
    return `${(Number(value || 0) * 100).toFixed(2)}%`
  }
  function formatMs(value: unknown) {
    return value === null || value === undefined || value === ''
      ? '-'
      : `${formatNumber(value, 2)} ms`
  }
  function formatRps(value: unknown) {
    return value === null || value === undefined || value === ''
      ? '-'
      : `${formatNumber(value, 2)} RPS`
  }
  function formatOptionalPercent(value: unknown) {
    return value === null || value === undefined || value === ''
      ? '-'
      : `${formatNumber(value, 2)}%`
  }
  function formatBytes(value: unknown) {
    if (value === null || value === undefined || value === '') return '-'
    const bytes = Number(value)
    if (!Number.isFinite(bytes)) return '-'
    if (bytes < 1024) return `${formatNumber(bytes)} B`
    if (bytes < 1024 ** 2) return `${formatNumber(bytes / 1024, 2)} KB`
    if (bytes < 1024 ** 3) return `${formatNumber(bytes / 1024 ** 2, 2)} MB`
    return `${formatNumber(bytes / 1024 ** 3, 2)} GB`
  }
  function captureStatusText(status: string | undefined) {
    return ({ disabled: '未开启', too_large: '超过 100 MB，未上传', upload_failed: '上传失败', failed: '生成失败', ready: '待上传' } as Record<string, string>)[status || ''] || (activeRunStatuses.has(overview.status) ? '采集中' : '无记录')
  }
  async function downloadCapture(nodeId: number) {
    captureDownloadingNodeId.value = nodeId
    try {
      const response: any = await getPerfRunCaptureDownload(id, nodeId)
      const url = response.data?.url
      if (!url) throw new Error('下载地址不可用')
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = response.data?.name || `perf-run-${id}-node-${nodeId}.csv`
      anchor.rel = 'noopener noreferrer'
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
    } catch (_error) {
      Message.error('请求记录下载失败，请稍后重试')
    } finally {
      captureDownloadingNodeId.value = null
    }
  }
  function formatDuration(seconds: number) {
    if (seconds < 60) return `${seconds} 秒`
    const minutes = Math.floor(seconds / 60)
    return `${minutes} 分 ${seconds % 60} 秒`
  }
  function nodeStatusTitle(value: string) {
    return (
      (
        {
          created: '已创建',
          waiting_executor: '等待执行器',
          dispatched: '已下发',
          preparing: '准备中',
          ready: '已就绪',
          running: '运行中',
          completed: '已完成',
          failed: '失败',
          stopped: '已停止',
          timeout: '超时',
          lost: '失联',
        } as Record<string, string>
      )[value] || value
    )
  }
  function nodeStatusColor(value: string) {
    if (value === 'completed') return 'green'
    if (['failed', 'timeout', 'lost'].includes(value)) return 'red'
    if (['preparing', 'ready', 'running'].includes(value)) return 'blue'
    return 'gray'
  }
  function performanceGoalMetricTitle(metric: string) {
    return metric === 'p95_ms'
      ? 'P95 响应时间'
      : metric === 'error_rate'
      ? '错误率'
      : metric === 'load_achievement_rate'
      ? '负载达成率'
      : metric
  }
  function formatGoalValue(metric: string, value: unknown) {
    if (metric === 'p95_ms') return `${Number(value || 0)} ms`
    if (metric === 'error_rate' || metric === 'load_achievement_rate')
      return `${Number((Number(value || 0) * 100).toFixed(2))}%`
    return String(value ?? '-')
  }
  function formatGoalActual(item: any) {
    return formatGoalValue(item.metric, item.actual_value)
  }
  function formatGoalExpected(item: any) {
    return formatGoalValue(item.metric, item.threshold_value)
  }
  async function loadOverview() {
    const response: any = await getPerfRunOverview(id)
    Object.assign(overview, response.data || {})
  }
  function mergeMetricPoints(incoming: any[]) {
    for (const item of incoming) {
      const key = item.window_start
      let target = points.value.find((row) => row.window_start === key)
      if (!target) {
        target = {
          ...item,
          target_load: { ...(item.target_load || {}) },
          actual_load: { ...(item.actual_load || {}) },
          generator_metrics: { ...(item.generator_metrics || {}) },
          _nodes: new Set([item.node_id]),
        }
        points.value.push(target)
        continue
      }
      if (target._nodes?.has(item.node_id)) continue
      target._nodes ||= new Set()
      target._nodes.add(item.node_id)
      for (const field of [
        'request_count',
        'failure_count',
        'iteration_count',
        'dropped_count',
        'response_time_sum_ms',
        'bytes_sent',
        'bytes_received',
        'connection_count',
        'connect_error_count',
      ])
        target[field] = Number(target[field] || 0) + Number(item[field] || 0)
      if (item.min_response_time_ms !== null && item.min_response_time_ms !== undefined)
        target.min_response_time_ms =
          target.min_response_time_ms === null || target.min_response_time_ms === undefined
            ? Number(item.min_response_time_ms)
            : Math.min(Number(target.min_response_time_ms), Number(item.min_response_time_ms))
      if (item.max_response_time_ms !== null && item.max_response_time_ms !== undefined)
        target.max_response_time_ms = Math.max(
          Number(target.max_response_time_ms || 0),
          Number(item.max_response_time_ms)
        )
      target.actual_load.users =
        Number(target.actual_load.users || 0) + Number(item.actual_load?.users || 0)
      target.target_load.users =
        Number(target.target_load.users || 0) + Number(item.target_load?.users || 0)
      target.generator_metrics.cpu_percent = Math.max(
        Number(target.generator_metrics.cpu_percent || 0),
        Number(item.generator_metrics?.cpu_percent || 0)
      )
      target.generator_metrics.memory_bytes =
        Number(target.generator_metrics.memory_bytes || 0) +
        Number(item.generator_metrics?.memory_bytes || 0)
      if (
        target.generator_metrics.event_loop_lag_ms != null ||
        item.generator_metrics?.event_loop_lag_ms != null
      )
        target.generator_metrics.event_loop_lag_ms = Math.max(
          Number(target.generator_metrics.event_loop_lag_ms || 0),
          Number(item.generator_metrics?.event_loop_lag_ms || 0)
        )
      for (const [field, value] of Object.entries(item.timing_breakdown || {})) {
        const targetRequests = Number(target.request_count || 0) - Number(item.request_count || 0)
        const itemRequests = Number(item.request_count || 0)
        const totalRequests = targetRequests + itemRequests
        if (value === null || value === undefined || !totalRequests) continue
        target.timing_breakdown ||= {}
        target.timing_breakdown[field] =
          (Number(target.timing_breakdown[field] || 0) * targetRequests +
            Number(value) * itemRequests) /
          totalRequests
      }
    }
    points.value.sort((left, right) =>
      String(left.window_start).localeCompare(String(right.window_start))
    )
    if (points.value.length > 600) points.value.splice(0, points.value.length - 600)
  }
  async function loadMetrics() {
    const response: any = await getPerfRunMetrics(id, {
      cursor,
      max_points: 1000,
      scope_type: 'global',
    })
    const data = response.data || {}
    cursor = data.cursor || cursor
    if (data.points?.length) {
      mergeMetricPoints(data.points)
      renderChart()
    }
    if (data.run_status && data.run_status !== overview.status) {
      overview.status = data.run_status
      overview.verdict = data.verdict
      if (!activeRunStatuses.has(data.run_status)) await refreshFinal()
    }
  }
  async function refreshFinal() {
    detailLoading.value = true
    try {
      const [
        requestResult,
        stageResult,
        nodeResult,
        gateResult,
        thresholdResult,
        errorResult,
        comparisonResult,
      ]: any[] = await Promise.all([
        getPerfRunRequests(id),
        getPerfRunStages(id),
        getPerfRunNodes(id),
        getPerfRunValidity(id),
        getPerfRunThresholds(id),
        getPerfRunErrors(id),
        getPerfRunComparison(id),
      ])
      requests.value = requestResult.data || []
      stages.value = stageResult.data || []
      nodes.value = nodeResult.data || []
      validity.value = gateResult.data || []
      thresholds.value = thresholdResult.data || []
      errors.value = errorResult.data || []
      Object.assign(comparison, comparisonResult.data || { available: false, metrics: [] })
      await loadOverview()
    } finally {
      detailLoading.value = false
    }
  }
  async function refreshAll() {
    refreshing.value = true
    try {
      await Promise.all([loadOverview(), loadMetrics(), refreshFinal()])
    } finally {
      refreshing.value = false
    }
  }
  function renderChart() {
    nextTick(() => {
      if (!chartRef.value || !loadChartRef.value) return
      chart ||= makeChartDensityAware(echarts.init(chartRef.value))
      loadChart ||= makeChartDensityAware(echarts.init(loadChartRef.value))
      if (resourceChartRef.value) {
        resourceChart ||= makeChartDensityAware(echarts.init(resourceChartRef.value))
      }
      chartResizeObserver ||= new ResizeObserver(resizeChart)
      ;[chartRef.value, loadChartRef.value, resourceChartRef.value]
        .filter(Boolean)
        .forEach((element) => chartResizeObserver?.observe(element as HTMLElement))
      const rows = points.value
      const axisColor = css('--m-muted')
      const splitColor = css('--m-border')
      const labelStyle = { color: axisColor, fontSize: 11 }
      const categoryAxis = {
        type: 'category' as const,
        boundaryGap: false,
        data: rows.map((item) => item.window_start?.slice(11, 19)),
        axisLabel: labelStyle,
        axisLine: { lineStyle: { color: splitColor } },
        axisTick: { show: false },
      }
      const valueAxis = (name: string) => ({
        type: 'value' as const,
        name,
        nameTextStyle: labelStyle,
        axisLabel: labelStyle,
        splitLine: { lineStyle: { color: splitColor, type: 'dashed' as const } },
      })
      chart.setOption(
        {
          animation: false,
          color: [css('--m-chart-1'), css('--m-chart-2')],
          grid: { left: 48, right: 50, top: 36, bottom: 28 },
          tooltip: { trigger: 'axis' },
          legend: { data: ['RPS', '平均响应时间'], textStyle: labelStyle },
          xAxis: categoryAxis,
          yAxis: [valueAxis('RPS'), valueAxis('ms')],
          series: [
            {
              name: 'RPS',
              type: 'line',
              smooth: 0.25,
              showSymbol: false,
              tooltip: {
                valueFormatter: (value: unknown) => `${formatNumber(value, 2)} RPS`,
              },
              data: rows.map((item) =>
                Number(
                  (Number(item.request_count || 0) / Number(item.window_seconds || 1)).toFixed(2)
                )
              ),
              areaStyle: { opacity: 0.1 },
            },
            {
              name: '平均响应时间',
              type: 'line',
              smooth: 0.25,
              yAxisIndex: 1,
              showSymbol: false,
              tooltip: {
                valueFormatter: (value: unknown) => `${formatNumber(value, 2)} ms`,
              },
              data: rows.map((item) =>
                item.request_count
                  ? Number(
                      (Number(item.response_time_sum_ms) / Number(item.request_count)).toFixed(2)
                    )
                  : 0
              ),
            },
          ],
        },
        true
      )
      loadChart.setOption(
        {
          animation: false,
          color: [css('--m-chart-3'), css('--m-chart-1'), css('--m-danger')],
          grid: { left: 48, right: 50, top: 36, bottom: 28 },
          tooltip: { trigger: 'axis' },
          legend: { data: ['目标用户', '活跃用户', '失败数'], textStyle: labelStyle },
          xAxis: categoryAxis,
          yAxis: [valueAxis('用户'), valueAxis('失败数')],
          series: [
            {
              name: '目标用户',
              type: 'line',
              step: 'end',
              showSymbol: false,
              lineStyle: { type: 'dashed', width: 1.5 },
              data: rows.map((item) => Number(item.target_load?.users || 0)),
            },
            {
              name: '活跃用户',
              type: 'line',
              smooth: 0.2,
              showSymbol: false,
              areaStyle: { opacity: 0.1 },
              data: rows.map((item) => Number(item.actual_load?.users || 0)),
            },
            {
              name: '失败数',
              type: 'bar',
              yAxisIndex: 1,
              barMaxWidth: 10,
              data: rows.map((item) => Number(item.failure_count || 0)),
            },
          ],
        },
        true
      )
      if (resourceChart) {
        resourceChart.setOption(
          {
            animation: false,
            color: [css('--m-chart-4'), css('--m-chart-2')],
            grid: { left: 48, right: 58, top: 36, bottom: 28 },
            tooltip: { trigger: 'axis' },
            legend: { data: ['CPU', '内存'], textStyle: labelStyle },
            xAxis: categoryAxis,
            yAxis: [valueAxis('%'), valueAxis('MB')],
            series: [
              {
                name: 'CPU',
                type: 'line',
                smooth: 0.2,
                showSymbol: false,
                areaStyle: { opacity: 0.08 },
                tooltip: { valueFormatter: (value: unknown) => `${formatNumber(value, 2)}%` },
                data: rows.map((item) => Number(item.generator_metrics?.cpu_percent || 0)),
              },
              {
                name: '内存',
                type: 'line',
                smooth: 0.2,
                yAxisIndex: 1,
                showSymbol: false,
                tooltip: { valueFormatter: (value: unknown) => `${formatNumber(value, 2)} MB` },
                data: rows.map(
                  (item) => Number(item.generator_metrics?.memory_bytes || 0) / 1024 ** 2
                ),
              },
            ],
          },
          true
        )
      }
    })
  }
  async function stop() {
    stopping.value = true
    try {
      await stopPerfRun(id)
      Message.success('停止请求已提交')
      await loadOverview()
    } finally {
      stopping.value = false
    }
  }
  function baseline() {
    Modal.confirm({
      title: '设为性能基线',
      content: '仅有效且通过的运行适合作为基线，确认继续？',
      async onOk() {
        baselineSaving.value = true
        try {
          await setPerfRunBaseline(id, overview.name)
          Message.success('基线已更新')
        } finally {
          baselineSaving.value = false
        }
      },
    })
  }
  async function exportReport() {
    exporting.value = true
    try {
      const response: any = await exportPerfRun(id)
      const url = URL.createObjectURL(
        new Blob([response.data], { type: 'application/json;charset=utf-8' })
      )
      const link = document.createElement('a')
      link.href = url
      link.download = `perf-run-${id}.json`
      link.click()
      URL.revokeObjectURL(url)
    } finally {
      exporting.value = false
    }
  }
  function rerun() {
    router.push({
      path: '/perf/scenario/details',
      query: { id: overview.scenario_id, execute: '1' },
    })
  }
  function handleWebsocket(event: Event) {
    const message = (event as CustomEvent).detail
    if (
      message?.data?.func_name !== 'perf_run_update' ||
      String(message?.data?.func_args?.run_id) !== id
    )
      return
    if (websocketTimer) clearTimeout(websocketTimer)
    websocketTimer = window.setTimeout(() => loadMetrics(), 150)
  }
  function resizeChart() {
    chart?.resize()
    loadChart?.resize()
    resourceChart?.resize()
  }
  onMounted(async () => {
    loading.value = true
    try {
      await Promise.all([loadOverview(), loadMetrics(), refreshFinal(), subscribePerfRun(id)])
      timer = window.setInterval(() => {
        if (activeRunStatuses.has(overview.status)) loadMetrics()
      }, 2000)
      subscriptionTimer = window.setInterval(() => subscribePerfRun(id), 30000)
      window.addEventListener('mango:websocket-message', handleWebsocket)
      window.addEventListener('resize', resizeChart)
    } finally {
      loading.value = false
    }
  })
  onBeforeUnmount(() => {
    if (timer) clearInterval(timer)
    if (subscriptionTimer) clearInterval(subscriptionTimer)
    if (websocketTimer) clearTimeout(websocketTimer)
    unsubscribePerfRun(id).catch(() => undefined)
    window.removeEventListener('mango:websocket-message', handleWebsocket)
    window.removeEventListener('resize', resizeChart)
    chartResizeObserver?.disconnect()
    chart?.dispose()
    loadChart?.dispose()
    resourceChart?.dispose()
  })
</script>

<style scoped lang="less">
  .mango-perf-detail-spin {
    display: block;
    width: 100%;
    min-width: 0;
  }
  .mango-perf-detail-spin :deep(> .mango-panel-spin__content) {
    width: 100%;
    min-width: 0;
  }
  .mango-perf-run-error-alert {
    margin-bottom: var(--m-page-gap);
  }
  .mango-perf-run-workbench {
    display: grid;
    width: 100%;
    min-width: 0;
    max-width: 100%;
    gap: var(--m-page-gap);
  }
  .mango-perf-run-workbench > *,
  .mango-perf-run-workbench .mango-section-card {
    min-width: 0;
    max-width: 100%;
  }
  .mango-perf-run-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(520px, 100%), 1fr));
    align-items: center;
    gap: var(--m-page-gap);
    border-left: 4px solid var(--m-muted);
  }
  .mango-perf-run-summary.is-passed {
    border-left-color: var(--m-success);
  }
  .mango-perf-run-summary.is-failed {
    border-left-color: var(--m-danger);
  }
  .mango-perf-run-summary.is-invalid {
    border-left-color: var(--m-warning);
  }
  .mango-perf-run-conclusion {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 14px;
  }
  .mango-perf-run-conclusion-mark {
    display: inline-flex;
    width: 58px;
    height: 58px;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--m-border-strong);
    border-radius: 50%;
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
  }
  .is-passed .mango-perf-run-conclusion-mark {
    border-color: color-mix(in srgb, var(--m-success) 35%, var(--m-border));
    background: color-mix(in srgb, var(--m-success) 10%, var(--m-surface));
    color: var(--m-success);
  }
  .is-failed .mango-perf-run-conclusion-mark {
    border-color: color-mix(in srgb, var(--m-danger) 35%, var(--m-border));
    background: color-mix(in srgb, var(--m-danger) 9%, var(--m-surface));
    color: var(--m-danger);
  }
  .is-invalid .mango-perf-run-conclusion-mark {
    border-color: color-mix(in srgb, var(--m-warning) 35%, var(--m-border));
    background: color-mix(in srgb, var(--m-warning) 10%, var(--m-surface));
    color: var(--m-warning);
  }
  .mango-perf-run-conclusion > div {
    min-width: 0;
  }
  .mango-perf-run-conclusion span,
  .mango-perf-run-conclusion p {
    color: var(--m-muted);
  }
  .mango-perf-run-conclusion h2 {
    margin: 3px 0;
    color: var(--m-text);
    font-size: 21px;
  }
  .mango-perf-run-conclusion p {
    margin: 0;
    line-height: 1.55;
  }
  .mango-perf-run-meta {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px 18px;
    padding-left: 20px;
    border-left: 1px solid var(--m-border);
  }
  .mango-perf-run-meta > div {
    display: grid;
    min-width: 0;
    gap: 3px;
  }
  .mango-perf-run-meta span {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-run-meta strong {
    overflow: hidden;
    color: var(--m-text-2);
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-perf-kpi-grid {
    display: grid;
    min-width: 0;
    grid-template-columns: repeat(auto-fit, minmax(min(190px, 100%), 1fr));
    gap: var(--m-page-gap);
  }
  .mango-perf-kpi-grid .mango-soft-panel {
    display: grid;
    gap: 4px;
    padding: 12px;
  }
  .mango-perf-kpi-grid strong {
    font-size: 22px;
    color: var(--m-text);
  }
  .mango-perf-kpi-grid span,
  .mango-perf-kpi-grid small {
    color: var(--m-muted);
  }
  .mango-perf-chart-title {
    align-items: flex-start;
  }
  .mango-perf-chart-grid {
    display: grid;
    width: 100%;
    min-width: 0;
    grid-template-columns: repeat(auto-fit, minmax(min(520px, 100%), 1fr));
    gap: var(--m-page-gap);
  }
  .mango-perf-chart-panel {
    min-width: 0;
    padding: 10px 10px 2px;
  }
  .mango-perf-chart-panel > div:first-child {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 0 4px;
  }
  .mango-perf-chart-panel strong {
    color: var(--m-text);
  }
  .mango-perf-chart-panel span {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-chart {
    width: 100%;
    min-width: 0;
    height: 260px;
  }
  .mango-perf-resource-chart-panel {
    grid-column: 1 / -1;
  }
  .mango-perf-resource-chart {
    height: 220px;
  }
  .mango-perf-metric-groups {
    display: grid;
    min-width: 0;
    grid-template-columns: repeat(auto-fit, minmax(min(250px, 100%), 1fr));
    gap: var(--m-page-gap);
  }
  .mango-perf-metric-group {
    min-width: 0;
    padding: 12px;
  }
  .mango-perf-metric-group-head {
    display: grid;
    gap: 2px;
    padding-bottom: 9px;
    border-bottom: 1px solid var(--m-border);
  }
  .mango-perf-metric-group-head strong {
    color: var(--m-text);
  }
  .mango-perf-metric-group-head span {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-metric-group dl {
    display: grid;
    gap: 8px;
    margin: 10px 0 0;
  }
  .mango-perf-metric-group dl > div {
    display: flex;
    min-width: 0;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
  }
  .mango-perf-metric-group dt {
    color: var(--m-muted);
  }
  .mango-perf-metric-group dd {
    margin: 0;
    color: var(--m-text-2);
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    text-align: right;
  }
  .mango-perf-live-indicator {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--m-muted);
  }
  .mango-perf-live-indicator i {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--m-success);
  }
  .mango-perf-error-list {
    display: grid;
    gap: var(--m-page-gap);
  }
  .mango-perf-error-list .mango-soft-panel {
    display: grid;
    gap: 8px;
    padding: 10px;
  }
  .mango-perf-error-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .mango-perf-error-head strong {
    color: var(--m-danger);
  }
  .mango-perf-error-head span,
  .mango-perf-error-list > div > span {
    color: var(--m-muted);
  }
  .mango-perf-error-sample {
    display: grid;
    gap: 4px;
    padding-top: 8px;
    border-top: 1px solid var(--m-border);
  }
  .mango-perf-error-sample small {
    color: var(--m-muted);
  }
  .mango-perf-error-sample code {
    overflow: hidden;
    color: var(--m-text-2);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-perf-stage-flow {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: var(--m-page-gap);
  }
  .mango-perf-stage-card {
    position: relative;
    display: grid;
    gap: 12px;
    padding: 12px;
  }
  .mango-perf-stage-head {
    display: flex;
    align-items: center;
    gap: 9px;
  }
  .mango-perf-stage-head > span {
    display: inline-flex;
    width: 24px;
    height: 24px;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: var(--m-primary-soft);
    color: var(--m-primary);
    font-weight: 700;
  }
  .mango-perf-stage-head > div {
    display: grid;
    min-width: 0;
  }
  .mango-perf-stage-head strong,
  .mango-perf-stage-target strong {
    color: var(--m-text);
  }
  .mango-perf-stage-head small,
  .mango-perf-stage-target span,
  .mango-perf-stage-stats {
    color: var(--m-muted);
  }
  .mango-perf-stage-target {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
  }
  .mango-perf-stage-target strong {
    font-size: 18px;
  }
  .mango-perf-stage-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    padding-top: 8px;
    border-top: 1px solid var(--m-border);
    font-size: 12px;
  }
  .mango-perf-compare-alert {
    margin-bottom: var(--m-page-gap);
  }
  .mango-perf-goal-result {
    display: grid;
    gap: 10px;
  }
  .mango-perf-goal-result-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .mango-perf-goal-result-head > div {
    display: grid;
    gap: 2px;
  }
  .mango-perf-goal-result-head strong {
    color: var(--m-text);
  }
  .mango-perf-goal-result-head span {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-goal-result-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--m-page-gap);
  }
  .mango-perf-goal-result-item {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 4px 10px;
    padding: 12px;
  }
  .mango-perf-goal-result-item > span,
  .mango-perf-goal-result-item > strong,
  .mango-perf-goal-result-item > small {
    grid-column: 1;
  }
  .mango-perf-goal-result-item > span,
  .mango-perf-goal-result-item > small {
    color: var(--m-muted);
  }
  .mango-perf-goal-result-item > strong {
    color: var(--m-text);
    font-size: 20px;
  }
  .mango-perf-goal-result-item > .arco-tag {
    grid-column: 2;
    grid-row: 1 / span 3;
  }
  @container (max-width: 1099px) {
    .mango-perf-run-meta {
      padding-top: 14px;
      padding-left: 0;
      border-top: 1px solid var(--m-border);
      border-left: 0;
    }
  }
</style>
