<template>
  <mango-panel-spin :loading="loading || rendering" class="mango-effectiveness-chart-spin">
    <div class="mango-effectiveness-chart-wrap" :style="{ height: chartHeight }">
      <div ref="chartRef" class="mango-effectiveness-chart"></div>
      <MangoRequestFeedback v-if="renderError && !loading" :message="(renderError)"><a-button size="small" :loading="rendering" @click="scheduleRender">重试</a-button></MangoRequestFeedback>
      <div v-else-if="empty && !loading && !rendering" class="mango-effectiveness-chart-empty">
        <EffectivenessEmptyState
          :title="emptyText"
          :description="emptyDescription"
          :positive="emptyPositive"
        />
      </div>
    </div>
    <EffectivenessAiNote v-if="!loading && !rendering && !renderError && !empty" :text="insight" />
  </mango-panel-spin>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import useEcharts from '@/hooks/useEcharts'
  import { scaleDensityLength } from '@/hooks/useDisplayDensity'
  import { resolveChartOption } from '../chart-boundary'
  import EffectivenessAiNote from './EffectivenessAiNote.vue'
  import EffectivenessEmptyState from './EffectivenessEmptyState.vue'

  const props = withDefaults(defineProps<{
    option: unknown
    loading?: boolean
    empty?: boolean
    emptyText?: string
    emptyDescription?: string
    emptyPositive?: boolean
    height?: string
    insight?: string
  }>(), {
    loading: false, empty: false, emptyText: '当前范围暂无可分析数据',
    emptyDescription: '可调整筛选周期或项目产品后重新查看', emptyPositive: false,
    height: '280px', insight: '',
  })
  const emit = defineEmits<{ (event: 'chart-click', params: unknown): void }>()
  const route = useRoute(), pagePath = route.path
  const chartRef = ref<HTMLElement | null>(null)
  const chartHeight = computed(() => {
    const value = scaleDensityLength(props.height)
    return typeof value === 'string' ? value : props.height
  })
  const rendering = ref(false), renderError = ref('')
  let chart: ReturnType<typeof useEcharts> | null = null
  let chartClick: ((params: unknown) => void) | null = null
  let resizeObserver: ResizeObserver | null = null
  let mounted = false, active = true, disposed = false, generation = 0
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  function click(params: unknown) { if (available() && !props.loading && !rendering.value && !renderError.value) emit('chart-click', params) }
  function disposeChart() {
    if (!chart) return
    if (chartClick) chart.off('click', chartClick)
    if (!chart.isDisposed()) chart.dispose()
    chart = null
    chartClick = null
  }
  function renderChart() {
    if (!available() || props.loading || !chartRef.value) return
    const node = chartRef.value
    const option = resolveChartOption(props.option, key => getComputedStyle(node).getPropertyValue(key))
    if (!chart || chart.isDisposed()) {
      chart = useEcharts(node)
    }
    chart.clear()
    chart.setOption(option)
    if (chartClick) chart.off('click', chartClick)
    const instance = chart, currentGeneration = generation
    chartClick = params => { if (chart === instance && generation === currentGeneration) click(params) }
    chart.on('click', chartClick)
    chart.resize()
  }
  function scheduleRender(): Promise<void> {
    const currentGeneration = ++generation
    if (!available() || props.loading) { rendering.value = false; return Promise.resolve() }
    rendering.value = true
    renderError.value = ''
    return nextTick().then(() => {
      if (currentGeneration !== generation || !available() || props.loading) return
      try { renderChart() }
      catch (loadFailure0) { if (available() && currentGeneration === generation) (reportLoadError(loadFailure0, "图表加载失败，请重试", false), renderError.value = '图表加载失败，请重试') }
      finally { if (currentGeneration === generation) rendering.value = false }
    }).catch((loadFailure1) => {
      if (available() && currentGeneration === generation) {
        void (reportLoadError(loadFailure1, "图表加载失败，请重试", false), renderError.value = '图表加载失败，请重试')
        rendering.value = false
      }
    })
  }
  function resizeChart() {
    if (!available() || props.loading || !chart || chart.isDisposed()) return
    try { chart.resize() } catch (loadFailure2) { (reportLoadError(loadFailure2, "图表加载失败，请重试", false), renderError.value = '图表加载失败，请重试') }
  }
  function pause() { generation++; rendering.value = false; resizeObserver?.disconnect(); disposeChart() }
  function resume() {
    if (!available()) return
    if (chartRef.value) resizeObserver?.observe(chartRef.value)
    void scheduleRender()
  }
  function visibilityChanged() { if (available()) resume(); else pause() }
  watch([() => props.option, () => props.loading, () => props.height], () => { void scheduleRender() }, { deep: true })
  watch(chartRef, (node, previous) => {
    if (node === previous) return
    generation++
    resizeObserver?.disconnect()
    disposeChart()
    if (available() && node) { resizeObserver?.observe(node); void scheduleRender() }
  }, { flush: 'sync' })
  watch(() => route.path, visibilityChanged, { flush: 'sync' })
  onMounted(() => {
    mounted = true
    if (typeof ResizeObserver !== 'undefined') resizeObserver = new ResizeObserver(resizeChart)
    window.addEventListener('mango-theme-change', resume)
    window.addEventListener('mango-density-change', resume)
    window.addEventListener('resize', resizeChart)
    document.addEventListener('visibilitychange', visibilityChanged)
    resume()
  })
  onDeactivated(() => { active = false; pause() })
  onActivated(() => { const inactive = !active; active = true; if (inactive) resume() })
  onBeforeUnmount(() => {
    disposed = true
    pause()
    window.removeEventListener('mango-theme-change', resume)
    window.removeEventListener('mango-density-change', resume)
    window.removeEventListener('resize', resizeChart)
    document.removeEventListener('visibilitychange', visibilityChanged)
    disposeChart()
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
