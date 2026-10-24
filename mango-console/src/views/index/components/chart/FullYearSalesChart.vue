<template>
  <div class="chart-item-container">
    <mango-panel-spin :loading="loading" class="mango-chart-spin">
      <div class="mango-chart-content">
        <div class="mango-trend-summary" aria-label="近 12 周自动化执行总次数">
          <div class="mango-trend-summary__item is-api">
            <span class="mango-trend-summary__dot"></span>
            <span class="mango-trend-summary__label">API 场景</span>
            <strong>{{ formatNumber(summary.api) }}</strong>
            <small>次</small>
          </div>
          <div class="mango-trend-summary__item is-ui">
            <span class="mango-trend-summary__dot"></span>
            <span class="mango-trend-summary__label">UI 用例</span>
            <strong>{{ formatNumber(summary.ui) }}</strong>
            <small>次</small>
          </div>
          <div class="mango-trend-summary__item is-pytest">
            <span class="mango-trend-summary__dot"></span>
            <span class="mango-trend-summary__label">Pytest 用例</span>
            <strong>{{ formatNumber(summary.pytest) }}</strong>
            <small>次</small>
          </div>
        </div>
        <div ref="fullYearSalesChart" class="chart-item"></div>
      </div>
    </mango-panel-spin>
  </div>
</template>
<script lang="ts">
  import useEcharts from '@/hooks/useEcharts'
  import { defineComponent, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { dispose } from 'echarts/core'
  import { getSystemCaseResultWeekSum } from '@/api/system'

  export default defineComponent({
    name: 'FullYearSalesChart',
    setup() {
      const loading = ref(true)
      const fullYearSalesChart = ref<HTMLDivElement | null>(null)
      let resizeObserver: ResizeObserver | null = null
      let resizeFrame = 0
      let visibleLabelSignature = ''
      const token = (name: string, fallback: string) =>
        getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
      const testTypeColors = () => ({
        api: token('--m-chart-1', '#5b7cfa'),
        ui: token('--m-chart-2', '#22c55e'),
        pytest: token('--m-chart-3', '#f6c143'),
      })
      let interval: any = null
      let data: any = reactive([])
      const summary = reactive({ api: 0, ui: 0, pytest: 0 })

      function sumValues(values: unknown) {
        return Array.isArray(values)
          ? values.reduce((total, value) => total + Number(value || 0), 0)
          : 0
      }

      function updateSummary() {
        summary.api = sumValues(data.api_count)
        summary.ui = sumValues(data.ui_count)
        summary.pytest = sumValues(data.pytest_count)
      }

      function formatNumber(value: number) {
        return Number(value || 0).toLocaleString('zh-CN')
      }

      function caseResultWeekSum() {
        loading.value = true
        getSystemCaseResultWeekSum()
          .then((res) => {
            data = res.data
            updateSummary()
            init()
          })
          .catch(console.log)
          .finally(() => {
            loading.value = false
          })
      }

      function getVisibleLabelIndexes() {
        const labels = Array.isArray(data.labels)
          ? data.labels.map((item: any) => String(item))
          : []
        if (!labels.length) return new Set<number>()

        const chartWidth = fullYearSalesChart.value?.clientWidth || 0
        const canvas = document.createElement('canvas')
        const context = canvas.getContext('2d')
        if (context) context.font = '12px system-ui'
        const widestLabel = Math.max(
          ...labels.map((label: string) => context?.measureText(label).width || label.length * 7),
          72
        )
        const availableWidth = Math.max(0, chartWidth - 48)
        const visibleCount = Math.max(
          2,
          Math.min(labels.length, Math.floor(availableWidth / (widestLabel + 18)))
        )

        if (visibleCount >= labels.length) {
          return new Set(labels.map((_: string, index: number) => index))
        }

        const indexes = new Set<number>()
        for (let index = 0; index < visibleCount; index += 1) {
          indexes.add(Math.round((index * (labels.length - 1)) / (visibleCount - 1)))
        }
        return indexes
      }

      function responsiveAxisLabelInterval() {
        const visibleIndexes = getVisibleLabelIndexes()
        visibleLabelSignature = [...visibleIndexes].join(',')
        return (index: number) => visibleIndexes.has(index)
      }

      function updateResponsiveAxisLabels() {
        if (!fullYearSalesChart.value) return
        const visibleIndexes = getVisibleLabelIndexes()
        const signature = [...visibleIndexes].join(',')
        if (signature === visibleLabelSignature) return
        visibleLabelSignature = signature
        useEcharts(fullYearSalesChart.value).setOption({
          xAxis: {
            axisLabel: {
              interval: (index: number) => visibleIndexes.has(index),
            },
          },
        })
      }

      const init = () => {
        const option = {
          color: [testTypeColors().ui, testTypeColors().api, testTypeColors().pytest],
          grid: {
            // 为双纵轴标题预留完整高度，避免标题被图表容器顶部裁切。
            top: 37,
            left: 10,
            right: 21,
            bottom: 7,
            containLabel: true,
          },
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'line' },
            backgroundColor: token('--m-surface', '#fff'),
            borderColor: token('--m-border', '#e5e6eb'),
            textStyle: {
              color: token('--m-text', '#1d2129'),
              fontSize: 14,
              lineHeight: 18,
            },
            padding: 9,
            formatter(params: any[]) {
              if (!params?.length) return ''
              return [
                `<strong>${params[0].axisValueLabel || params[0].name}</strong>`,
                ...params.map(
                  (item) => `${item.marker}${item.seriesName}：${Number(item.value || 0)} 个`
                ),
              ].join('<br />')
            },
          },
          xAxis: {
            type: 'category',
            data: Array.isArray(data.labels) && data.labels.length ? data.labels : [],
            axisLine: {
              show: true,
              lineStyle: {
                color: token('--m-border-strong', '#98A3B2'),
                width: 0,
                type: 'solid',
              },
            },
            axisTick: {
              show: false,
            },
            axisLabel: {
              color: token('--m-muted', '#86909c'),
              fontSize: 12,
              interval: responsiveAxisLabelInterval(),
              hideOverlap: true,
            },
          },
          yAxis: [
            {
              type: 'value',
              name: 'API 场景（个）',
              nameLocation: 'end',
              nameGap: 9,
              min: 0,
              minInterval: 1,
              nameTextStyle: {
                color: token('--m-text-2', '#4e5969'),
                fontSize: 11,
                fontWeight: 600,
                align: 'left',
              },
              splitLine: {
                show: true,
                lineStyle: {
                  color: token('--m-border', '#eef0f5'),
                  type: 'dashed',
                },
              },
              axisLine: {
                show: true,
                lineStyle: {
                  color: token('--m-border-strong', '#98A3B2'),
                },
              },
              axisTick: {
                show: false,
              },
              axisLabel: {
                color: token('--m-muted', '#86909c'),
                fontSize: 12,
              },
            },
            {
              type: 'value',
              name: 'UI / Pytest（个）',
              nameLocation: 'end',
              nameGap: 9,
              min: 0,
              minInterval: 1,
              nameTextStyle: {
                color: token('--m-text-2', '#4e5969'),
                fontSize: 11,
                fontWeight: 600,
                align: 'right',
              },
              splitLine: {
                show: false,
              },
              axisLine: {
                show: true,
                lineStyle: {
                  color: token('--m-border-strong', '#98A3B2'),
                },
              },
              axisTick: {
                show: false,
              },
              axisLabel: {
                color: token('--m-muted', '#86909c'),
                fontSize: 12,
              },
            },
          ],
          series: [
            {
              type: 'line',
              name: 'UI 用例',
              yAxisIndex: 1,
              data: data.ui_count || [],
              symbol: 'circle',
              symbolSize: 6,
              smooth: true,
              lineStyle: {
                width: 3,
                color: testTypeColors().ui,
              },
              itemStyle: {
                color: token('--m-surface', '#fff'),
                borderColor: testTypeColors().ui,
                borderWidth: 2,
              },
              emphasis: {
                focus: 'none',
                lineStyle: { width: 4, color: testTypeColors().ui },
              },
            },
            {
              type: 'line',
              name: 'API 场景',
              yAxisIndex: 0,
              data: data.api_count || [],
              symbol: 'circle',
              symbolSize: 6,
              smooth: true,
              lineStyle: {
                width: 3,
                color: testTypeColors().api,
              },
              itemStyle: {
                color: token('--m-surface', '#fff'),
                borderColor: testTypeColors().api,
                borderWidth: 2,
              },
              emphasis: {
                focus: 'none',
                lineStyle: { width: 4, color: testTypeColors().api },
              },
            },
            {
              type: 'line',
              name: 'Pytest 用例',
              yAxisIndex: 1,
              data: data.pytest_count || [],
              symbol: 'circle',
              symbolSize: 6,
              smooth: true,
              lineStyle: {
                width: 3,
                color: testTypeColors().pytest,
              },
              itemStyle: {
                color: token('--m-surface', '#fff'),
                borderColor: testTypeColors().pytest,
                borderWidth: 2,
              },
              emphasis: {
                focus: 'none',
                lineStyle: { width: 4, color: testTypeColors().pytest },
              },
            },
          ],
        }
        nextTick(() => {
          if (fullYearSalesChart.value) {
            useEcharts(fullYearSalesChart.value as HTMLDivElement).setOption(option)
            updateChart()
          }
        })
      }
      const updateChart = () => {
        if (!fullYearSalesChart.value) {
          return
        }
        if (resizeFrame) {
          window.cancelAnimationFrame(resizeFrame)
        }
        resizeFrame = window.requestAnimationFrame(() => {
          if (fullYearSalesChart.value) {
            useEcharts(fullYearSalesChart.value as HTMLDivElement).resize()
            updateResponsiveAxisLabels()
          }
          resizeFrame = 0
        })
      }
      onMounted(() => {
        nextTick(async () => {
          await caseResultWeekSum()
          updateChart()
        })
        window.addEventListener('mango-theme-change', init)
        window.addEventListener('resize', updateChart)
        if (fullYearSalesChart.value) {
          resizeObserver = new ResizeObserver(updateChart)
          resizeObserver.observe(fullYearSalesChart.value)
        }
      })
      onBeforeUnmount(() => {
        window.removeEventListener('mango-theme-change', init)
        window.removeEventListener('resize', updateChart)
        resizeObserver?.disconnect()
        if (resizeFrame) {
          window.cancelAnimationFrame(resizeFrame)
        }
        dispose(fullYearSalesChart.value as HTMLDivElement)
        clearInterval(interval)
      })
      return {
        loading,
        fullYearSalesChart,
        summary,
        formatNumber,
        updateChart,
      }
    },
  })
</script>

<style lang="less" scoped>
  .chart-item-container {
    height: 100%;
    min-height: 0;
    width: 100%;
  }

  .mango-chart-spin,
  :deep(.mango-chart-spin > .mango-panel-spin__content) {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    width: 100%;
  }

  .mango-chart-content {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    width: 100%;
  }

  .mango-trend-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    padding: 6px 8px 2px;
  }

  .mango-trend-summary__item {
    display: flex;
    min-width: 0;
    height: 40px;
    align-items: center;
    gap: 7px;
    padding: 0 12px;
    border: 1px solid var(--m-border);
    border-radius: 5px;
    background: var(--m-surface-soft);

    strong {
      margin-left: auto;
      color: var(--m-text);
      font-size: 18px;
      font-variant-numeric: tabular-nums;
      line-height: 22px;
    }

    small {
      color: var(--m-muted);
      font-size: 12px;
    }

    &.is-api .mango-trend-summary__dot {
      background: var(--m-chart-1);
    }

    &.is-ui .mango-trend-summary__dot {
      background: var(--m-chart-2);
    }

    &.is-pytest .mango-trend-summary__dot {
      background: var(--m-chart-3);
    }
  }

  .mango-trend-summary__dot {
    width: 8px;
    height: 8px;
    flex: 0 0 8px;
    border-radius: 50%;
  }

  .mango-trend-summary__label {
    overflow: hidden;
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 16px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chart-item {
    flex: 1;
    min-height: 0;
    width: 100%;
    min-width: 0;
  }
</style>
