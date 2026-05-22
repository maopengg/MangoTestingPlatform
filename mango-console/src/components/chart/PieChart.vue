<template>
  <div class="mango-chart-item-container">
    <a-spin :loading="loading" class="mango-chart-spin">
      <div class="mango-chart-content">
        <div class="mango-donut-wrap">
          <div ref="chartRef" class="mango-chart-item"></div>
          <div class="mango-donut-total">
            <span>总数</span>
            <strong>{{ total }}</strong>
          </div>
        </div>
        <div class="mango-legend-list">
          <div v-for="(item, index) in normalizedData" :key="item.name" class="mango-legend-item">
            <span
              class="mango-legend-dot"
              :style="{ backgroundColor: palette[index % palette.length] }"
            ></span>
            <div class="mango-legend-main">
              <span class="mango-legend-name">{{ item.name }}</span>
              <div class="mango-legend-bar">
                <span
                  :style="{
                    width: `${item.percent}%`,
                    backgroundColor: palette[index % palette.length],
                  }"
                ></span>
              </div>
            </div>
            <div class="mango-legend-value">
              <strong>{{ item.percentText }}</strong>
              <span>{{ item.value }}</span>
            </div>
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
  import { dispose } from 'echarts/core'
  import useEcharts from '@/hooks/useEcharts'

  // 定义 props
  const props = defineProps({
    chartData: {
      type: Array,
      required: true,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  })

  const chartRef = ref<HTMLDivElement | null>(null)
  const token = (name: string, fallback: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
  const palette = computed(() => [
    token('--m-chart-1', '#5b7cfa'),
    token('--m-chart-2', '#7bcf65'),
    token('--m-chart-3', '#f6c143'),
    token('--m-chart-4', '#38bdf8'),
    token('--m-chart-5', '#a78bfa'),
    token('--m-primary-border', '#fb7185'),
  ])

  const total = computed(() =>
    props.chartData.reduce((sum: number, item: any) => sum + Number(item.value || 0), 0)
  )

  const normalizedData = computed(() =>
    props.chartData.map((item: any) => {
      const value = Number(item.value || 0)
      const percent = total.value ? (value / total.value) * 100 : 0
      return {
        ...item,
        value,
        percent,
        percentText: `${percent.toFixed(2)}%`,
      }
    })
  )

  const initChart = () => {
    if (!chartRef.value) return

    const option = {
      color: palette.value,
      tooltip: {
        trigger: 'item',
        formatter: '{b}<br />{d}% | {c}',
      },
      series: [
        {
          name: '访问来源',
          type: 'pie',
          center: ['50%', '50%'],
          radius: ['56%', '76%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderColor: token('--m-surface', '#fff'),
            borderWidth: 4,
            borderRadius: 6,
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
          data: normalizedData.value,
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
    window.addEventListener('mango-theme-change', initChart)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('mango-theme-change', initChart)
    if (chartRef.value) {
      dispose(chartRef.value)
    }
  })
</script>

<style lang="less" scoped>
  .mango-chart-item-container {
    height: 100%;
    width: 100%;
    min-height: 0;
  }

  .mango-chart-spin,
  :deep(.mango-chart-spin .arco-spin-children) {
    display: grid;
    height: 100%;
    width: 100%;
    min-height: 0;
  }

  .mango-chart-content {
    display: grid;
    height: 100%;
    width: 100%;
    min-height: 0;
    grid-template-columns: 44% minmax(0, 1fr);
    align-items: center;
    gap: 8px;
  }

  .mango-donut-wrap {
    position: relative;
    height: 100%;
    min-height: 0;

    .mango-chart-item {
      height: 100%;
    }
  }

  .mango-donut-total {
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
      line-height: 16px;
    }

    strong {
      max-width: 76px;
      overflow: hidden;
      color: var(--m-text);
      font-size: 20px;
      font-weight: 700;
      line-height: 24px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-legend-list {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 10px;
  }

  .mango-legend-item {
    display: grid;
    min-width: 0;
    grid-template-columns: 10px minmax(0, 1fr) 74px;
    align-items: center;
    gap: 8px;
  }

  .mango-legend-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
  }

  .mango-legend-main {
    min-width: 0;
  }

  .mango-legend-name {
    display: block;
    overflow: hidden;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-legend-bar {
    height: 4px;
    margin-top: 4px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--m-border);

    span {
      display: block;
      height: 100%;
      min-width: 2px;
      border-radius: inherit;
    }
  }

  .mango-legend-value {
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
