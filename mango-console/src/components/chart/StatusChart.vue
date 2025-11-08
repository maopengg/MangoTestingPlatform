<template>
  <div ref="pieChart" style="width: 100%; height: 100%;"></div>
</template>

<script lang="ts" setup>
  import { ref, onMounted, watch, onUpdated, onUnmounted } from 'vue'
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
  let resizeObserver: ResizeObserver | null = null;

  // 初始化饼状图
  const initPieChart = () => {
    if (!pieChart.value) return

    myChart = echarts.init(pieChart.value)
    updateChart()
    
    // 监听窗口大小变化，重新调整图表大小
    window.addEventListener('resize', resizeChart)
    
    // 使用ResizeObserver监听容器大小变化
    if (window.ResizeObserver) {
      resizeObserver = new ResizeObserver(resizeChart)
      resizeObserver.observe(pieChart.value)
    }
  }

  // 调整图表大小
  const resizeChart = () => {
    if (myChart) {
      myChart.resize({
        animation: {
          duration: 300
        }
      })
    }
  }

  // 动态生成饼状图数据
  const getChartData = () => {
    const data = [
      {
        value: props.success,
        name: '通过',
        itemStyle: {
          color: '#11a834', // 绿色
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
          color: '#ffb400', // 橙色
        },
      })
    }

    // 如果传入了 todo，添加到数据中
    if (props.todo !== undefined) {
      data.push({
        value: props.todo,
        name: '待开始',
        itemStyle: {
          color: '#86909c', // 灰色
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
        type: 'scroll'
      },
      series: [
        {
          name: '测试结果分布',
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
              fontSize: 24,
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
      // 数据更新后也调整图表大小
      setTimeout(resizeChart, 100)
    },
    { deep: true }
  )

  // 组件更新时也重新渲染图表
  onUpdated(() => {
    if (myChart) {
      myChart.resize({
        animation: {
          duration: 300
        }
      })
    }
  })

  onMounted(() => {
    initPieChart()
    // 组件挂载后延迟调整大小
    setTimeout(resizeChart, 100)
  })
  
  // 组件卸载时移除事件监听器
  onUnmounted(() => {
    window.removeEventListener('resize', resizeChart)
    if (resizeObserver) {
      resizeObserver.disconnect()
    }
    if (myChart) {
      myChart.dispose()
    }
  })
</script>