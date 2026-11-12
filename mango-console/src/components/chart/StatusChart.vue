<script lang="ts" setup>
  import { computed, ref, onActivated, onDeactivated, onMounted, onBeforeUnmount, watch } from 'vue'
  import useEcharts from '@/hooks/useEcharts'

  // 定义 props
  const props = defineProps<{
    success: number // 成功数据
    fail: number // 失败数据
    warning?: number // 未执行/警告（可选）
    pending?: number // 进行中（可选）
    todo?: number // 待开始（可选）
    stopped?: number // 已停止（可选）
    other?: number // 合并后的其他状态（可选）
    loading?: boolean
    totalLabel?: string
    centerLabel?: string
    centerValue?: string | number
    unit?: string
  }>()

  const pieChart = ref<HTMLElement | null>(null)
  let myChart: ReturnType<typeof useEcharts> | null = null
  let resizeObserver: ResizeObserver | null = null
  let resizeFrame = 0
  let active = true, mounted = false

  const token = (name: string, fallback: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback

  const getPalette = () => [
    token('--m-success', '#22c55e'),
    token('--m-danger', '#ef4444'),
    token('--m-warning', '#f59e0b'),
    token('--m-primary', '#165dff'),
    token('--m-muted', '#64748b'),
  ]
  const palette = ref(getPalette())

  const chartItems = computed(() => {
    const colors = palette.value
    const items = [
      { name: '通过', value: Number(props.success || 0), color: colors[0] },
      { name: '失败', value: Number(props.fail || 0), color: colors[1] },
    ]
    if (props.warning !== undefined) {
      items.push({ name: '警告', value: Number(props.warning || 0), color: colors[2] })
    }
    if (props.pending !== undefined) {
      items.push({ name: '进行中', value: Number(props.pending || 0), color: colors[3] })
    }
    if (props.todo !== undefined) {
      items.push({ name: '待开始', value: Number(props.todo || 0), color: colors[4] })
    }
    if (props.stopped !== undefined) {
      items.push({ name: '已停止', value: Number(props.stopped || 0), color: colors[4] })
    }
    if (props.other !== undefined) {
      items.push({ name: '其他', value: Number(props.other || 0), color: colors[4] })
    }
    const total = items.reduce((sum, item) => sum + item.value, 0)
    return items.map((item) => ({
      ...item,
      percent: total ? (item.value / total) * 100 : 0,
      percentText: total ? `${((item.value / total) * 100).toFixed(2)}%` : '0.00%',
    }))
  })

  const total = computed(() => chartItems.value.reduce((sum, item) => sum + item.value, 0))

  // 初始化饼状图
  const initPieChart = () => {
    if (!active || !mounted || !pieChart.value) return

    myChart = useEcharts(pieChart.value)
    updateChart()
  }

  // 动态生成饼状图数据
  const getChartData = () => {
    return chartItems.value.map((item) => ({
      value: item.value,
      name: item.name,
      itemStyle: { color: item.color },
      label: { show: item.value > 0 },
      labelLine: { show: item.value > 0 },
    }))
  }

  // 更新饼状图数据
  const updateChart = () => {
    if (!active || !mounted || !myChart) return

    myChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}<br />{d}% | {c}',
        padding: 9,
        textStyle: {
          fontSize: 14,
          lineHeight: 18,
        },
      },
      legend: { bottom: 0, left: 'center', selectedMode: false, itemWidth: 9, itemHeight: 7,
        textStyle: { color: token('--m-text-2', '#64748b'), fontSize: 11 }, data: chartItems.value.map(item => item.name) },
      series: [
        {
          name: '测试状态',
          type: 'pie',
          radius: ['40%', '58%'],
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 5,
            borderColor: token('--m-surface', '#fff'),
            borderWidth: 3,
          },
          label: {
            show: true, position: 'outside', alignTo: 'edge', edgeDistance: 8,
            color: token('--m-text-2', '#64748b'), fontSize: 11, lineHeight: 17,
            formatter(item: { name: string; value: number }) {
              return `${item.name}\n${item.value.toLocaleString('zh-CN')} ${props.unit || '个'} · ${total.value ? (item.value * 100 / total.value).toFixed(2) : '0.00'}%`
            },
          },
          labelLayout: { hideOverlap: true },
          emphasis: {
            scaleSize: 3,
          },
          labelLine: { show: true, length: 10, length2: 8, lineStyle: { color: token('--m-muted', '#64748b') } },
          data: getChartData(), // 动态生成数据
        },
      ],
    })
  }

  const updateTheme = () => {
    palette.value = getPalette()
    updateChart()
  }

  const resizeChart = () => {
    if (!active || !mounted || !myChart) return
    if (resizeFrame) window.cancelAnimationFrame(resizeFrame)
    const chart = myChart
    resizeFrame = window.requestAnimationFrame(() => {
      if (active && mounted && chart === myChart && !chart.isDisposed()) chart.resize()
      resizeFrame = 0
    })
  }

  // 监听数据变化，更新图表
  watch(
    () => [
      props.success,
      props.fail,
      props.warning,
      props.pending,
      props.todo,
      props.stopped,
      props.other,
    ],
    () => {
      updateChart()
    },
    { deep: true }
  )

  function stopCanvas() {
    resizeObserver?.disconnect()
    resizeObserver = null
    if (resizeFrame) window.cancelAnimationFrame(resizeFrame)
    resizeFrame = 0
    myChart?.dispose()
    myChart = null
  }
  function startCanvas() {
    stopCanvas()
    if (!active || !mounted || !pieChart.value) return
    palette.value = getPalette()
    initPieChart()
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(resizeChart)
      resizeObserver.observe(pieChart.value)
    }
  }
  function startChart() {
    if (!active || !mounted) return
    startCanvas()
    window.addEventListener('mango-theme-change', updateTheme)
    window.addEventListener('resize', resizeChart)
  }

  function stopChart() {
    window.removeEventListener('mango-theme-change', updateTheme)
    window.removeEventListener('resize', resizeChart)
    stopCanvas()
  }
  watch(pieChart, startCanvas, { flush: 'post' })
  onMounted(() => { mounted = true; startChart() })
  onActivated(() => { if (!active) { active = true; startChart() } })
  onDeactivated(() => { active = false; stopChart() })
  onBeforeUnmount(() => { active = false; mounted = false; stopChart() })
</script>

<template>
  <div class="mango-status-chart">
    <mango-panel-spin :loading="props.loading" class="mango-chart-spin">
      <div class="mango-status-chart__content">
        <div class="mango-status-donut">
          <div ref="pieChart" class="mango-chart"></div>
          <div class="mango-status-total">
            <strong>{{ centerValue ?? total.toLocaleString('zh-CN') }}</strong>
            <span>{{ centerLabel || totalLabel || '总数' }}</span>
          </div>
        </div>

      </div>
    </mango-panel-spin>
  </div>
</template>

<style lang="less" scoped>
  .mango-status-chart, .mango-chart-spin, :deep(.mango-chart-spin > .mango-panel-spin__content),
  .mango-status-chart__content, .mango-status-donut, .mango-chart { width: 100%; height: 100%; min-width: 0; min-height: 0; }
  .mango-status-donut { position: relative; }
  .mango-status-total { position: absolute; top: 44%; left: 50%; display: flex; width: 34%; align-items: center; justify-content: center; flex-direction: column; gap: 4px; transform: translate(-50%, -50%); pointer-events: none; }
  .mango-status-total span { color: var(--m-muted); font-size: 11px; line-height: 16px; }
  .mango-status-total strong { color: var(--m-text); font-size: 24px; font-variant-numeric: tabular-nums; line-height: 30px; white-space: nowrap; }
</style>
