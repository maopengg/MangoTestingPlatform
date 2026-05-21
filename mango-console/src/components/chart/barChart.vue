<script lang="ts" setup>
  import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
  import * as echarts from 'echarts'

  // 定义 props
  const props = defineProps<{
    success: number[] // 成功数据
    fail: number[] // 失败数据
  }>()

  const barChart = ref<HTMLElement | null>(null)
  let myChart: echarts.ECharts | null = null
  const successTotal = computed(() => props.success.reduce((sum, item) => sum + Number(item || 0), 0))
  const failTotal = computed(() => props.fail.reduce((sum, item) => sum + Number(item || 0), 0))

  // ECharts 配置
  const chartOptions: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#e5e6eb',
      textStyle: {
        color: '#1d2129',
      },
    },
    grid: {
      top: 18,
      left: 8,
      right: 12,
      bottom: 8,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: ['1周', '2周', '3周', '4周', '5周', '6周', '7周', '8周', '9周', '10周', '11周', '12周'],
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
        name: '成功',
        type: 'line',
        data: [], // 将在 updateChart 中动态设置
        symbol: 'circle',
        symbolSize: 6,
        smooth: true,
        lineStyle: {
          width: 3,
          color: '#22c55e',
        },
        areaStyle: {
          opacity: 0.12,
          color: '#22c55e',
        },
        itemStyle: {
          color: '#22c55e',
        },
      },
      {
        name: '失败',
        type: 'line',
        data: [], // 将在 updateChart 中动态设置
        symbol: 'circle',
        symbolSize: 6,
        smooth: true,
        lineStyle: {
          width: 3,
          color: '#ef4444',
        },
        areaStyle: {
          opacity: 0.1,
          color: '#ef4444',
        },
        itemStyle: {
          color: '#ef4444',
        },
      },
    ],
  }

  // 初始化柱状图
  const initBarChart = () => {
    if (!barChart.value) return

    myChart = echarts.init(barChart.value)
    updateChart()
  }

  // 更新柱状图数据
  const updateChart = () => {
    if (!myChart) return

    // 更新 series 数据
    const options = {
      ...chartOptions,
      series: [
        {
          ...chartOptions.series![0],
          data: props.success, // 使用 success 数据
        },
        {
          ...chartOptions.series![1],
          data: props.fail,
        },
      ],
    }

    myChart.setOption(options)
  }

  watch(
    () => [props.success, props.fail],
    () => {
      updateChart()
    },
    { deep: true }
  )

  onMounted(() => {
    initBarChart()
  })

  onBeforeUnmount(() => {
    myChart?.dispose()
  })
</script>

<template>
  <div class="report-trend-chart">
    <div class="trend-stat-row">
      <div class="trend-stat success">
        <span></span>
        <div>
          <strong>{{ successTotal }}</strong>
          <p>成功</p>
        </div>
      </div>
      <div class="trend-stat fail">
        <span></span>
        <div>
          <strong>{{ failTotal }}</strong>
          <p>失败</p>
        </div>
      </div>
    </div>
    <div ref="barChart" class="chart"></div>
  </div>
</template>

<style lang="less" scoped>
  .report-trend-chart {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }

  .trend-stat-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    padding: 8px 4px 2px;
  }

  .trend-stat {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border: 1px solid var(--color-neutral-3);
    border-radius: 8px;
    background: var(--color-fill-1);

    > span {
      width: 9px;
      height: 9px;
      flex: 0 0 auto;
      border-radius: 50%;
    }

    strong {
      color: var(--color-text-1);
      font-size: 18px;
      line-height: 22px;
    }

    p {
      margin: 0;
      color: var(--color-text-3);
      font-size: 12px;
      line-height: 17px;
    }
  }

  .trend-stat.success > span {
    background: #22c55e;
  }

  .trend-stat.fail > span {
    background: #ef4444;
  }

  .chart {
    flex: 1;
    width: 100%;
    min-height: 0;
  }
</style>
