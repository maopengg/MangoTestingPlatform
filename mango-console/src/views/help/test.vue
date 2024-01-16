<template>
  <div>
    <a-card>
      <a-space>
        <div ref="barChart" :style="{ width: '400px', height: '300px' }"></div>
        <div ref="pieChart" :style="{ width: '500px', height: '300px' }"></div>
      </a-space>
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as echarts from 'echarts'

const barChart = ref<HTMLElement>()
const myChart1 = ref<any>()
function initBarEcharts() {
  myChart1.value = echarts.init(barChart.value!)
  myChart1.value.setOption({
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['成功', '失败']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['1周', '2周', '3周', '4周', '5周', '6周', '7周', '8周', '9周', '10周', '11周', '12周']
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '成功',
        type: 'line',
        data: [150, 230, 224, 218, 135, 147, 260, 231, 433, 133, 89, 213, 355, 299]
      },
      {
        name: '失败',
        type: 'line',
        data: [10, 10, 24, 18, 35, 47, 60, 10, 30, 24, 18, 35, 47, 60]
      }
    ]
  })
}
//绘制饼图
const pieChart = ref<HTMLElement>()
const myChart2 = ref<any>()
function initPieEcharts() {
  myChart2.value = echarts.init(pieChart.value!)
  myChart2.value.setOption({
    tooltip: {
      trigger: 'item'
    },
    legend: {
      top: '5%',
      left: 'center'
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
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 40,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: 1048, name: 'Search Engine' },
          { value: 735, name: 'Direct' },
          { value: 580, name: 'Email' },
          { value: 484, name: 'Union Ads' },
          { value: 300, name: 'Video Ads' }
        ]
      }
    ]
  })
}
onMounted(() => {
  initBarEcharts()
  initPieEcharts()
})
</script>
