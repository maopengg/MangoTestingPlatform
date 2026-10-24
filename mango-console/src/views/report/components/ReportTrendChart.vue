<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import type { ECharts } from 'echarts'
  import useEcharts from '@/hooks/useEcharts'

  interface TrendItem {
    label: string
    batch_count: number
    scheduled_count: number
    other_count?: number
    success_count: number
    fail_count: number
    warning_count: number
    pass_rate: number | null
  }

  const props = defineProps<{
    items: TrendItem[]
    loading?: boolean
  }>()

  const chartRef = ref<HTMLElement | null>(null)
  let chart: ECharts | null = null
  let resizeObserver: ResizeObserver | null = null
  let resizeFrame = 0
  const batchTotal = computed(() =>
    props.items.reduce((sum, item) => sum + Number(item.batch_count || 0), 0)
  )
  const scheduledTotal = computed(() =>
    props.items.reduce((sum, item) => sum + Number(item.scheduled_count || 0), 0)
  )
  const otherTotal = computed(() =>
    props.items.reduce((sum, item) => sum + Number(item.other_count || 0), 0)
  )
  const total = computed(() => batchTotal.value + scheduledTotal.value + otherTotal.value)
  const token = (name: string, fallback: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback

  function shouldShowTrendLabel(index: number) {
    const itemCount = props.items.length
    if (itemCount <= 2) return true
    const chartWidth = chartRef.value?.clientWidth || 0
    const longestLabelLength = props.items.reduce(
      (maxLength, item) => Math.max(maxLength, String(item.label || '').length),
      0
    )
    const estimatedLabelWidth = Math.max(76, longestLabelLength * 6.5 + 20)
    const availableWidth = Math.max(chartWidth - 110, estimatedLabelWidth * 2)
    const visibleLabelCount = Math.max(
      2,
      Math.min(itemCount, Math.floor(availableWidth / estimatedLabelWidth))
    )
    const labelStep = Math.max(1, Math.ceil((itemCount - 1) / (visibleLabelCount - 1)))
    return index === 0 || index === itemCount - 1 || index % labelStep === 0
  }

  function resizeChart() {
    if (!chart) return
    if (resizeFrame) cancelAnimationFrame(resizeFrame)
    resizeFrame = requestAnimationFrame(() => {
      chart?.resize()
      resizeFrame = 0
    })
  }

  function updateChart() {
    if (!chart) return
    const primary = token('--m-chart-1', '#1e40af')
    const scheduled = token('--m-chart-3', '#d97706')
    const other = token('--m-chart-5', '#64748b')
    const success = token('--m-success', '#00b42a')
    const muted = token('--m-muted', '#86909c')
    chart.setOption(
      {
        color: [primary, scheduled, other, success],
        tooltip: {
          trigger: 'axis',
          confine: true,
          backgroundColor: token('--m-surface', '#fff'),
          borderColor: token('--m-border', '#e5e6eb'),
          textStyle: { color: token('--m-text', '#1d2129') },
          formatter(params: any[]) {
            const index = Number(params?.[0]?.dataIndex || 0)
            const item = props.items[index]
            if (!item) return ''
            const rate = item.pass_rate === null ? '-' : `${item.pass_rate.toFixed(2)}%`
            return [
              `<strong>${item.label}</strong>`,
              `批量执行：${item.batch_count} 份`,
              `定时任务：${item.scheduled_count} 份`,
              ...(item.other_count ? [`其他执行：${item.other_count} 份`] : []),
              `通过 / 失败 / 警告：${item.success_count} / ${item.fail_count} / ${item.warning_count}`,
              `最终通过率：${rate}`,
            ].join('<br />')
          },
        },
        legend: {
          top: 2,
          itemWidth: 12,
          itemHeight: 8,
          textStyle: { color: token('--m-text-2', '#4e5969') },
        },
        grid: { top: 36, right: 46, bottom: 38, left: 8, containLabel: true },
        xAxis: {
          type: 'category',
          data: props.items.map((item) => item.label),
          axisTick: { show: false },
          axisLine: { lineStyle: { color: token('--m-border-strong', '#c9cdd4') } },
          axisLabel: {
            show: true,
            color: muted,
            fontSize: 11,
            margin: 10,
            hideOverlap: false,
            interval: (index: number) => shouldShowTrendLabel(index),
          },
        },
        yAxis: [
          {
            type: 'value',
            minInterval: 1,
            name: '报告数',
            nameTextStyle: { color: muted },
            axisLabel: { color: muted },
            splitLine: { lineStyle: { color: token('--m-border', '#e5e6eb'), type: 'dashed' } },
          },
          {
            type: 'value',
            min: 0,
            max: 100,
            name: '通过率',
            nameTextStyle: { color: muted },
            axisLabel: { color: muted, formatter: '{value}%' },
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: '批量执行',
            type: 'bar',
            stack: 'source',
            barMaxWidth: 26,
            data: props.items.map((item) => item.batch_count),
            itemStyle: { color: primary, borderRadius: [3, 3, 0, 0] },
            emphasis: { focus: 'none', itemStyle: { color: primary } },
          },
          {
            name: '定时任务',
            type: 'bar',
            stack: 'source',
            barMaxWidth: 26,
            data: props.items.map((item) => item.scheduled_count),
            itemStyle: { color: scheduled, borderRadius: [3, 3, 0, 0] },
            emphasis: { focus: 'none', itemStyle: { color: scheduled } },
          },
          {
            name: '其他执行',
            type: 'bar',
            stack: 'source',
            barMaxWidth: 26,
            data: props.items.map((item) => Number(item.other_count || 0)),
            itemStyle: { color: other, borderRadius: [3, 3, 0, 0] },
            emphasis: { focus: 'none', itemStyle: { color: other } },
          },
          {
            name: '最终通过率',
            type: 'line',
            yAxisIndex: 1,
            connectNulls: false,
            symbol: 'circle',
            symbolSize: 7,
            data: props.items.map((item) => item.pass_rate),
            lineStyle: { width: 2, color: success },
            itemStyle: {
              color: token('--m-surface', '#fff'),
              borderColor: success,
              borderWidth: 2,
            },
            emphasis: {
              focus: 'none',
              lineStyle: { width: 2, color: success },
              itemStyle: {
                color: token('--m-surface', '#fff'),
                borderColor: success,
                borderWidth: 2,
              },
            },
          },
        ],
      },
      true
    )
    resizeChart()
  }

  watch(() => props.items, updateChart, { deep: true })

  onMounted(async () => {
    await nextTick()
    if (!chartRef.value) return
    chart = useEcharts(chartRef.value)
    updateChart()
    resizeObserver = new ResizeObserver(resizeChart)
    resizeObserver.observe(chartRef.value)
    window.addEventListener('mango-theme-change', updateChart)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('mango-theme-change', updateChart)
    resizeObserver?.disconnect()
    if (resizeFrame) cancelAnimationFrame(resizeFrame)
    chart?.dispose()
  })
</script>

<template>
  <div class="mango-report-source-trend">
    <mango-panel-spin :loading="loading" class="mango-report-source-trend__spin">
      <div class="mango-report-source-trend__summary">
        <span
          >共 <strong>{{ total }}</strong> 份</span
        >
        <span
          >批量执行 <strong>{{ batchTotal }}</strong></span
        >
        <span
          >定时任务 <strong>{{ scheduledTotal }}</strong></span
        >
        <span v-if="otherTotal"
          >其他执行 <strong>{{ otherTotal }}</strong></span
        >
      </div>
      <div ref="chartRef" class="mango-report-source-trend__chart"></div>
    </mango-panel-spin>
  </div>
</template>

<style lang="less" scoped>
  .mango-report-source-trend,
  .mango-report-source-trend__spin {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  :deep(.mango-report-source-trend__spin > .mango-panel-spin__content) {
    display: flex;
    width: 100%;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }

  .mango-report-source-trend__summary {
    display: flex;
    padding: 4px 8px 0;
    color: var(--m-muted);
    font-size: 12px;
    gap: 16px;

    strong {
      color: var(--m-text);
      font-size: 14px;
    }
  }

  .mango-report-source-trend__chart {
    width: 100%;
    height: 210px;
    min-height: 180px;
    flex: 1;
  }
</style>
