<script lang="ts" setup>
import {ref, onMounted, watch} from 'vue'
import * as echarts from 'echarts'

// 定义 props
const props = defineProps<{
  success: number // 成功数据
  fail: number // 失败数据
  pending?: number // 进行中（可选）
  todo?: number // 待开始（可选）
}>()

const pieChart = ref<HTMLElement | null>(null)
let myChart: echarts.ECharts | null = null

// 初始化饼状图
const initPieChart = () => {
  if (!pieChart.value) return

  myChart = echarts.init(pieChart.value)
  updateChart()
}

// 动态生成饼状图数据
const getChartData = () => {
  const data = [
    {
      value: props.success,
      name: '通过',
      itemStyle: {
        color: '#91cc75', // 与主页面一致的绿色
      },
    },
    {
      value: props.fail,
      name: '失败',
      itemStyle: {
        color: '#d34141', // 红色
      },
    },
  ]

  // 如果传入了 pending，添加到数据中
  if (props.pending !== undefined) {
    data.push({
      value: props.pending,
      name: '进行中',
      itemStyle: {
        color: '#FF7D00', // 与主页面一致的蓝色
      },
    })
  }

  // 如果传入了 todo，添加到数据中
  if (props.todo !== undefined) {
    data.push({
      value: props.todo,
      name: '待开始',
      itemStyle: {
        color: '#566070', // 灰色
      },
    })
  }

  return data
}

// 更新饼状图数据
const updateChart = () => {
  if (!myChart) return

  myChart.setOption({
    tooltip: {
      trigger: 'item',
    },
    legend: {
      top: '5%',
      left: 'center',
      textStyle: {
        color: 'var(--color-text-2)', // 与主页面一致的文本颜色
      },
    },
    series: [
      {
        name: 'Access From',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          position: 'center',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 40,
            fontWeight: 'bold',
          },
        },
        labelLine: {
          show: false,
        },
        data: getChartData(), // 动态生成数据
      },
    ],
  })
}

// 监听数据变化，更新图表
watch(
    () => [props.success, props.fail, props.pending, props.todo],
    () => {
      updateChart()
    },
    {deep: true}
)

onMounted(() => {
  initPieChart()
})
</script>

<template>
  <div ref="pieChart" :style="{ width: '100%', height: '250px' }"></div>
</template>
