<template>
  <div class="chart-item-container">
    <div ref="channelsChart" class="chart-item"></div>
  </div>
</template>

<script lang="ts">
  import useEcharts from '@/hooks/useEcharts'
  import { defineComponent, nextTick, onBeforeUnmount, onMounted, ref, reactive } from 'vue'
  import { dispose } from 'echarts/core'
  import { getSystemCaseSum } from '@/api/system'

  export default defineComponent({
    name: 'CaseSum',
    setup() {
      const loading = ref(true)
      const channelsChart = ref<HTMLDivElement | null>(null)
      let data: any = reactive([])

      function caseSum() {
        getSystemCaseSum()
          .then((res) => {
            data = res.data
            init()
          })
          .catch(console.log)
      }

      const init = () => {
        const option = {
          legend: {
            right: '10%',
            y: 'center',
            icon: 'circle',
            orient: 'vertical',
            formatter: function (name: string) {
              // 添加
              let total = 0
              let target = 0
              for (let i = 0; i < data.length; i++) {
                total += data[i].value
                if (data[i].name === name) {
                  target = data[i].value
                }
              }
              var arr = [
                '{a|' + name + '}',
                '{b|' + ((target / total) * 100).toFixed(2) + '%' + '}' + '{a|' + '  |  ' + '}' + '{b|' + target + '}',
              ]
              return arr.join('  ')
            },
            textStyle: {
              // 添加
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
              data,
            },
          ],
        }
        setTimeout(() => {
          loading.value = false
          nextTick(() => {
            useEcharts(channelsChart.value as HTMLDivElement).setOption(option)
          })
        }, 1000)
      }
      const updateChart = () => {
        useEcharts(channelsChart.value as HTMLDivElement).resize()
      }

      onMounted(() => {
        nextTick(async () => {
          await caseSum()
        })
      })
      // onMounted(init)
      onBeforeUnmount(() => {
        dispose(channelsChart.value as HTMLDivElement)
      })
      return {
        loading,
        channelsChart,
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
