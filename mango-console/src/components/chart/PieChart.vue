<template>
  <div class="mango-chart-item-container">
    <mango-panel-spin :loading="loading" class="mango-chart-spin">
      <div class="mango-chart-content">
        <div class="mango-donut-wrap">
          <div ref="chartRef" class="mango-chart-item"></div>
          <div class="mango-donut-total">
            <strong>{{ total.toLocaleString('zh-CN') }}</strong>
            <span>{{ totalLabel }}</span>
          </div>
        </div>

      </div>
    </mango-panel-spin>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
  import { dispose } from 'echarts/core'
  import useEcharts from '@/hooks/useEcharts'

  // 定义 props
  const props = defineProps({
    chartData: {
      type: Array,
      required: true,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    totalLabel: {
      type: String,
      default: '总数',
    },
  })

  const chartRef = ref<HTMLDivElement | null>(null)
  let resizeObserver: ResizeObserver | null = null
  let resizeFrame = 0
  const token = (name: string, fallback: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
  const palette = () => [
    token('--m-chart-1', '#5b7cfa'),
    token('--m-chart-2', '#7bcf65'),
    token('--m-chart-3', '#f6c143'),
    token('--m-chart-4', '#38bdf8'),
    token('--m-chart-5', '#a78bfa'),
    token('--m-primary-border', '#fb7185'),
  ]
  const testTypeColorMap = () => ({
    api: token('--m-chart-1', '#5b7cfa'),
    ui: token('--m-chart-2', '#7bcf65'),
    pytest: token('--m-chart-3', '#f6c143'),
  })

  function getTypeColor(name: string, index: number) {
    const text = String(name || '').toLowerCase()
    if (text.includes('接口') || text.includes('api')) {
      return testTypeColorMap().api
    }
    if (text.includes('界面') || text.includes('ui')) {
      return testTypeColorMap().ui
    }
    if (text.includes('单元') || text.includes('pytest') || text.includes('python')) {
      return testTypeColorMap().pytest
    }
    const colors = palette()
    return colors[index % colors.length]
  }

  const total = computed(() =>
    props.chartData.reduce((sum: number, item: any) => sum + Number(item.value || 0), 0)
  )

  const normalizedData = computed(() =>
    props.chartData.map((item: any) => {
      const value = Number(item.value || 0)
      const percent = total.value ? (value / total.value) * 100 : 0
      return {
        ...item,
        value,
        percent,
        percentText: `${percent.toFixed(2)}%`,
      }
    })
  )

  const initChart = () => {
    if (!chartRef.value) return

    const option = {
      color: normalizedData.value.map((item: any, index: number) => getTypeColor(item.name, index)),
      tooltip: {
        trigger: 'item',
        formatter: '{b}<br />{d}% | {c}',
      },
      legend: { bottom: 0, left: 'center', selectedMode: false, itemWidth: 9, itemHeight: 7,
        textStyle: { color: token('--m-text-2', '#64748b'), fontSize: 11 }, data: normalizedData.value.map((item: any) => item.name) },
      series: [
        {
          name: '访问来源',
          type: 'pie',
          center: ['50%', '44%'],
          radius: ['40%', '58%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderColor: token('--m-surface', '#fff'),
            borderWidth: 4,
            borderRadius: 6,
          },
          emphasis: { scale: false },
          label: { show: true, position: 'outside', alignTo: 'edge', edgeDistance: 8,
            color: token('--m-text-2', '#64748b'), fontSize: 11, lineHeight: 17,
            formatter(item: { name: string; value: number }) {
              return `${item.name}\n${item.value.toLocaleString('zh-CN')} 个 · ${total.value ? (item.value * 100 / total.value).toFixed(2) : '0.00'}%`
            },
          },
          labelLayout: { hideOverlap: true },
          labelLine: { show: true, length: 10, length2: 8, lineStyle: { color: token('--m-muted', '#64748b') } },
          data: normalizedData.value.map((item: any) => ({ ...item, label: { show: item.value > 0 }, labelLine: { show: item.value > 0 } })),
        },
      ],
    }

    useEcharts(chartRef.value).setOption(option)
    updateChart()
  }

  const updateChart = () => {
    if (!chartRef.value) {
      return
    }
    if (resizeFrame) {
      window.cancelAnimationFrame(resizeFrame)
    }
    resizeFrame = window.requestAnimationFrame(() => {
      if (chartRef.value) {
        useEcharts(chartRef.value).resize()
      }
      resizeFrame = 0
    })
  }

  // 监听 chartData 变化，重新渲染图表
  watch(
    () => props.chartData,
    () => {
      initChart()
    },
    { deep: true }
  )

  onMounted(() => {
    initChart()
    window.addEventListener('mango-theme-change', initChart)
    window.addEventListener('resize', updateChart)
    if (chartRef.value) {
      resizeObserver = new ResizeObserver(updateChart)
      resizeObserver.observe(chartRef.value)
    }
  })

  onBeforeUnmount(() => {
    window.removeEventListener('mango-theme-change', initChart)
    window.removeEventListener('resize', updateChart)
    resizeObserver?.disconnect()
    if (resizeFrame) {
      window.cancelAnimationFrame(resizeFrame)
    }
    if (chartRef.value) {
      dispose(chartRef.value)
    }
  })
</script>

<style lang="less" scoped>
  .mango-chart-item-container, .mango-chart-spin, :deep(.mango-chart-spin > .mango-panel-spin__content),
  .mango-chart-content, .mango-donut-wrap, .mango-chart-item { height: 100%; width: 100%; min-width: 0; min-height: 0; }
  .mango-donut-wrap { position: relative; }
  .mango-donut-total { position: absolute; top: 44%; left: 50%; display: flex; width: 34%; align-items: center; justify-content: center; flex-direction: column; gap: 4px; transform: translate(-50%, -50%); pointer-events: none; }
  .mango-donut-total span { color: var(--m-muted); font-size: 11px; line-height: 16px; }
  .mango-donut-total strong { color: var(--m-text); font-size: 24px; font-variant-numeric: tabular-nums; line-height: 30px; white-space: nowrap; }
</style>
