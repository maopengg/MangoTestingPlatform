<template>
  <div class="chart-item-container">
    <div ref="chartRef" class="chart-item"></div>
  </div>
</template>

<script lang="ts" setup>
  import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
  import { dispose } from 'echarts/core'
  import useEcharts from '@/hooks/useEcharts'

  // 定义 props
  const props = defineProps({
    chartData: {
      type: Array,
      required: true,
    },
  })

  const chartRef = ref<HTMLDivElement | null>(null)

  const initChart = () => {
    if (!chartRef.value) return

    const option = {
      legend: {
        right: '10%',
        y: 'center',
        icon: 'circle',
        orient: 'vertical',
        formatter: function (name: string) {
          let total = 0
          let target = 0
          for (let i = 0; i < props.chartData.length; i++) {
            total += props.chartData[i].value
            if (props.chartData[i].name === name) {
              target = props.chartData[i].value
            }
          }
          const arr = [
            '{a|' + name + '}',
            '{b|' +
              ((target / total) * 100).toFixed(2) +
              '%' +
              '}' +
              '{a|' +
              '  |  ' +
              '}' +
              '{b|' +
              target +
              '}',
          ]
          return arr.join('  ')
        },
        textStyle: {
          rich: {
            a: {
              fontSize: 12,
              color: 'var(--color-text-2)',
            },
            b: {
              fontSize: 12,
              color: 'rgb(var(--primary-1))',
              fontWeight: 'bold',
            },
          },
        },
      },
      series: [
        {
          name: '访问来源',
          type: 'pie',
          center: ['30%', '50%'],
          radius: ['50%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '16',
              fontWeight: 'bold',
            },
          },
          label: {
            show: false,
            position: 'center',
          },
          labelLine: {
            show: false,
          },
          data: props.chartData,
        },
      ],
    }

    useEcharts(chartRef.value).setOption(option)
  }

  const updateChart = () => {
    if (chartRef.value) {
      useEcharts(chartRef.value).resize()
    }
  }

  // 监听 chartData 变化，重新渲染图表
  watch(
    () => props.chartData,
    () => {
      initChart()
    },
    { deep: true }
  )

  onMounted(() => {
    initChart()
  })

  onBeforeUnmount(() => {
    if (chartRef.value) {
      dispose(chartRef.value)
    }
  })
</script>

<style lang="less" scoped>
  .chart-item-container {
    width: 100%;

    .chart-item {
      height: 100%;
    }
  }
</style>
