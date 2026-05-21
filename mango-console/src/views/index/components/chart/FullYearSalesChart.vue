<template>
  <div class="chart-item-container">
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
      const seriesSummary = ref([
        { name: '接口用例', total: 0, color: '#5b7cfa' },
        { name: '界面用例', total: 0, color: '#22c55e' },
        { name: '单元用例', total: 0, color: '#f6c143' },
      ])
      let interval: any = null
      let data: any = reactive([])

      function caseResultWeekSum() {
        getSystemCaseResultWeekSum()
          .then((res) => {
            data = res.data
            seriesSummary.value = [
              {
                name: '接口用例',
                total: (data.api_count || []).reduce((sum: number, item: number) => sum + Number(item || 0), 0),
                color: '#5b7cfa',
              },
              {
                name: '界面用例',
                total: (data.ui_count || []).reduce((sum: number, item: number) => sum + Number(item || 0), 0),
                color: '#22c55e',
              },
              {
                name: '单元用例',
                total: (data.pytest_count || []).reduce((sum: number, item: number) => sum + Number(item || 0), 0),
                color: '#f6c143',
              },
            ]
            init()
          })
          .catch(console.log)
      }

      const init = () => {
        const option = {
          color: ['#5b7cfa', '#22c55e', '#f6c143'],
          grid: {
            top: 20,
            left: 8,
            right: 12,
            bottom: 8,
            containLabel: true,
          },
          tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(255, 255, 255, 0.96)',
            borderColor: '#e5e6eb',
            textStyle: {
              color: '#1d2129',
            },
          },
          xAxis: {
            type: 'category',
            data: months,
            axisLine: {
              show: true,
              lineStyle: {
                color: '#98A3B2',
                width: 0,
                type: 'solid',
              },
            },
            axisTick: {
              show: false,
            },
            axisLabel: {
              color: '#86909c',
            },
          },
          yAxis: {
            type: 'value',
            splitLine: {
              show: true,
              lineStyle: {
                color: '#eef0f5',
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
              color: '#86909c',
            },
          },
          series: [
            {
              type: 'line',
              name: '接口用例',
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
                color: '#5b7cfa',
              },
            },
            {
              type: 'line',
              name: '界面用例',
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
                color: '#22c55e',
              },
            },
            {
              type: 'line',
              name: '单元用例',
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
                color: '#f6c143',
              },
            },
          ],
        }
        setTimeout(() => {
          loading.value = false
          setTimeout(() => {
            nextTick(() => {
              if (fullYearSalesChart.value) {
                useEcharts(fullYearSalesChart.value as HTMLDivElement).setOption(option)
              }
            })
          }, 100)
        }, 1000)
      }
      const updateChart = () => {
        useEcharts(fullYearSalesChart.value as HTMLDivElement).resize()
      }
      onMounted(() => {
        nextTick(async () => {
          await caseResultWeekSum()
        })
      })
      onBeforeUnmount(() => {
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
    border: 1px solid var(--color-neutral-3);
    border-radius: 8px;
    background: var(--color-fill-1);

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
      color: var(--color-text-3);
      font-size: 12px;
    }

    strong {
      margin-top: 2px;
      color: var(--color-text-1);
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
  }
</style>
