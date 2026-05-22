<script lang="ts" setup>
  import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
  import * as echarts from 'echarts'

  // 定义 props
  const props = defineProps<{
    success: number // 成功数据
    fail: number // 失败数据
    pending?: number // 进行中（可选）
    todo?: number // 待开始（可选）
    loading?: boolean
  }>()

  const pieChart = ref<HTMLElement | null>(null)
  let myChart: echarts.ECharts | null = null

  const token = (name: string, fallback: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback

  const getPalette = () => [
    token('--m-success', '#22c55e'),
    token('--m-danger', '#ef4444'),
    token('--m-warning', '#f59e0b'),
    token('--m-muted', '#64748b'),
  ]

  const chartItems = computed(() => {
    const items = [
      { name: '通过', value: Number(props.success || 0), color: getPalette()[0] },
      { name: '失败', value: Number(props.fail || 0), color: getPalette()[1] },
    ]
    if (props.pending !== undefined) {
      items.push({ name: '进行中', value: Number(props.pending || 0), color: getPalette()[2] })
    }
    if (props.todo !== undefined) {
      items.push({ name: '待开始', value: Number(props.todo || 0), color: getPalette()[3] })
    }
    const total = items.reduce((sum, item) => sum + item.value, 0)
    return items.map((item) => ({
      ...item,
      percent: total ? (item.value / total) * 100 : 0,
      percentText: total ? `${((item.value / total) * 100).toFixed(2)}%` : '0.00%',
    }))
  })

  const total = computed(() => chartItems.value.reduce((sum, item) => sum + item.value, 0))

  // 初始化饼状图
  const initPieChart = () => {
    if (!pieChart.value) return

    myChart = echarts.init(pieChart.value)
    updateChart()
  }

  // 动态生成饼状图数据
  const getChartData = () => {
    return chartItems.value.map((item) => ({
      value: item.value,
      name: item.name,
      itemStyle: {
        color: item.color,
      },
    }))
  }

  // 更新饼状图数据
  const updateChart = () => {
    if (!myChart) return

    myChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}<br />{d}% | {c}',
      },
      series: [
        {
          name: '测试状态',
          type: 'pie',
          radius: ['58%', '78%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 6,
            borderColor: token('--m-surface', '#fff'),
            borderWidth: 4,
          },
          label: {
            show: false,
          },
          emphasis: {
            scaleSize: 4,
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
    { deep: true }
  )

  onMounted(() => {
    initPieChart()
    window.addEventListener('mango-theme-change', updateChart)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('mango-theme-change', updateChart)
    myChart?.dispose()
  })
</script>

<template>
  <div class="mango-status-chart">
    <a-spin :loading="props.loading" class="mango-chart-spin">
      <div class="mango-status-chart__content">
        <div class="mango-status-donut">
          <div ref="pieChart" class="mango-chart"></div>
          <div class="mango-status-total">
            <span>总数</span>
            <strong>{{ total }}</strong>
          </div>
        </div>
        <div class="mango-status-list">
          <div v-for="item in chartItems" :key="item.name" class="mango-status-item">
            <span class="mango-status-dot" :style="{ backgroundColor: item.color }"></span>
            <div class="mango-status-main">
              <span>{{ item.name }}</span>
              <div class="mango-status-bar">
                <i :style="{ width: `${item.percent}%`, backgroundColor: item.color }"></i>
              </div>
            </div>
            <div class="mango-status-value">
              <strong>{{ item.percentText }}</strong>
              <span>{{ item.value }}</span>
            </div>
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<style lang="less" scoped>
  .mango-status-chart {
    height: 100%;
    min-height: 0;
  }

  .mango-chart-spin,
  :deep(.mango-chart-spin .arco-spin-children) {
    display: grid;
    height: 100%;
    min-height: 0;
  }

  .mango-status-chart__content {
    display: grid;
    height: 100%;
    min-height: 0;
    grid-template-columns: 42% minmax(0, 1fr);
    align-items: center;
    gap: 12px;
  }

  .mango-status-donut {
    position: relative;
    height: 100%;
    min-height: 180px;
  }

  .mango-chart {
    width: 100%;
    height: 100%;
  }

  .mango-status-total {
    position: absolute;
    top: 50%;
    left: 50%;
    display: flex;
    width: 78px;
    height: 78px;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    transform: translate(-50%, -50%);
    pointer-events: none;

    span {
      color: var(--m-muted);
      font-size: 11px;
    }

    strong {
      max-width: 74px;
      overflow: hidden;
      color: var(--m-text);
      font-size: 20px;
      line-height: 24px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-status-list {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 10px;
  }

  .mango-status-item {
    display: grid;
    min-width: 0;
    grid-template-columns: 10px minmax(0, 1fr) 72px;
    align-items: center;
    gap: 8px;
  }

  .mango-status-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
  }

  .mango-status-main {
    min-width: 0;

    span {
      display: block;
      overflow: hidden;
      color: var(--m-text-2);
      font-size: 12px;
      line-height: 18px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-status-bar {
    height: 4px;
    margin-top: 4px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--m-border);

    i {
      display: block;
      height: 100%;
      min-width: 2px;
      border-radius: inherit;
    }
  }

  .mango-status-value {
    text-align: right;

    strong,
    span {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: var(--m-primary);
      font-size: 12px;
      line-height: 17px;
    }

    span {
      color: var(--m-muted);
      font-size: 11px;
      line-height: 16px;
    }
  }
</style>
