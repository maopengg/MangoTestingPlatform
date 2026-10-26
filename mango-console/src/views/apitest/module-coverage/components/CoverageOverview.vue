<template>
  <div class="mango-coverage-overview">
      <div
        class="mango-coverage-overview__scroll mango-native-scrollbar"
        role="region"
        aria-label="覆盖概览内容"
        tabindex="0"
      >
        <div v-if="error && !data" class="mango-empty-state">
          覆盖概览加载失败，<a-link @click="emit('retry')">重新加载</a-link>
        </div>
        <div v-else-if="data || loading" class="mango-coverage-overview__layout">
          <a-alert v-if="error" type="warning">覆盖概览刷新失败，当前保留上次结果。<a-link @click="emit('retry')">重试</a-link></a-alert>
          <div v-if="!loading && !data?.modules.length" class="mango-empty-state"
            >当前范围暂无模块，请选择项目/产品或创建模块。</div
          >
          <template v-else>
            <div class="mango-workbench-scroll-x mango-coverage-overview__charts-scroll" role="region" aria-label="覆盖统计图表，可横向滚动" tabindex="0">
            <div class="mango-coverage-overview__charts">
              <section class="mango-section-card mango-coverage-overview__panel">
                <header class="mango-section-title"
                  ><div class="mango-section-title__main"
                    ><h2>模块扫描进度</h2><p>项目/产品级统计，不随左侧模块选择变化</p></div
                  ></header
                >
                <MangoPanelSpin :loading="loading" class="mango-coverage-overview__chart-spin">
                  <div ref="scanChart" class="mango-coverage-overview__chart"></div>
                </MangoPanelSpin>
              </section>
              <section class="mango-section-card mango-coverage-overview__panel">
                <header class="mango-section-title"
                  ><div class="mango-section-title__main"
                    ><h2>接口录入状态</h2><p>已发现接口的 ApiInfo 绑定情况；点击待录入筛选模块</p></div
                  ></header
                >
                <MangoPanelSpin :loading="loading" class="mango-coverage-overview__chart-spin">
                <div
                  v-if="loading || data?.summary.interface_count"
                  ref="entryChart"
                  class="mango-coverage-overview__chart"
                  role="img"
                  :aria-label="entryDescription"
                ></div>
                <div v-else class="mango-empty-state mango-coverage-overview__chart-empty"
                  >暂无已发现接口</div
                >
                </MangoPanelSpin>
              </section>
              <section class="mango-section-card mango-coverage-overview__panel">
                <header class="mango-section-title"
                  ><div class="mango-section-title__main"
                    ><h2>接口覆盖率</h2><p>已覆盖 / 已发现接口；全部目标场景有效完成才算覆盖</p></div
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
              <section class="mango-section-card mango-coverage-overview__panel">
                <header class="mango-section-title"
                  ><div class="mango-section-title__main"
                    ><h2>用例自动化进度</h2><p>按 Case 场景统计，待复核、失效计入未完成</p></div
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
            </div>
            </div>
            <section class="mango-section-card mango-coverage-overview__panel">
              <header class="mango-section-title mango-coverage-overview__toolbar">
                <div class="mango-section-title__main"
                  ><h2>模块进度</h2
                  ><p>{{ loading && !data ? '正在加载模块进度…' : `当前 ${filtered.length} 个模块，点击录入或自动化进度查看明细` }}</p></div
                >
                <div class="mango-section-actions mango-coverage-overview__filters">
                  <a-input
                    v-model="keyword"
                    class="mango-coverage-overview__search"
                    placeholder="搜索模块路径"
                    allow-clear
                    size="small"
                  />
                  <a-radio-group v-model="gapFilter" type="button" size="small">
                    <a-radio
                      v-for="option in overviewFilters"
                      :key="option.value"
                      :value="option.value"
                      >{{ option.label }}</a-radio
                    >
                  </a-radio-group>
                </div>
              </header>
              <div class="mango-coverage-overview__table">
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
                      <button class="mango-coverage-overview__progress" :aria-label="`查看${record.name}的接口录入明细`" @click="drill(record, 'interfaces')">
                        <span><b>{{ rate(record.binding_rate) }}</b><small>{{ record.bound_count }} / {{ record.interface_count }}</small></span>
                        <a-progress :percent="(record.binding_rate || 0) / 100" color="var(--m-chart-1)" :show-text="false" size="small" />
                      </button>
                    </template>
                    <template #automation="{ record }">
                      <button class="mango-coverage-overview__progress" :aria-label="`查看${record.name}的自动化场景明细`" @click="drill(record, 'cases')">
                        <span><b>完成率 {{ rate(record.automation_rate) }}</b><small>{{ record.completed_count }} / {{ record.target_count }}</small></span>
                        <a-progress :percent="(record.automation_rate || 0) / 100" color="var(--m-chart-2)" :show-text="false" size="small" />
                      </button>
                    </template>
                    <template #project_product="{ record }">{{ record.project_name }} / {{ record.product_name }}</template>
                    <template #actions="{ record }">
                      <MangoTableActions :actions="[{ label: '扫描记录', permission: 'api.module_coverage:detail', onClick: () => drill(record, 'scans') }]" />
                    </template>
                    <template #empty><div class="mango-empty-state">{{ loading ? '正在加载模块进度…' : '当前条件没有模块。' }}</div></template>
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
              <div v-if="!data?.interface_gaps.length" class="mango-empty-state"
                >{{ loading ? '正在加载待完成接口…' : '已发现接口暂无录入或自动化缺口，未扫描模块仍需扫描确认。' }}</div
              >
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
                  }}{{ item.target_count && item.deferred_count ? ` · 暂不处理 ${item.deferred_count}` : '' }}</span
                >
                <a-link
                  v-permission="'api.module_coverage:detail'"
                  @click="emit('interface', item.id)"
                  >查看场景</a-link
                >
              </div>
              </MangoPanelSpin>
            </section>
          </template>
        </div>
      </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
  import {
    getAutomationStatusData, getInterfaceCoverageData, overviewFilters,
    overviewModuleColumns, overviewModuleScrollX, overviewModuleScrollY,
  } from '../config'

  use([TitleComponent])

  const props = defineProps<{ data?: CoverageOverview; loading: boolean; error: boolean }>()
  const emit = defineEmits<{
    (event: 'retry'): void
    (event: 'drill', row: CoverageModuleOverview, tab: string): void
    (event: 'interface', id: number): void
  }>()
  const keyword = ref('')
  const gapFilter = ref('all')
  const pagination = usePagination(() => {})
  const scanChart = ref<HTMLElement>()
  const entryChart = ref<HTMLElement>()
  const coverageChart = ref<HTMLElement>()
  const statusChart = ref<HTMLElement>()
  const coverageData = computed(() => props.data ? getInterfaceCoverageData(props.data.summary) : [])
  const coverageDescription = computed(() =>
    `以已发现接口总数为分母，暂不处理不算已覆盖。${coverageData.value
      .map((item) => `${item.name} ${item.value} 个接口`).join('，')}`
  )
  const entryData = computed(() => {
    const summary = props.data?.summary
    return [
      { name: '已正确录入', value: summary?.bound_count || 0 },
      { name: '待录入/绑定异常', value: Math.max(0, (summary?.interface_count || 0) - (summary?.bound_count || 0)) },
    ]
  })
  const entryDescription = computed(() =>
    entryData.value.map((item) => `${item.name} ${item.value} 个接口`).join('，')
  )
  const projectScanSummary = computed(() => props.data?.project_scan_summary || props.data?.summary)
  const statusData = computed(() => (props.data ? getAutomationStatusData(props.data.summary) : []))
  const statusTotal = computed(() => statusData.value.reduce((sum, item) => sum + item.value, 0))
  const statusPercent = (value: number) =>
    statusTotal.value ? ((value * 100) / statusTotal.value).toFixed(2) : '0.00'
  const statusDescription = computed(() =>
    statusData.value.map((item) => `${item.name} ${item.value} 个场景`).join('，')
  )
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
      if (gapFilter.value === 'scan') return !row.scan_completed && row.is_leaf
      if (gapFilter.value === 'entry') return row.bound_count < row.interface_count
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
    if (row.scan_completed) return `完整扫描已生效 #${row.applied_scan_id}`
    return row.latest_scan_id ? `尚无完整扫描基线 · 最近 #${row.latest_scan_id}` : '未扫描'
  }
  function drill(row: CoverageModuleOverview, tab: string) {
    emit('drill', row, tab)
  }
  const token = (name: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  function donutStyle(
    element: HTMLElement, rows: Array<{ name: string; value: number }>, unit: string, centerText?: string
  ) {
    const total = rows.reduce((sum, item) => sum + item.value, 0)
    const text = token('--m-text-2')
    const current = useEcharts(element).getOption() as {
      legend?: Array<{ selected?: Record<string, boolean> }>
    } | undefined
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
    if (!props.data || props.error) return
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
        { name: '已完整扫描', value: projectScanSummary.value?.scanned_count || 0 },
        { name: '未完整扫描', value: projectScanSummary.value?.unscanned_count || 0 },
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
                { name: '已完整扫描', value: projectScanSummary.value?.scanned_count || 0 },
                { name: '未完整扫描', value: projectScanSummary.value?.unscanned_count || 0 },
              ],
            },
          ],
        },
        true
      )
      chart.off('click')
      chart.on('click', (event: any) => {
        gapFilter.value = event.dataIndex === 1 ? 'scan' : 'all'
      })
    }
    if (entryChart.value) {
      const chart = useEcharts(entryChart.value)
      chart.setOption({
        ...donutStyle(entryChart.value, entryData.value, '接口总数'),
        animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
        animationDuration: 280,
        color: [token('--m-success'), token('--m-warning')],
        tooltip,
        series: [{ ...donutSeries(entryChart.value, entryData.value), data: entryData.value }],
      }, true)
      chart.off('click')
      chart.on('click', (event: any) => {
        gapFilter.value = event.dataIndex === 1 ? 'entry' : 'all'
      })
    }
    if (coverageChart.value) {
      useEcharts(coverageChart.value).setOption({
        ...donutStyle(coverageChart.value, coverageData.value, '接口覆盖率',
          rate(props.data.summary.interface_coverage_rate)),
        animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
        animationDuration: 280,
        color: [token('--m-success'), token('--m-chart-1'), token('--m-warning'), token('--m-chart-5')],
        tooltip,
        series: [{ ...donutSeries(coverageChart.value, coverageData.value), data: coverageData.value }],
      }, true)
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
            formatter: (item: any) =>
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
    for (const element of [scanChart.value, entryChart.value, coverageChart.value, statusChart.value])
      if (element) useEcharts(element).resize()
    render()
  }
  async function update() {
    await nextTick()
    observer?.disconnect()
    const current = [scanChart.value, entryChart.value, coverageChart.value, statusChart.value].filter(
      (element): element is HTMLElement => !!element
    )
    for (const element of chartElements) if (!current.includes(element)) dispose(element)
    chartElements = current
    for (const element of [scanChart.value, entryChart.value, coverageChart.value, statusChart.value])
      if (element) observer?.observe(element)
    render()
  }
  watch([keyword, gapFilter, () => props.data], () => {
    pagination.page = 1
  })
  watch(() => [props.data, props.error, props.loading], update)
  onMounted(() => {
    observer = new ResizeObserver(resize)
    window.addEventListener('mango-theme-change', render)
    window.addEventListener('mango-density-change', resize)
    update()
  })
  onBeforeUnmount(() => {
    observer?.disconnect()
    window.removeEventListener('mango-theme-change', render)
    window.removeEventListener('mango-density-change', resize)
    for (const element of chartElements) dispose(element)
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
  .mango-coverage-overview__toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--m-page-gap);
  }
  .mango-coverage-overview__filters {
    flex: 0 1 auto;
    min-width: 0;
  }
  .mango-coverage-overview__search {
    flex: 1 1 16ch;
    width: auto;
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
    overscroll-behavior: contain;
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
