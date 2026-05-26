<template>
  <div class="chart-item-container">
    <a-spin :loading="loading" class="mango-chart-spin">
      <div class="mango-chart-content">
        <div class="trend-summary">
          <div v-for="item in seriesSummary" :key="item.name" class="summary-item">
            <span class="summary-dot" :style="{ backgroundColor: item.color }"></span>
            <div>
              <span>{{ item.name }}</span>
              <strong>{{ item.total }}</strong>
            </div>
          </div>
        </div>
        <div ref="fullYearSalesChart" class="chart-item"></div>
      </div>
    </a-spin>
  </div>
</template>
<script lang="ts">
  import useEcharts from '@/hooks/useEcharts'
  import { defineComponent, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { dispose } from 'echarts/core'
  import { getSystemCaseResultWeekSum } from '@/api/system'

  const months = [
    '1周',
    '2周',
    '3周',
    '4周',
    '5周',
    '6周',
    '7周',
    '8周',
    '9周',
    '10周',
    '11周',
    '12周',
  ]
  export default defineComponent({
    name: 'FullYearSalesChart',
    setup() {
      const loading = ref(true)
      const fullYearSalesChart = ref<HTMLDivElement | null>(null)
      let resizeObserver: ResizeObserver | null = null
      let resizeFrame = 0
      const token = (name: string, fallback: string) =>
        getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
      const testTypeColors = () => ({
        api: token('--m-chart-1', '#5b7cfa'),
        ui: token('--m-chart-2', '#22c55e'),
        pytest: token('--m-chart-3', '#f6c143'),
      })
      const seriesSummary = ref([
        { name: '接口自动化', total: 0, color: testTypeColors().api },
        { name: '界面自动化', total: 0, color: testTypeColors().ui },
        { name: '单元自动化', total: 0, color: testTypeColors().pytest },
      ])
      let interval: any = null
      let data: any = reactive([])

      function syncSummaryColors() {
        const colors = testTypeColors()
        seriesSummary.value = seriesSummary.value.map((item) => {
          if (item.name.includes('接口')) {
            return { ...item, color: colors.api }
          }
          if (item.name.includes('界面')) {
            return { ...item, color: colors.ui }
          }
          return { ...item, color: colors.pytest }
        })
      }

      function caseResultWeekSum() {
        loading.value = true
        getSystemCaseResultWeekSum()
          .then((res) => {
            data = res.data
            seriesSummary.value = [
              {
                name: '接口自动化',
                total: (data.api_count || []).reduce(
                  (sum: number, item: number) => sum + Number(item || 0),
                  0
                ),
                color: testTypeColors().api,
              },
              {
                name: '界面自动化',
                total: (data.ui_count || []).reduce(
                  (sum: number, item: number) => sum + Number(item || 0),
                  0
                ),
                color: testTypeColors().ui,
              },
              {
                name: '单元自动化',
                total: (data.pytest_count || []).reduce(
                  (sum: number, item: number) => sum + Number(item || 0),
                  0
                ),
                color: testTypeColors().pytest,
              },
            ]
            init()
          })
          .catch(console.log)
          .finally(() => {
            loading.value = false
          })
      }

      const init = () => {
        syncSummaryColors()
        const option = {
          color: [testTypeColors().api, testTypeColors().ui, testTypeColors().pytest],
          grid: {
            top: 20,
            left: 8,
            right: 12,
            bottom: 8,
            containLabel: true,
          },
          tooltip: {
            trigger: 'axis',
            backgroundColor: token('--m-surface', '#fff'),
            borderColor: token('--m-border', '#e5e6eb'),
            textStyle: {
              color: token('--m-text', '#1d2129'),
            },
          },
          xAxis: {
            type: 'category',
            data: months,
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
            },
          },
          yAxis: {
            type: 'value',
            splitLine: {
              show: true,
              lineStyle: {
                color: token('--m-border', '#eef0f5'),
                type: 'dashed',
              },
            },
            axisLine: {
              show: false,
            },
            axisTick: {
              show: false,
            },
            axisLabel: {
              color: token('--m-muted', '#86909c'),
            },
          },
          series: [
            {
              type: 'line',
              name: '接口自动化',
              data: data.api_count,
              symbol: 'circle',
              symbolSize: 6,
              smooth: true,
              lineStyle: {
                width: 3,
              },
              areaStyle: {
                opacity: 0.12,
              },
              itemStyle: {
                color: testTypeColors().api,
              },
            },
            {
              type: 'line',
              name: '界面自动化',
              data: data.ui_count,
              symbol: 'circle',
              symbolSize: 6,
              smooth: true,
              lineStyle: {
                width: 3,
              },
              areaStyle: {
                opacity: 0.1,
              },
              itemStyle: {
                color: testTypeColors().ui,
              },
            },
            {
              type: 'line',
              name: '单元自动化',
              data: data.pytest_count,
              symbol: 'circle',
              symbolSize: 6,
              smooth: true,
              lineStyle: {
                width: 3,
              },
              areaStyle: {
                opacity: 0.12,
              },
              itemStyle: {
                color: testTypeColors().pytest,
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
        seriesSummary,
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
  :deep(.mango-chart-spin .arco-spin-children) {
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

  .trend-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    padding: 8px 6px 2px;
  }

  .summary-item {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface-soft);

    div {
      min-width: 0;
    }

    span,
    strong {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: var(--m-muted);
      font-size: 12px;
    }

    strong {
      margin-top: 2px;
      color: var(--m-text);
      font-size: 18px;
      line-height: 22px;
    }
  }

  .summary-dot {
    width: 9px;
    height: 9px;
    flex: 0 0 auto;
    border-radius: 50%;
  }

  .chart-item {
    flex: 1;
    min-height: 0;
    width: 100%;
    min-width: 0;
  }
</style>
