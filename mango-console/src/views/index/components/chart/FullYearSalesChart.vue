<template>
  <div class="chart-item-container">
    <div ref="fullYearSalesChart" class="chart-item"></div>
  </div>
</template>
<script lang="ts">
  import useEcharts from '@/hooks/useEcharts'
  import { defineComponent, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { dispose, graphic } from 'echarts/core'
  import { getSystemCaseResultWeekSum } from '@/api/system'

  const months = ['1周', '2周', '3周', '4周', '5周', '6周', '7周', '8周', '9周', '10周', '11周', '12周']
  export default defineComponent({
    name: 'FullYearSalesChart',
    setup() {
      const loading = ref(true)
      const fullYearSalesChart = ref<HTMLDivElement | null>(null)
      let interval: any = null
      let data: any = reactive([])
      function caseResultWeekSum() {
        getSystemCaseResultWeekSum()
          .then((res) => {
            data = res.data
            init()
          })
          .catch(console.log)
      }
      const init = () => {
        const option = {
          color: ['rgba(64, 58, 255)'],
          grid: {
            top: '5%',
            left: '2%',
            right: '2%',
            bottom: '4%',
            containLabel: true,
          },
          tooltip: {
            trigger: 'axis',
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
          },
          yAxis: {
            type: 'value',
            max: 800,
            splitLine: { show: false },
            axisLine: {
              show: true,
              lineStyle: {
                color: '#98A3B2',
                width: 0,
                type: 'solid',
              },
            },
          },
          series: [
            {
              type: 'line',
              name: '接口用例执行数',
              stack: '总量',
              data: data.api_count,
              symbolSize: 0,
              smooth: true,
              lineStyle: {
                width: 5,
                shadowColor: '#999', //设置折线阴影
                shadowBlur: 10,
                shadowOffsetY: 5,
              },
              itemStyle: {
                color: new graphic.LinearGradient(1, 0, 0, 0, [{ offset: 1, color: '#91cc75' }]),
              },
            },
            {
              type: 'line',
              name: '界面用例执行数',
              stack: '总量2',
              data: data.ui_count,
              symbolSize: 0,
              smooth: true,
              lineStyle: {
                width: 5,
                shadowColor: '#999', //设置折线阴影
                shadowBlur: 10,
                shadowOffsetY: 5,
              },
              itemStyle: {
                color: new graphic.LinearGradient(1, 0, 0, 0, [{ offset: 1, color: '#5470c6' }]),
              },
            },
          ],
        }
        setTimeout(() => {
          loading.value = false
          setTimeout(() => {
            nextTick(() => useEcharts(fullYearSalesChart.value as HTMLDivElement).setOption(option))
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
        updateChart,
      }
    },
  })
</script>

<style lang="less" scoped>
  .chart-item-container {
    width: 100%;

    .chart-item {
      height: 31vh;
    }
  }
</style>
