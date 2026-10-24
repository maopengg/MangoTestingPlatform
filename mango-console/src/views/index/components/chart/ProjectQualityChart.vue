<template>
  <div class="mango-project-quality-chart">
    <mango-panel-spin :loading="loading" class="mango-project-quality-chart__spin">
      <div v-if="chartData.length" ref="chartRef" class="mango-project-quality-chart__canvas"></div>
      <div v-else-if="!loading" class="mango-empty-state mango-project-quality-chart__empty">
        暂无定时任务执行报告
      </div>
    </mango-panel-spin>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { dispose } from 'echarts/core'
  import useEcharts from '@/hooks/useEcharts'

  interface ProjectQualityItem {
    project_id: number
    project_name: string
    report_count: number
    success_count: number
    fail_count: number
    warning_count: number
    other_count: number
    pass_rate: number | null
  }

  const props = defineProps<{
    data: ProjectQualityItem[]
    loading?: boolean
  }>()

  const chartRef = ref<HTMLDivElement | null>(null)
  const chartData = computed(() => (Array.isArray(props.data) ? props.data : []))
  let resizeObserver: ResizeObserver | null = null
  let resizeFrame = 0

  const token = (name: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim()

  function formatNumber(value: unknown) {
    return Number(value || 0).toLocaleString('zh-CN')
  }

  function renderChart() {
    if (!chartRef.value || !chartData.value.length) return
    const rows = chartData.value
    const names = rows.map((item) => item.project_name || `项目 ${item.project_id}`)
    const visibleRows = Math.min(rows.length, 4)
    const dataZoom =
      rows.length > visibleRows
        ? [
            {
              type: 'inside',
              yAxisIndex: 0,
              startValue: 0,
              endValue: visibleRows - 1,
              zoomLock: true,
            },
          ]
        : []

    useEcharts(chartRef.value).setOption(
      {
        animationDuration: 280,
        color: [
          token('--m-success'),
          token('--m-danger'),
          token('--m-warning'),
          token('--m-muted'),
        ],
        grid: {
          top: 32,
          right: 10,
          bottom: 12,
          left: 7,
          containLabel: true,
        },
        legend: {
          top: 3.6,
          right: 8,
          itemWidth: 10,
          itemHeight: 8,
          textStyle: { color: token('--m-text-2'), fontSize: 11 },
          data: ['通过', '失败', '警告', '其他'],
        },
        tooltip: {
          trigger: 'axis',
          confine: true,
          axisPointer: { type: 'shadow' },
          backgroundColor: token('--m-surface'),
          borderColor: token('--m-border'),
          textStyle: { color: token('--m-text') },
          padding: 9,
          formatter(params: any[]) {
            if (!params?.length) return ''
            const row = rows[params[0].dataIndex]
            const passRate = row.pass_rate === null ? '-' : `${row.pass_rate.toFixed(2)}%`
            return [
              `<strong>${row.project_name}</strong>`,
              `定时任务报告：${formatNumber(row.report_count)} 份`,
              ...params.map(
                (item) => `${item.marker}${item.seriesName}：${formatNumber(item.value)} 份`
              ),
              `最终通过率：${passRate}`,
            ].join('<br />')
          },
        },
        xAxis: {
          type: 'value',
          name: '报告数（份）',
          nameLocation: 'end',
          nameGap: 6,
          min: 0,
          minInterval: 1,
          nameTextStyle: { color: token('--m-muted'), fontSize: 11 },
          axisLabel: { color: token('--m-muted'), fontSize: 11 },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: {
            lineStyle: { color: token('--m-border'), type: 'dashed' },
          },
        },
        yAxis: {
          type: 'category',
          inverse: true,
          data: names,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            width: 64,
            overflow: 'truncate',
            color: token('--m-text-2'),
            fontSize: 11,
          },
        },
        dataZoom,
        series: [
          {
            name: '通过',
            type: 'bar',
            stack: 'result',
            barMaxWidth: 16,
            data: rows.map((item) => item.success_count),
            emphasis: { focus: 'none' },
          },
          {
            name: '失败',
            type: 'bar',
            stack: 'result',
            barMaxWidth: 16,
            data: rows.map((item) => item.fail_count),
            emphasis: { focus: 'none' },
          },
          {
            name: '警告',
            type: 'bar',
            stack: 'result',
            barMaxWidth: 16,
            data: rows.map((item) => item.warning_count),
            emphasis: { focus: 'none' },
          },
          {
            name: '其他',
            type: 'bar',
            stack: 'result',
            barMaxWidth: 16,
            data: rows.map((item) => item.other_count),
            emphasis: { focus: 'none' },
          },
        ],
      },
      true
    )
  }

  function resizeChart() {
    if (!chartRef.value) return
    if (resizeFrame) window.cancelAnimationFrame(resizeFrame)
    resizeFrame = window.requestAnimationFrame(() => {
      if (chartRef.value) useEcharts(chartRef.value).resize()
      resizeFrame = 0
    })
  }

  function observeChart() {
    if (!chartRef.value || resizeObserver) return
    resizeObserver = new ResizeObserver(resizeChart)
    resizeObserver.observe(chartRef.value)
  }

  watch(
    chartData,
    async () => {
      await nextTick()
      observeChart()
      renderChart()
    },
    { deep: true }
  )

  onMounted(() => {
    window.addEventListener('mango-theme-change', renderChart)
    window.addEventListener('resize', resizeChart)
    nextTick(() => {
      observeChart()
      renderChart()
    })
  })

  onBeforeUnmount(() => {
    window.removeEventListener('mango-theme-change', renderChart)
    window.removeEventListener('resize', resizeChart)
    resizeObserver?.disconnect()
    if (resizeFrame) window.cancelAnimationFrame(resizeFrame)
    if (chartRef.value) dispose(chartRef.value)
  })
</script>

<style lang="less" scoped>
  .mango-project-quality-chart {
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  .mango-project-quality-chart__spin,
  :deep(.mango-project-quality-chart__spin > .mango-panel-spin__content) {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  .mango-project-quality-chart__canvas {
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  .mango-project-quality-chart__empty {
    display: flex;
    height: 100%;
    min-height: 120px;
    align-items: center;
    justify-content: center;
  }
</style>
