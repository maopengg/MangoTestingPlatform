<script lang="ts" setup>
  import { computed, ref } from 'vue'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import EffectivenessChart from '../effectiveness/components/EffectivenessChart.vue'
  import { chartHtml, chartPoints } from '../effectiveness/chart-boundary'
  import { parseReportTrendItems } from '../report-list'

  const props = defineProps<{ items: unknown; loading?: boolean }>()
  const chartContainer = ref<HTMLElement | null>(null)
  const items = computed(() => parseReportTrendItems(props.items))
  const batchTotal = computed(() => items.value.reduce((sum, item) => sum + item.batch_count, 0))
  const scheduledTotal = computed(() => items.value.reduce((sum, item) => sum + item.scheduled_count, 0))
  const otherTotal = computed(() => items.value.reduce((sum, item) => sum + item.other_count, 0))
  const total = computed(() => batchTotal.value + scheduledTotal.value + otherTotal.value)
  function shouldShowTrendLabel(index: number) {
    const count = items.value.length
    if (!Number.isInteger(index) || index < 0 || index >= count) return false
    if (count <= 2) return true
    const longest = items.value.reduce((size, item) => Math.max(size, item.label.length), 0)
    const estimated = scaleDensityPixels(Math.max(76, longest * 6.5 + 20))
    const width = Math.max((chartContainer.value?.clientWidth || 0) - scaleDensityPixels(110), estimated * 2)
    const visible = Math.max(2, Math.min(count, Math.floor(width / estimated)))
    const step = Math.max(1, Math.ceil((count - 1) / (visible - 1)))
    return index === 0 || index === count - 1 || index % step === 0
  }
  function tooltip(params: unknown) {
    const index = chartPoints(params)[0]?.dataIndex
    if (index === null || index === undefined) return ''
    const item = items.value[index]
    if (!item) return ''
    return [
      `<strong>${chartHtml(item.label)}</strong>`, `批量执行：${item.batch_count} 份`, `定时任务：${item.scheduled_count} 份`,
      ...(item.other_count ? [`其他执行：${item.other_count} 份`] : []),
      `通过 / 失败 / 警告：${item.success_count} / ${item.fail_count} / ${item.warning_count}`,
      `最终通过率：${item.pass_rate === null ? '-' : `${item.pass_rate.toFixed(2)}%`}`,
    ].join('<br />')
  }
  const chartOption = computed(() => {
    const primary = 'var(--m-chart-1)', scheduled = 'var(--m-chart-3)', other = 'var(--m-chart-5)', success = 'var(--m-success)', muted = 'var(--m-muted)'
    const bar = (name: string, key: 'batch_count' | 'scheduled_count' | 'other_count', color: string) => ({
      name, type: 'bar', stack: 'source', barMaxWidth: 26, data: items.value.map(item => item[key]),
      itemStyle: { color, borderRadius: [3, 3, 0, 0] }, emphasis: { focus: 'none', itemStyle: { color } },
    })
    return {
      color: [primary, scheduled, other, success],
      tooltip: { trigger: 'axis', confine: true, backgroundColor: 'var(--m-surface)', borderColor: 'var(--m-border)', textStyle: { color: 'var(--m-text)' }, formatter: tooltip },
      legend: { top: 2, itemWidth: 12, itemHeight: 8, textStyle: { color: 'var(--m-text-2)' } },
      grid: { top: 36, right: 46, bottom: 12, left: 8, containLabel: true },
      xAxis: { type: 'category', data: items.value.map(item => item.label), axisTick: { show: false },
        axisLine: { lineStyle: { color: 'var(--m-border-strong)' } },
        axisLabel: { show: true, color: muted, fontSize: 11, margin: 10, hideOverlap: false, interval: shouldShowTrendLabel },
      },
      yAxis: [
        { type: 'value', minInterval: 1, name: '报告数', nameTextStyle: { color: muted }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: 'var(--m-border)', type: 'dashed' } } },
        { type: 'value', min: 0, max: 100, name: '通过率', nameTextStyle: { color: muted }, axisLabel: { color: muted, formatter: '{value}%' }, splitLine: { show: false } },
      ],
      series: [bar('批量执行', 'batch_count', primary), bar('定时任务', 'scheduled_count', scheduled), bar('其他执行', 'other_count', other),
        { name: '最终通过率', type: 'line', yAxisIndex: 1, connectNulls: false, symbol: 'circle', symbolSize: 7,
          data: items.value.map(item => item.pass_rate), lineStyle: { width: 2, color: success },
          itemStyle: { color: 'var(--m-surface)', borderColor: success, borderWidth: 2 },
          emphasis: { focus: 'none', lineStyle: { width: 2, color: success }, itemStyle: { color: 'var(--m-surface)', borderColor: success, borderWidth: 2 } },
        },
      ],
    }
  })
</script>


<template>
  <div class="mango-report-source-trend">
    <div class="mango-report-source-trend__spin">
      <div class="mango-report-source-trend__summary" :class="{ 'mango-report-source-trend__summary--loading': loading }">
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
      <div ref="chartContainer" class="mango-report-source-trend__chart">
        <EffectivenessChart :option="chartOption" :loading="loading" height="100%" />
      </div>
    </div>
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

  .mango-report-source-trend__spin {
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

  .mango-report-source-trend__summary--loading { visibility: hidden; }

  .mango-report-source-trend__chart :deep(.mango-effectiveness-chart-spin),
  .mango-report-source-trend__chart :deep(.mango-effectiveness-chart-spin > .mango-panel-spin__content) {
    height: 100%;
  }

  .mango-report-source-trend__chart {
    display: flex;
    width: 100%;
    height: 0;
    min-height: 180px;
    flex: 1;
  }
</style>
