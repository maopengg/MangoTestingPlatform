<template>
  <div ref="barChart" :style="{ width: '100%', height: '250px' }"></div>
</template>

<script lang="ts" setup>
  import { ref, onMounted, watch } from 'vue'
  import * as echarts from 'echarts'

  // 定义 props
  const props = defineProps<{
    success: number[] // 成功数据
    fail: number[] // 失败数据
  }>()

  const barChart = ref<HTMLElement | null>(null)
  let myChart: echarts.ECharts | null = null

  // ECharts 配置
  const chartOptions: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
    },
    xAxis: {
      type: 'category',
      data: ['1周', '2周', '3周', '4周', '5周', '6周', '7周', '8周', '9周', '10周', '11周', '12周'],
    },
    legend: {
      data: ['成功', '失败'],
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        name: '成功',
        type: 'line',
        itemStyle: {
          color: 'green', // 绿色
        },
      },
      {
        name: '失败',
        type: 'line',
        itemStyle: {
          color: 'red', // 红色
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
</script>
