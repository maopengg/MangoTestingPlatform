<template>
  <mango-panel-spin :loading="loading" class="mango-effectiveness-chart-spin">
    <div class="mango-effectiveness-chart-wrap" :style="{ height }">
      <div ref="chartRef" class="mango-effectiveness-chart"></div>
      <div v-if="empty && !loading" class="mango-effectiveness-chart-empty">
        <EffectivenessEmptyState
          :title="emptyText"
          :description="emptyDescription"
          :positive="emptyPositive"
        />
      </div>
    </div>
    <EffectivenessAiNote v-if="!loading && !empty" :text="insight" />
  </mango-panel-spin>
</template>

<script setup lang="ts">
  import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import useEcharts from '@/hooks/useEcharts'
  import EffectivenessAiNote from './EffectivenessAiNote.vue'
  import EffectivenessEmptyState from './EffectivenessEmptyState.vue'

  const props = withDefaults(
    defineProps<{
      option: Record<string, any>
      loading?: boolean
      empty?: boolean
      emptyText?: string
      emptyDescription?: string
      emptyPositive?: boolean
      height?: string
      insight?: string
    }>(),
    {
      loading: false,
      empty: false,
      emptyText: '当前范围暂无可分析数据',
      emptyDescription: '可调整筛选周期或项目产品后重新查看',
      emptyPositive: false,
      height: '280px',
      insight: '',
    }
  )
  const emit = defineEmits<{
    (event: 'chart-click', params: any): void
  }>()

  const chartRef = ref<HTMLElement | null>(null)
  let resizeObserver: ResizeObserver | null = null

  function resolveChartTokens(value: any): any {
    if (typeof value === 'string') {
      const token = value.match(/^var\((--m-[^)]+)\)$/)?.[1]
      if (!token || !chartRef.value) return value
      return getComputedStyle(chartRef.value).getPropertyValue(token).trim() || value
    }
    if (Array.isArray(value)) return value.map(resolveChartTokens)
    if (value && typeof value === 'object') {
      return Object.fromEntries(
        Object.entries(value).map(([key, item]) => [key, resolveChartTokens(item)])
      )
    }
    return value
  }

  function renderChart() {
    if (!chartRef.value) return
    const chart = useEcharts(chartRef.value)
    chart.clear()
    chart.setOption(resolveChartTokens(props.option || {}))
    chart.off('click')
    chart.on('click', (params: any) => emit('chart-click', params))
    chart.resize()
  }

  function resizeChart() {
    if (chartRef.value) useEcharts(chartRef.value).resize()
  }

  watch(
    () => props.option,
    () => nextTick(renderChart),
    { deep: true }
  )

  onMounted(() => {
    nextTick(renderChart)
    window.addEventListener('mango-theme-change', renderChart)
    window.addEventListener('resize', resizeChart)
    if (chartRef.value) {
      resizeObserver = new ResizeObserver(resizeChart)
      resizeObserver.observe(chartRef.value)
    }
  })

  onBeforeUnmount(() => {
    window.removeEventListener('mango-theme-change', renderChart)
    window.removeEventListener('resize', resizeChart)
    resizeObserver?.disconnect()
    if (chartRef.value) useEcharts(chartRef.value).dispose()
  })
</script>

<style scoped>
  .mango-effectiveness-chart-spin,
  :deep(.mango-effectiveness-chart-spin > .mango-panel-spin__content) {
    display: flex;
    width: 100%;
    min-height: 0;
    flex: 1;
    flex-direction: column;
  }

  .mango-effectiveness-chart-wrap {
    position: relative;
    width: 100%;
    min-height: 160px;
  }

  .mango-effectiveness-chart {
    width: 100%;
    height: 100%;
  }

  .mango-effectiveness-chart-empty {
    position: absolute;
    inset: 0;
    display: flex;
    padding: 12px;
    align-items: center;
    justify-content: center;
    background: var(--m-surface);
  }
</style>
