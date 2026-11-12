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
  import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { dispose } from 'echarts/core'
  import useEcharts from '@/hooks/useEcharts'
  import type { ProjectQualityItem } from '../../types'

  const props = defineProps<{
    data: ProjectQualityItem[]
    loading?: boolean
  }>()

  const chartRef = ref<HTMLDivElement | null>(null)
  const chartData = computed(() => (Array.isArray(props.data) ? props.data : []))
  let resizeObserver: ResizeObserver | null = null
  let resizeFrame = 0
  let active = true, mounted = false, listening = false, generation = 0
  let observedElement: HTMLDivElement | null = null

  const token = (name: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim()

  function formatNumber(value: unknown) {
    return Number(value || 0).toLocaleString('zh-CN')
  }

  function renderChart() {
    if (!active || !mounted || !chartRef.value || !chartData.value.length) return
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
          right: 28,
          bottom: 32,
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
          formatter(params: Array<{ dataIndex: number; marker?: string; seriesName?: string; value?: unknown }>) {
            if (!params?.length) return ''
            const row = rows[params[0].dataIndex]
            if (!row) return ''
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
          nameLocation: 'middle',
          nameGap: 24,
          min: 0,
          minInterval: 1,
          nameTextStyle: { color: token('--m-muted'), fontSize: 11 },
          axisLabel: { color: token('--m-muted'), fontSize: 11, hideOverlap: true, showMaxLabel: true },
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
    if (!active || !mounted || !chartRef.value) return
    if (resizeFrame) window.cancelAnimationFrame(resizeFrame)
    const current = generation, element = chartRef.value
    resizeFrame = window.requestAnimationFrame(() => {
      if (active && mounted && current === generation && chartRef.value === element) useEcharts(element).resize()
      resizeFrame = 0
    })
  }

  function observeChart() {
    if (observedElement !== chartRef.value) releaseCanvas()
    if (!active || !mounted || !chartRef.value) return
    observedElement = chartRef.value
    if (!resizeObserver && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(resizeChart)
      resizeObserver.observe(chartRef.value)
    }
    renderChart()
  }

  function releaseCanvas() {
    generation++
    resizeObserver?.disconnect()
    resizeObserver = null
    if (resizeFrame) window.cancelAnimationFrame(resizeFrame)
    resizeFrame = 0
    if (observedElement) dispose(observedElement)
    observedElement = null
  }

  watch(
    chartData,
    async () => {
      const current = generation
      await nextTick()
      if (!active || !mounted || current !== generation) return
      observeChart()
    },
    { deep: true }
  )
  watch(chartRef, observeChart, { flush: 'post' })

  function startChart() {
    if (!active || !mounted || listening) return
    listening = true
    window.addEventListener('mango-theme-change', renderChart)
    window.addEventListener('resize', resizeChart)
    observeChart()
  }

  function stopChart() {
    window.removeEventListener('mango-theme-change', renderChart)
    window.removeEventListener('resize', resizeChart)
    listening = false
    releaseCanvas()
  }
  onMounted(() => { mounted = true; startChart() })
  onActivated(() => { active = true; startChart() })
  onDeactivated(() => { active = false; stopChart() })
  onBeforeUnmount(() => { active = false; mounted = false; stopChart() })
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
