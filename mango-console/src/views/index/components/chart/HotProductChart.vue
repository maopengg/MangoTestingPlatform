<template>
  <div class="chart-item-container">
    <div ref="hotProdChart" class="chart-item"></div>
  </div>
</template>
<script lang="ts">
  import useEcharts from '@/hooks/useEcharts'
  import { defineComponent, nextTick, onBeforeUnmount, onMounted, ref, reactive } from 'vue'
  import { dispose } from 'echarts/core'
  import { getSystemActivityLevel } from '@/api/system'

  export default defineComponent({
    name: 'HotProdChart',
    setup() {
      const loading = ref(true)
      const hotProdChart = ref<HTMLDivElement | null>(null)
      let interval: any = null
      let data: any = reactive([])
      function activityLevel() {
        getSystemActivityLevel()
          .then((res) => {
            data = res.data
            init()
          })
          .catch(console.log)
      }
      const init = () => {
        const option = {
          grid: {
            top: '2%',
            left: '5%',
            right: '8%',
            bottom: '2%',
            containLabel: true,
          },
          tooltip: {
            trigger: 'axis',
          },
          yAxis: {
            type: 'category',
            data: data.nickname,
            axisLine: {
              show: false,
            },
            axisTick: {
              show: false,
            },
            axisLabel: {
              textStyle: {
                fontSize: 10,
                color: '#98A3B2',
              },
            },
          },
          xAxis: {
            show: false,
          },
          series: [
            {
              type: 'pictorialBar',
              name: '访问次数',
              stack: '指数',
              data: data.total_logins,
              smooth: true,
              symbol: 'rect',
              symbolRepeat: true,
              symbolSize: [2, 10],
              symbolMargin: 1,
              label: {
                show: true, //开启数值显示
                position: 'right', //在上方显示
                textStyle: {
                  //数值样式
                  color: 'rgb(var(--primary-1))',
                  fontSize: 12,
                },
              },
              itemStyle: {
                color: 'rgb(var(--primary-1))',
              },
            },
          ],
        }
        setTimeout(() => {
          loading.value = false
          setTimeout(() => {
            nextTick(() => useEcharts(hotProdChart.value as HTMLDivElement).setOption(option))
          }, 100)
        }, 1000)
      }
      const updateChart = () => {
        useEcharts(hotProdChart.value as HTMLDivElement).resize()
      }
      onMounted(() => {
        nextTick(async () => {
          await activityLevel()
        })
      })
      onBeforeUnmount(() => {
        dispose(hotProdChart.value as HTMLDivElement)
        clearInterval(interval)
      })
      return {
        loading,
        hotProdChart,
        updateChart,
      }
    },
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
