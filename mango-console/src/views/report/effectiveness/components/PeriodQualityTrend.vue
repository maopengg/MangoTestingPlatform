<template>
  <section class="mango-period-quality-trend" :class="{ 'is-report-layout': reportMode }">
    <article
      class="mango-section-card mango-effectiveness-panel mango-period-quality-trend__current-status"
    >
      <div class="mango-period-quality-trend__title">
        <div>
          <strong>{{ currentPeriodLabel }}执行状态</strong>
          <span>查看通过、失败、警告、进行中、待开始和已停止状态占比</span>
        </div>
        <small v-if="!reportMode" :class="rateTone(currentItem?.final_pass_rate)">{{ currentRateText }}</small>
      </div>
      <StatusChart
        v-if="loading || hasCurrentData"
        :class="[
          'mango-period-quality-trend__status-chart',
          { 'is-report-layout': reportMode },
        ]"
        :success="currentItem?.success_count || 0"
        :fail="currentItem?.failed_count || 0"
        :warning="currentItem?.warning_count || 0"
        :pending="currentItem?.proceed_count || 0"
        :todo="currentItem?.stay_begin_count || 0"
        :stopped="currentItem?.stopped_count || 0"
        :loading="loading"
        center-label="最终通过率"
        :center-value="currentRateText"
      />
      <EffectivenessEmptyState
        v-else
        title="当前周期暂无执行状态数据"
        description="当前筛选范围内尚未生成正式定时任务执行结果"
      />
    </article>

    <article
      class="mango-section-card mango-effectiveness-panel mango-period-quality-trend__comparison"
    >
      <div class="mango-period-quality-trend__title">
        <div>
          <strong>四周期质量环比</strong>
          <span>{{ subtitle }}</span>
        </div>
        <small :class="deltaTone">{{ deltaText }}</small>
      </div>

      <EffectivenessChart
        :option="chartOption"
        :loading="loading"
        :empty="!hasData"
        empty-text="连续四个周期内暂无正式定时任务数据"
        :insight="insight"
        height="300px"
        @chart-click="onChartClick"
      />

      <div v-if="hasData" class="mango-period-quality-trend__periods">
        <article v-for="item in normalizedItems" :key="item.key"
          :class="{ 'is-current': item.key === 'current' }">
          <div>
            <strong>{{ item.displayLabel }}</strong>
            <span :title="item.dateText">{{ item.dateText }}</span>
          </div>
          <strong :class="rateTone(item.final_pass_rate)">{{
            formatRate(item.final_pass_rate)
          }}</strong>
          <small>
            {{ item.detail_count }} 次执行 · {{ item.failed_count }} 失败 ·
            {{ item.warning_count }} 警告
          </small>
        </article>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import StatusChart from '@/components/chart/StatusChart.vue'
  import EffectivenessChart from './EffectivenessChart.vue'
  import EffectivenessEmptyState from './EffectivenessEmptyState.vue'

  interface PeriodQualityItem {
    key: string
    label?: string
    start?: string
    end?: string
    suite_count?: number
    detail_count?: number
    success_count?: number
    failed_count?: number
    warning_count?: number
    proceed_count?: number
    stay_begin_count?: number
    stopped_count?: number
    unfinished_count?: number
    final_pass_rate?: number | null
  }

  const props = withDefaults(
    defineProps<{
      items?: PeriodQualityItem[]
      loading?: boolean
      insight?: string
      reportMode?: boolean
    }>(),
    {
      items: () => [],
      loading: false,
      insight: '',
      reportMode: false,
    }
  )
  const emit = defineEmits<{
    (event: 'period-click', item: PeriodQualityItem): void
  }>()

  function dateValue(value?: string) {
    const date = String(value || '').slice(0, 10)
    return date ? new Date(`${date}T00:00:00`) : null
  }

  function dateText(value?: string) {
    return String(value || '').slice(0, 10) || '-'
  }

  function inclusiveDays(item?: PeriodQualityItem) {
    const start = dateValue(item?.start)
    const end = dateValue(item?.end)
    if (!start || !end) return 0
    return Math.max(Math.round((end.getTime() - start.getTime()) / 86400000) + 1, 1)
  }

  const periodDays = computed(() => inclusiveDays(props.items[props.items.length - 1]))
  const labelMap: Record<string, string> = {
    three_periods_ago: '前三周期',
    two_periods_ago: '前二周期',
    previous: '上一周期',
    current: '当前周期',
  }
  const normalizedItems = computed(() =>
    props.items.map((item) => ({
      ...item,
      displayLabel: labelMap[item.key] || item.label || '周期',
      dateText: `${dateText(item.start)} 至 ${dateText(item.end)}`,
      suite_count: Number(item.suite_count || 0),
      detail_count: Number(item.detail_count || 0),
      success_count: Number(item.success_count || 0),
      failed_count: Number(item.failed_count || 0),
      warning_count: Number(item.warning_count || 0),
      proceed_count: Number(item.proceed_count || 0),
      stay_begin_count: Number(item.stay_begin_count || 0),
      stopped_count: Number(item.stopped_count || 0),
      unfinished_count: Number(item.unfinished_count || 0),
    }))
  )
  const hasData = computed(() => normalizedItems.value.some((item) => item.suite_count > 0))
  const subtitle = computed(() =>
    periodDays.value
      ? `按当前筛选的 ${periodDays.value} 天周期，对比连续四个等长周期的问题结果与最终通过率`
      : '对比连续四个等长周期的问题结果与最终通过率'
  )
  const currentItem = computed(() => normalizedItems.value.find((item) => item.key === 'current'))
  const currentPeriodLabel = computed(() => labelMap.current || '当前周期')
  const currentRateText = computed(() => formatRate(currentItem.value?.final_pass_rate))
  const currentStatusTotal = computed(() => {
    const item = currentItem.value
    if (!item) return 0
    return (
      item.success_count +
      item.failed_count +
      item.warning_count +
      item.proceed_count +
      item.stay_begin_count +
      item.stopped_count
    )
  })
  const hasCurrentData = computed(() => currentStatusTotal.value > 0)
  const previousItem = computed(() => normalizedItems.value.find((item) => item.key === 'previous'))
  const passRateDelta = computed(() => {
    const current = currentItem.value?.final_pass_rate
    const previous = previousItem.value?.final_pass_rate
    if (current === null || current === undefined || previous === null || previous === undefined)
      return null
    return Number((Number(current) - Number(previous)).toFixed(2))
  })
  const deltaText = computed(() => {
    if (passRateDelta.value === null) return '暂无完整环比数据'
    if (passRateDelta.value === 0) return '最终通过率与上一周期持平'
    return `最终通过率较上一周期${passRateDelta.value > 0 ? '提升' : '下降'} ${Math.abs(
      passRateDelta.value
    )} 个百分点`
  })
  const deltaTone = computed(() => {
    if (passRateDelta.value === null || passRateDelta.value === 0) return ''
    return passRateDelta.value > 0 ? 'is-success' : 'is-danger'
  })

  function formatRate(value?: number | null) {
    return value === null || value === undefined ? '-' : `${Number(value).toFixed(2)}%`
  }

  function rateTone(value?: number | null) {
    if (value === null || value === undefined) return ''
    if (Number(value) >= 90) return 'is-success'
    if (Number(value) < 80) return 'is-danger'
    return 'is-warning'
  }

  const chartOption = computed(() => ({
    animationDuration: 500,
    tooltip: {
      trigger: 'axis',
      confine: true,
      axisPointer: { type: 'shadow' },
      formatter(params: any[]) {
        const index = Number(params?.[0]?.dataIndex || 0)
        const item = normalizedItems.value[index]
        if (!item) return ''
        return [
          `<strong>${item.displayLabel}</strong>`,
          item.dateText,
          `执行用例：${item.detail_count}`,
          `通过：${item.success_count}`,
          `失败：${item.failed_count}`,
          `警告：${item.warning_count}`,
          `进行中：${item.proceed_count}`,
          `待开始：${item.stay_begin_count}`,
          `已停止：${item.stopped_count}`,
          `最终通过率：${formatRate(item.final_pass_rate)}`,
        ].join('<br/>')
      },
    },
    legend: {
      top: 0,
      itemWidth: 13,
      itemHeight: 8,
      textStyle: { color: 'var(--m-text-2)' },
      selected: { 通过: false },
      data: ['通过', '失败', '警告', '进行中', '待开始', '已停止', '最终通过率'],
    },
    grid: { left: 40, right: 44, top: 44, bottom: 28, containLabel: true },
    xAxis: {
      type: 'category',
      data: normalizedItems.value.map((item) => item.displayLabel),
      axisLabel: { color: 'var(--m-text-2)' },
      axisTick: { alignWithLabel: true },
    },
    yAxis: [
      {
        type: 'value',
        minInterval: 1,
        name: '问题结果',
        axisLabel: { color: 'var(--m-muted)' },
        splitLine: { lineStyle: { color: 'var(--m-border)' } },
      },
      {
        type: 'value',
        min: 0,
        max: 100,
        name: '通过率',
        axisLabel: { formatter: '{value}%', color: 'var(--m-muted)' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '通过',
        type: 'bar',
        stack: 'result',
        barMaxWidth: 62,
        data: normalizedItems.value.map((item) => item.success_count),
        itemStyle: { color: 'var(--m-success)' },
      },
      {
        name: '已停止',
        type: 'bar',
        stack: 'result',
        barMaxWidth: 62,
        data: normalizedItems.value.map((item) => item.stopped_count),
        itemStyle: { color: 'var(--m-muted)' },
      },
      {
        name: '待开始',
        type: 'bar',
        stack: 'result',
        barMaxWidth: 62,
        data: normalizedItems.value.map((item) => item.stay_begin_count),
        itemStyle: { color: 'var(--m-chart-1)' },
      },
      {
        name: '进行中',
        type: 'bar',
        stack: 'result',
        barMaxWidth: 62,
        data: normalizedItems.value.map((item) => item.proceed_count),
        itemStyle: { color: 'var(--m-primary)' },
      },
      {
        name: '失败',
        type: 'bar',
        stack: 'result',
        barMaxWidth: 62,
        data: normalizedItems.value.map((item) => item.failed_count),
        itemStyle: { color: 'var(--m-danger)' },
      },
      {
        name: '警告',
        type: 'bar',
        stack: 'result',
        barMaxWidth: 62,
        data: normalizedItems.value.map((item) => item.warning_count),
        itemStyle: { color: 'var(--m-warning)', borderRadius: [3, 3, 0, 0] },
      },
      {
        name: '最终通过率',
        type: 'line',
        yAxisIndex: 1,
        data: normalizedItems.value.map((item) => item.final_pass_rate),
        symbol: 'circle',
        symbolSize: 8,
        z: 5,
        connectNulls: false,
        lineStyle: { color: 'var(--m-success)', width: 3 },
        itemStyle: {
          color: 'var(--m-surface)',
          borderColor: 'var(--m-success)',
          borderWidth: 3,
        },
        emphasis: {
          focus: 'none',
          lineStyle: { color: 'var(--m-success)', width: 3, opacity: 1 },
          itemStyle: {
            color: 'var(--m-surface)',
            borderColor: 'var(--m-success)',
            opacity: 1,
          },
        },
        blur: { lineStyle: { opacity: 1 }, itemStyle: { opacity: 1 } },
      },
    ],
  }))

  function onChartClick(params: any) {
    const item = props.items[Number(params?.dataIndex)]
    if (item) emit('period-click', item)
  }

</script>

<style scoped>
  .mango-period-quality-trend {
    display: grid;
    min-width: 0;
    grid-template-columns: minmax(300px, 0.72fr) minmax(0, 1.58fr);
    align-items: stretch;
    gap: var(--m-page-gap);
  }

  .mango-period-quality-trend__current-status,
  .mango-period-quality-trend__comparison {
    display: flex;
    min-width: 0;
    padding-bottom: 10px;
    flex-direction: column;
  }

  .mango-period-quality-trend > .mango-period-quality-trend__comparison {
    margin-top: 0;
  }

  .mango-period-quality-trend__title {
    display: flex;
    min-width: 0;
    padding-bottom: 9px;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-period-quality-trend__title > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 3px;
    flex: 1 1 220px;
  }

  .mango-period-quality-trend__title strong {
    color: var(--m-text);
    font-size: 15px;
  }

  .mango-period-quality-trend__title span,
  .mango-period-quality-trend__title small,
  .mango-period-quality-trend__periods span,
  .mango-period-quality-trend__periods small {
    color: var(--m-muted);
    font-size: 11px;
    line-height: 18px;
  }

  .mango-period-quality-trend__title > small {
    padding: 3px 7px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    max-width: 100%;
    overflow-wrap: anywhere;
  }

  .mango-period-quality-trend__title > small.is-success,
  .mango-period-quality-trend__periods strong.is-success {
    color: var(--m-success);
  }

  .mango-period-quality-trend__title > small.is-danger,
  .mango-period-quality-trend__periods strong.is-danger {
    color: var(--m-danger);
  }

  .mango-period-quality-trend__periods strong.is-warning {
    color: var(--m-warning);
  }

  .mango-period-quality-trend__status-chart {
    height: 300px;
  }

  .mango-period-quality-trend__status-chart.is-report-layout {
    height: 430px;
  }

  .mango-period-quality-trend__status-chart.is-report-layout
    :deep(.mango-status-chart__content) {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: 190px minmax(0, 1fr);
    align-content: center;
    gap: 10px;
  }

  .mango-period-quality-trend__status-chart.is-report-layout :deep(.mango-status-donut) {
    width: min(100%, 220px);
    height: 190px;
    min-height: 190px;
    justify-self: center;
  }

  .mango-period-quality-trend__status-chart.is-report-layout :deep(.mango-status-list) {
    width: 100%;
    height: auto;
    padding: 0 12px;
    box-sizing: border-box;
  }

  .mango-period-quality-trend__periods {
    display: grid;
    margin-top: var(--m-page-gap);
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
    gap: var(--m-page-gap);
  }

  .mango-period-quality-trend__periods article {
    display: grid;
    min-width: 0;
    padding: 12px;
    grid-template-columns: minmax(0, 1fr);
    gap: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-period-quality-trend__periods article > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
  }

  .mango-period-quality-trend__periods article > div > strong {
    color: var(--m-text);
    font-size: var(--m-font-body);
    white-space: nowrap;
  }

  .mango-period-quality-trend__periods article > div > span {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .mango-period-quality-trend__periods article.is-current {
    border-color: var(--m-primary);
  }

  .mango-period-quality-trend__periods article > strong {
    align-self: center;
    font-size: 22px;
    line-height: 1.2;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  .mango-period-quality-trend__periods article > small {
    grid-column: 1 / -1;
    padding-top: 8px;
    border-top: 1px solid var(--m-border);
    overflow-wrap: break-word;
  }

  @media (max-width: 900px) {
    .mango-period-quality-trend,
    .mango-period-quality-trend__periods {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
