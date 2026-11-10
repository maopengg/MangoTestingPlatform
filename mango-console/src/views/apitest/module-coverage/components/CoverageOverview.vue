<template>
  <div class="mango-coverage-overview">
    <div
      class="mango-coverage-overview__scroll mango-native-scrollbar"
      role="region"
      aria-label="覆盖概览内容"
      tabindex="0"
    >
      <template v-if="error && !data"></template>
      <div v-else-if="data || loading" class="mango-coverage-overview__layout">
        
        <div v-if="!loading && !data?.modules.length" class="mango-empty-state"
          >当前范围暂无模块，请选择项目/产品或创建模块。</div
        >
        <template v-else>
          <div
            class="mango-workbench-scroll-x mango-coverage-overview__charts-scroll"
            role="region"
            aria-label="覆盖统计图表，可横向滚动"
            tabindex="0"
          >
            <div class="mango-coverage-overview__charts">
              <section class="mango-section-card mango-coverage-overview__panel">
                <header class="mango-section-title"
                  ><div class="mango-section-title__main"
                    ><h2>① 模块接口扫描进度</h2
                    ><p>完整接口清单上传生效即完成</p></div
                  ></header
                >
                <MangoPanelSpin :loading="loading" class="mango-coverage-overview__chart-spin">
                  <div ref="scanChart" class="mango-coverage-overview__chart"></div>
                </MangoPanelSpin>
              </section>
              <section class="mango-section-card mango-coverage-overview__panel">
                <header class="mango-section-title"
                  ><div class="mango-section-title__main"
                    ><h2>② 接口分析进度</h2
                    ><p>业务全景图和场景分析</p></div
                  ></header
                >
                <MangoPanelSpin :loading="loading" class="mango-coverage-overview__chart-spin">
                  <div
                    v-if="loading || data?.summary.interface_count"
                    ref="entryChart"
                    class="mango-coverage-overview__chart mango-coverage-overview__analysis-chart"
                    role="img"
                    :aria-label="entryDescription"
                  ></div>
                  <div v-if="data?.summary.interface_count" class="mango-coverage-overview__analysis-legend">
                    <button
                      v-for="item in entryData"
                      :key="item.status"
                      type="button"
                      class="mango-coverage-overview__analysis-state"
                      :data-state="item.status"
                      :aria-pressed="gapFilter === item.filter"
                      @click="gapFilter = item.filter"
                    >
                      <i aria-hidden="true"></i>
                      <span>{{ item.name }}</span>
                      <small>{{ item.value.toLocaleString('zh-CN') }} 个 · {{ data.summary.interface_count ? ((item.value / data.summary.interface_count) * 100).toFixed(2) : '0.00' }}%</small>
                    </button>
                  </div>
                  <div v-if="!loading && !data?.summary.interface_count" class="mango-empty-state mango-coverage-overview__chart-empty"
                    >暂无已发现接口</div
                  >
                </MangoPanelSpin>
              </section>
              <section class="mango-section-card mango-coverage-overview__panel">
                <header class="mango-section-title"
                  ><div class="mango-section-title__main"
                    ><h2>③ 用例自动化进度</h2><p>有效自动化场景完成情况</p></div
                  ></header
                >
                <MangoPanelSpin :loading="loading" class="mango-coverage-overview__chart-spin">
                  <div
                    v-if="loading || statusTotal"
                    ref="statusChart"
                    class="mango-coverage-overview__chart"
                    role="img"
                    :aria-label="statusDescription"
                  ></div>
                  <div v-else class="mango-empty-state mango-coverage-overview__chart-empty"
                    >暂无自动化场景</div
                  >
                </MangoPanelSpin>
              </section>
              <section class="mango-section-card mango-coverage-overview__panel">
                <header class="mango-section-title"
                  ><div class="mango-section-title__main"
                    ><h2>④ 接口覆盖率</h2><p>分析完成且全部目标场景有效完成才算覆盖</p
                    ><p v-if="data?.summary.excluded_interface_count"
                      >已排除 {{ data.summary.excluded_interface_count }} 个接口，不计入分母</p
                    ></div
                  ></header
                >
                <MangoPanelSpin :loading="loading" class="mango-coverage-overview__chart-spin">
                  <div
                    v-if="loading || data?.summary.interface_count"
                    ref="coverageChart"
                    class="mango-coverage-overview__chart"
                    role="img"
                    :aria-label="coverageDescription"
                  ></div>
                  <div v-else class="mango-empty-state mango-coverage-overview__chart-empty"
                    >暂无已发现接口</div
                  >
                </MangoPanelSpin>
              </section>
            </div>
          </div>
          <section class="mango-section-card mango-coverage-overview__panel">
            <header class="mango-section-title mango-coverage-overview__toolbar">
              <div class="mango-section-title__main"
                ><h2>模块进度</h2
                ><p>{{
                  loading && !data
                    ? '正在加载模块进度…'
                    : `当前 ${filtered.length} 个模块，点击分析或自动化进度查看明细`
                }}</p></div
              >
              <div class="mango-section-actions mango-coverage-overview__filters">
                <a-input
                  v-model="keyword"
                  class="mango-coverage-overview__search"
                  placeholder="搜索模块路径"
                  allow-clear
                  size="small"
                />
                <a-select
                  v-model="gapFilter"
                  :options="overviewFilters"
                  class="mango-coverage-overview__filter"
                  size="small"
                  aria-label="模块进度筛选"
                />
              </div>
            </header>
            <div
              ref="moduleTableRegion"
              class="mango-coverage-overview__table"
              @wheel="handleModuleTableWheel"
            >
              <StickyHorizontalTable :scroll-x="overviewModuleScrollX">
                <a-table
                  class="mango-native-scroll-table"
                  :data="visibleModules"
                  :columns="overviewModuleColumns"
                  :loading="loading"
                  :bordered="false"
                  :pagination="false"
                  :scroll="{ x: overviewModuleScrollX, y: overviewModuleScrollY }"
                  row-key="id"
                  size="small"
                >
                  <template #scan="{ record }">{{ scanLabel(record) }}</template>
                  <template #entry="{ record }">
                    <button
                      class="mango-coverage-overview__progress"
                      :aria-label="`查看${record.name}的接口分析明细`"
                      @click="drill(record, 'interfaces')"
                    >
                      <span
                        ><b>{{ rate(record.analysis_rate) }}</b
                        ><small
                          >{{ record.analyzed_interface_count }} /
                          {{ record.interface_count }}</small
                        ></span
                      >
                      <a-progress
                        :percent="(record.analysis_rate || 0) / 100"
                        color="var(--m-chart-1)"
                        :show-text="false"
                        size="small"
                      />
                    </button>
                  </template>
                  <template #automation="{ record }">
                    <button
                      class="mango-coverage-overview__progress"
                      :aria-label="`查看${record.name}的自动化场景明细`"
                      @click="drill(record, 'cases')"
                    >
                      <span
                        ><b>完成率 {{ rate(record.automation_rate) }}</b
                        ><small
                          >{{ record.completed_count }} / {{ record.target_count }}</small
                        ></span
                      >
                      <a-progress
                        :percent="(record.automation_rate || 0) / 100"
                        color="var(--m-chart-2)"
                        :show-text="false"
                        size="small"
                      />
                    </button>
                  </template>
                  <template #project_product="{ record }"
                    >{{ record.project_name }} / {{ record.product_name }}</template
                  >
                  <template #actions="{ record }">
                    <MangoTableActions
                      :actions="[{ label: '扫描记录', onClick: () => drill(record, 'scans') }]"
                    />
                  </template>
                  <template #empty
                    ><div class="mango-empty-state">{{
                      loading ? '正在加载模块进度…' : '当前条件没有模块。'
                    }}</div></template
                  >
                </a-table>
              </StickyHorizontalTable>
            </div>
            <TableFooter
              compact-pages
              v-if="filtered.length"
              :pagination="pagination"
              :show-refresh="false"
            />
          </section>
          <section class="mango-section-card mango-coverage-overview__panel">
            <header class="mango-section-title"
              ><div class="mango-section-title__main"
                ><h2>待完成接口</h2
                ><p
                  >共 {{ data?.interface_gap_count ?? '—' }} 个，展示前 20
                  个；点击模块进度可查看全部明细</p
                ></div
              ></header
            >
            <MangoPanelSpin :loading="loading" class="mango-coverage-overview__gaps-spin">
              <div v-if="!data?.interface_gaps.length" class="mango-empty-state">{{
                loading
                  ? '正在加载待完成接口…'
                  : '已发现接口暂无录入或自动化缺口，未扫描模块仍需扫描确认。'
              }}</div>
              <div
                v-for="item in data?.interface_gaps || []"
                :key="item.id"
                class="mango-coverage-overview__gap"
              >
                <div
                  ><strong>{{ item.name }}</strong
                  ><small>{{ item.module_path }} · {{ item.method }} {{ item.url }}</small></div
                >
                <span>{{ !item.bound ? '接口尚未正确录入' : '接口已录入' }}</span>
                <span
                  >{{
                    item.target_count
                      ? `自动化 ${item.completed_count}/${item.target_count}`
                      : item.deferred_count
                      ? `暂不处理 ${item.deferred_count} 个场景`
                      : '尚无自动化场景'
                  }}{{
                    item.target_count && item.deferred_count
                      ? ` · 暂不处理 ${item.deferred_count}`
                      : ''
                  }}</span
                >
                <a-link @click="emit('interface', item.id)">查看场景</a-link>
              </div>
            </MangoPanelSpin>
          </section>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import {
    computed,
    nextTick,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    ref,
    watch,
  } from 'vue'
  import { dispose, use } from 'echarts/core'
  import { TitleComponent } from 'echarts/components'
  import useEcharts from '@/hooks/useEcharts'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import { usePagination } from '@/hooks/table'
  import type { CoverageOverview, CoverageModuleOverview } from '@/api/apitest/module-coverage'
  import type { CoverageTab } from '../types'
  import {
    getAutomationStatusData,
    getInterfaceCoverageData,
    getInterfaceAnalysisData,
    overviewFilters,
    overviewModuleColumns,
    overviewModuleScrollX,
    overviewModuleScrollY,
  } from '../config'

  use([TitleComponent])

  const props = defineProps<{ data?: CoverageOverview; loading: boolean; error: boolean }>()
  const emit = defineEmits<{
    (event: 'retry'): void
    (
      event: 'drill',
      row: CoverageModuleOverview,
      tab: CoverageTab,
      query?: Record<string, string[]>
    ): void
    (event: 'interface', id: number): void
  }>()
  const keyword = ref('')
  const gapFilter = ref('all')
  const moduleTableRegion = ref<HTMLElement>()
  function handleModuleTableWheel(event: WheelEvent) {
    if (event.ctrlKey || !event.cancelable || Math.abs(event.deltaY) <= Math.abs(event.deltaX))
      return
    const body = moduleTableRegion.value?.querySelector<HTMLElement>('.arco-table-body')
    if (!body || body.scrollHeight <= body.clientHeight) return
    // 表头等区域不在表体滚动链中，纵向滚轮仍交给同一表体；表体内部保持原生滚动。
    if (event.target instanceof Node && body.contains(event.target)) return
    const unit =
      event.deltaMode === 2 ? body.clientHeight : event.deltaMode === 1 ? scaleDensityPixels(20) : 1
    event.preventDefault()
    body.scrollTop += event.deltaY * unit
  }
  const paginationLoading = ref(false)
  const pagination = usePagination(() => {
    paginationLoading.value = false
  }, paginationLoading)
  const scanChart = ref<HTMLElement>()
  const entryChart = ref<HTMLElement>()
  const coverageChart = ref<HTMLElement>()
  const statusChart = ref<HTMLElement>()
  const coverageData = computed(() =>
    props.data ? getInterfaceCoverageData(props.data.summary) : []
  )
  const coverageDescription = computed(
    () =>
      `以纳入覆盖接口总数为分母，已排除接口不计入，暂不处理不算已覆盖。${coverageData.value
        .map((item) => `${item.name} ${item.value} 个接口`)
        .join('，')}`
  )
  const entryData = computed(() => (props.data ? getInterfaceAnalysisData(props.data.summary) : []))
  const entryDescription = computed(() =>
    entryData.value.map((item) => `${item.name} ${item.value} 个接口`).join('，')
  )
  const projectScanSummary = computed(() => props.data?.project_inventory_summary)
  const statusData = computed(() => (props.data ? getAutomationStatusData(props.data.summary) : []))
  const statusTotal = computed(() => statusData.value.reduce((sum, item) => sum + item.value, 0))
  const statusPercent = (value: number) =>
    statusTotal.value ? ((value * 100) / statusTotal.value).toFixed(2) : '0.00'
  const statusDescription = computed(() =>
    statusData.value.map((item) => `${item.name} ${item.value} 个场景`).join('，')
  )
  let disposed = false,
    suspended = false,
    updateRequest = 0
  let observer: ResizeObserver | undefined
  let chartElements: HTMLElement[] = []
  const rate = (value: number | null | undefined) => (value == null ? '—' : `${value.toFixed(2)}%`)
  const filtered = computed(() =>
    (props.data?.modules || []).filter((row) => {
      if (
        !`${row.project_name}/${row.product_name}/${row.full_path}`
          .toLowerCase()
          .includes(keyword.value.toLowerCase())
      )
        return false
      if (gapFilter.value === 'scan') return !row.inventory_completed && row.is_leaf
      if (gapFilter.value === 'entry') return row.pending_analysis_count > 0
      if (gapFilter.value === 'analysis_completed') return row.analyzed_interface_count > 0
      if (gapFilter.value === 'analysis_gap') return row.analysis_gap_count > 0
      if (gapFilter.value === 'analysis_review') return (row.analysis_review_count || 0) > 0
      if (gapFilter.value === 'analysis_deferred') return row.deferred_analysis_count > 0
      if (gapFilter.value === 'covered') return row.covered_interface_count > 0
      if (gapFilter.value === 'partial') return row.partial_interface_count > 0
      if (gapFilter.value === 'uncovered') return row.uncovered_interface_count > 0
      if (gapFilter.value === 'deferred') return row.deferred_interface_count > 0
      if (gapFilter.value === 'case') return row.incomplete_interface_count > 0
      return true
    })
  )
  const visibleModules = computed(() =>
    filtered.value.slice(
      (pagination.page - 1) * pagination.pageSize,
      pagination.page * pagination.pageSize
    )
  )
  watch(filtered, (rows) => pagination.setTotalSize(rows.length), { immediate: true })
  function scanLabel(row: CoverageModuleOverview) {
    if (row.inventory_completed) return `接口清单已生效 #${row.inventory_scan_ids.join('、#')}`
    return row.latest_scan_id ? `接口盘点未完成 · 最近 #${row.latest_scan_id}` : '未盘点'
  }
  function drill(row: CoverageModuleOverview, tab: CoverageTab) {
    const analysis = entryData.value.find((item) => item.filter === gapFilter.value)
    const query: Record<string, string[]> = {}
    if (tab === 'interfaces' && analysis) query.analysis_statuses = [analysis.status]
    if (
      tab === 'interfaces' &&
      ['covered', 'partial', 'uncovered', 'deferred'].includes(gapFilter.value)
    )
      query.coverage_statuses = [gapFilter.value]
    emit('drill', row, tab, query)
  }
  const token = (name: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  function donutStyle(
    element: HTMLElement,
    rows: Array<{ name: string; value: number }>,
    unit: string,
    centerText?: string
  ) {
    const total = rows.reduce((sum, item) => sum + item.value, 0)
    const text = token('--m-text-2')
    const current = useEcharts(element).getOption() as
      | {
          legend?: Array<{ selected?: Record<string, boolean> }>
        }
      | undefined
    const selected = current?.legend?.[0]?.selected
    return {
      textStyle: {
        fontFamily: getComputedStyle(document.documentElement).fontFamily,
        color: text,
        fontSize: 12,
      },
      title: {
        text: centerText ?? total.toLocaleString('zh-CN'),
        subtext: unit,
        left: '50%',
        top: '34%',
        textAlign: 'center',
        itemGap: 4,
        textStyle: { color: token('--m-text'), fontSize: 24, fontWeight: 600 },
        subtextStyle: { color: token('--m-muted'), fontSize: 11 },
      },
      legend: {
        selected,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        itemWidth: 10,
        itemHeight: 8,
        itemGap: 16,
        icon: 'roundRect',
        textStyle: { color: text, fontSize: 12, lineHeight: 18 },
      },
    }
  }
  function donutSeries(element: HTMLElement, rows: Array<{ name: string; value: number }>) {
    const compact = element.clientWidth < scaleDensityPixels(460)
    const total = rows.reduce((sum, item) => sum + item.value, 0)
    return {
      type: 'pie',
      radius: compact ? ['40%', '58%'] : ['50%', '68%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      label: {
        show: true,
        position: 'outside',
        color: token('--m-text-2'),
        fontSize: 11,
        lineHeight: 17,
        alignTo: 'edge',
        edgeDistance: 8,
        formatter(item: { name: string; value: number }) {
          const percent = total ? ((item.value * 100) / total).toFixed(2) : '0.00'
          return `${item.name}\n${item.value.toLocaleString('zh-CN')} 个 · ${percent}%`
        },
      },
      labelLine: { show: true, length: 12, length2: 8, lineStyle: { color: token('--m-muted') } },
      labelLayout: { hideOverlap: true },
      itemStyle: { borderColor: token('--m-surface'), borderWidth: 4, borderRadius: 6 },
      emphasis: { scale: false },
    }
  }
  function render() {
    if (disposed || suspended || !props.data || props.error) return
    const text = token('--m-text-2')
    const tooltip = {
      trigger: 'item',
      confine: true,
      renderMode: 'richText',
      backgroundColor: token('--m-surface'),
      borderColor: token('--m-border'),
      textStyle: { color: text, fontSize: 12 },
      padding: 10,
    }
    if (scanChart.value) {
      const chart = useEcharts(scanChart.value)
      const rows = [
        { name: '已盘点', value: projectScanSummary.value?.inventoried_count || 0 },
        { name: '未盘点', value: projectScanSummary.value?.uninventoried_count || 0 },
      ]
      chart.setOption(
        {
          ...donutStyle(scanChart.value, rows, '模块总数'),
          animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
          animationDuration: 280,
          color: [token('--m-success'), token('--m-chart-5')],
          tooltip,
          series: [
            {
              ...donutSeries(scanChart.value, rows),
              data: [
                { name: '已盘点', value: projectScanSummary.value?.inventoried_count || 0 },
                { name: '未盘点', value: projectScanSummary.value?.uninventoried_count || 0 },
              ],
            },
          ],
        },
        true
      )
      chart.off('click')
      chart.on('click', (event: { dataIndex: number }) => {
        gapFilter.value = event.dataIndex === 1 ? 'scan' : 'all'
      })
    }
    if (entryChart.value) {
      const chart = useEcharts(entryChart.value)
      chart.setOption(
        {
          ...donutStyle(
            entryChart.value,
            entryData.value,
            '分析完成率',
            rate(props.data.summary.analysis_rate)
          ),
          animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
          animationDuration: 280,
          color: [
            token('--m-success'),
            token('--m-warning'),
            token('--m-danger'),
            token('--m-primary'),
            token('--m-chart-5'),
          ],
          tooltip,
          title: {
            text: rate(props.data.summary.analysis_rate),
            subtext: '分析完成率',
            left: 'center',
            top: '35%',
            textStyle: { color: token('--m-text'), fontSize: 24, fontWeight: 600 },
            subtextStyle: { color: token('--m-muted'), fontSize: 11 },
          },
          legend: { show: false },
          series: [{
            ...donutSeries(entryChart.value, entryData.value),
            center: ['50%', '50%'],
            radius: ['64%', '86%'],
            label: { show: false },
            labelLine: { show: false },
            data: entryData.value,
          }],
        },
        true
      )
      chart.off('click')
      chart.on('click', (event: { dataIndex: number }) => {
        gapFilter.value = entryData.value[event.dataIndex]?.filter || 'all'
      })
    }
    if (coverageChart.value) {
      const chart = useEcharts(coverageChart.value)
      chart.setOption(
        {
          ...donutStyle(
            coverageChart.value,
            coverageData.value,
            '接口覆盖率',
            rate(props.data.summary.interface_coverage_rate)
          ),
          animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
          animationDuration: 280,
          color: [
            token('--m-success'),
            token('--m-chart-1'),
            token('--m-warning'),
            token('--m-chart-5'),
          ],
          tooltip,
          series: [
            { ...donutSeries(coverageChart.value, coverageData.value), data: coverageData.value },
          ],
        },
        true
      )
      chart.off('click')
      chart.on('click', (event: { dataIndex: number }) => {
        gapFilter.value = ['covered', 'partial', 'uncovered', 'deferred'][event.dataIndex] || 'all'
      })
    }
    if (statusChart.value) {
      useEcharts(statusChart.value).setOption(
        {
          ...donutStyle(statusChart.value, statusData.value, '场景总数'),
          animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
          animationDuration: 280,
          color: [token('--m-success'), token('--m-warning'), token('--m-chart-5')],
          tooltip: {
            ...tooltip,
            formatter: (item: { name: string; value: number }) =>
              `${item.name}：${item.value} 个场景（${statusPercent(item.value)}%）`,
          },
          series: [
            {
              ...donutSeries(statusChart.value, statusData.value),
              data: statusData.value,
            },
          ],
        },
        true
      )
    }
  }
  function resize() {
    if (disposed || suspended) return
    for (const element of [
      scanChart.value,
      entryChart.value,
      coverageChart.value,
      statusChart.value,
    ])
      if (element) useEcharts(element).resize()
    render()
  }
  async function update() {
    const request = ++updateRequest
    await nextTick()
    if (disposed || suspended || request !== updateRequest) return
    observer?.disconnect()
    const current = [
      scanChart.value,
      entryChart.value,
      coverageChart.value,
      statusChart.value,
    ].filter((element): element is HTMLElement => !!element)
    for (const element of chartElements) if (!current.includes(element)) dispose(element)
    chartElements = current
    for (const element of [
      scanChart.value,
      entryChart.value,
      coverageChart.value,
      statusChart.value,
    ])
      if (element) observer?.observe(element)
    render()
  }
  watch([keyword, gapFilter, () => props.data], () => {
    pagination.page = 1
  })
  watch(() => [props.data, props.error, props.loading], update)
  function attach() {
    window.addEventListener('mango-theme-change', render)
    window.addEventListener('mango-density-change', resize)
  }
  function release() {
    ++updateRequest
    observer?.disconnect()
    window.removeEventListener('mango-theme-change', render)
    window.removeEventListener('mango-density-change', resize)
    for (const element of chartElements) dispose(element)
    chartElements = []
  }
  onMounted(() => {
    observer = new ResizeObserver(resize)
    attach()
    void update()
  })
  onDeactivated(() => {
    suspended = true
    release()
  })
  onActivated(() => {
    if (suspended) {
      suspended = false
      attach()
      void update()
    }
  })
  onBeforeUnmount(() => {
    disposed = true
    release()
  })
</script>

<style scoped lang="less">
  .mango-coverage-overview {
    width: 100%;
    height: 100%;
    min-height: 0;
    min-width: 0;
    flex: 1;
    overflow: hidden;
    container-type: inline-size;
    container-name: mango-coverage-overview;
  }
  .mango-coverage-overview__chart-spin,
  .mango-coverage-overview__gaps-spin {
    display: block;
    width: 100%;
  }
  .mango-coverage-overview__scroll {
    height: 100%;
    min-height: 0;
    overflow-y: scroll;
    overflow-x: hidden;
    scrollbar-gutter: stable;
    overscroll-behavior-y: contain;
    padding: var(--m-page-gap);
    box-sizing: border-box;
  }
  .mango-coverage-overview__layout {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-coverage-overview__charts-scroll {
    --mango-workbench-min-width: 1280px;
    height: auto;
    flex-shrink: 0;
  }
  .mango-coverage-overview__charts {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    min-width: var(--mango-workbench-min-width);
    gap: var(--m-page-gap);
  }
  .mango-coverage-overview__panel {
    min-width: 0;
  }
  .mango-section-card.mango-coverage-overview__panel {
    margin: 0;
  }
  .mango-coverage-overview__chart {
    height: 240px;
    width: 100%;
    min-width: 0;
  }
  .mango-coverage-overview__chart-empty {
    height: 240px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .mango-coverage-overview__analysis-chart {
    height: 156px;
  }
  .mango-coverage-overview__analysis-legend {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 4px 12px;
    padding-top: 4px;
  }
  .mango-coverage-overview__analysis-state {
    display: grid;
    grid-template-columns: 8px minmax(0, 1fr);
    column-gap: 6px;
    align-items: center;
    min-width: 0;
    padding: 2px 0;
    border: 0;
    background: transparent;
    color: var(--m-text-2);
    font: inherit;
    font-size: 12px;
    line-height: 18px;
    text-align: left;
    cursor: pointer;
    i {
      width: 8px;
      height: 8px;
      border-radius: 2px;
      background: var(--m-chart-5);
    }
    small {
      grid-column: 2;
      color: var(--m-muted);
      font-size: 11px;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    &[data-state='completed'] i { background: var(--m-success); }
    &[data-state='pending'] i { background: var(--m-warning); }
    &[data-state='gap'] i { background: var(--m-danger); }
    &[data-state='review'] i { background: var(--m-primary); }
    &:hover, &[aria-pressed='true'] { color: var(--m-primary); }
    &:focus-visible { outline: 2px solid var(--m-primary); outline-offset: 2px; }
  }
  .mango-coverage-overview__toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--m-page-gap);
  }
  .mango-coverage-overview__filters {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    flex: 0 1 440px;
    min-width: 0;
    gap: var(--m-page-gap);
  }
  .mango-coverage-overview__search {
    width: 100%;
    min-width: 0;
  }
  .mango-coverage-overview__filter {
    width: 100%;
    min-width: 0;
  }
  .mango-coverage-overview__table {
    display: flex;
    flex-direction: column;
    height: 440px;
    min-width: 0;
    min-height: 0;
  }
  .mango-coverage-overview__table :deep(.arco-table-body) {
    overscroll-behavior-x: contain;
    overscroll-behavior-y: contain;
  }
  .mango-coverage-overview__progress small,
  .mango-coverage-overview__gap small {
    color: var(--m-muted);
    font-size: var(--m-font-caption);
    line-height: var(--m-line-caption);
  }
  .mango-coverage-overview__progress {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    align-items: center;
    column-gap: var(--m-space-sm);
    width: 100%;
    border: 0;
    background: transparent;
    padding: var(--m-space-xs) 0;
    text-align: left;
    color: var(--m-text-2);
    cursor: pointer;
    min-width: 0;
  }
  .mango-coverage-overview__progress small {
    display: block;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .mango-coverage-overview__progress:hover {
    color: var(--m-primary);
  }
  .mango-coverage-overview__progress span {
    grid-column: 1 / -1;
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--m-space-xs);
  }
  .mango-coverage-overview__progress:focus-visible {
    outline: 2px solid var(--m-chart-1);
  }
  .mango-coverage-overview__gap {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--m-page-gap);
    padding: var(--m-space-sm) 0;
    border-top: 1px solid var(--m-border);
    font-size: var(--m-font-caption);
    color: var(--m-text-2);
  }
  .mango-coverage-overview__gap > div {
    flex: 1 1 240px;
    min-width: 0;
  }
  .mango-coverage-overview__gap strong,
  .mango-coverage-overview__gap small {
    display: block;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  @container mango-coverage-overview (max-width: 760px) {
    .mango-coverage-overview__filters {
      flex: 1 1 100%;
      justify-content: flex-start;
    }
  }
</style>
