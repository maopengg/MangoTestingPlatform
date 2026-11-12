<template>
  <div class="mango-capability-overview">
    <mango-panel-spin :loading="loading" class="mango-capability-overview__spin">
      <div
        v-if="!loadFailed"
        ref="capabilityGridRef"
        class="mango-capability-grid mango-native-scrollbar"
        :class="{ 'mango-capability-grid--single': capabilityColumns === 1 }"
      >
        <article
          v-for="group in capabilityGroups"
          :key="group.key"
          class="mango-capability-card"
          :style="{ '--mango-capability-accent': group.accent }"
        >
          <header class="mango-capability-card__header">
            <span class="mango-capability-card__icon"><component :is="group.icon" /></span>
            <div class="mango-capability-card__title" :title="group.title">
              <strong>{{ group.title }}</strong>
              <span :title="group.description">{{ group.description }}</span>
            </div>
            <div class="mango-capability-card__total">
              <strong>{{ formatValue(group.total) }}</strong>
              <span>建设总量</span>
            </div>
          </header>
          <dl class="mango-capability-card__metrics">
            <div
              v-for="metric in group.metrics"
              :key="metric.label"
              class="mango-capability-metric"
              :title="`${metric.label}：${formatValue(metric.value)}`"
            >
              <dt>{{ metric.label }}</dt>
              <dd>{{ formatValue(metric.value) }}</dd>
            </div>
          </dl>
        </article>
      </div>
      <div v-else-if="!loading" class="mango-empty-state mango-capability-overview__empty">
        <a-button size="mini" type="text" @click="fetchStatistics">重新加载</a-button>
      </div>
    </mango-panel-spin>
  </div>
</template>

<script lang="ts" setup>
  import { computed, markRaw, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import {
    IconCalendar,
    IconCode,
    IconDesktop,
    IconSettings,
    IconStorage,
    IconThunderbolt,
  } from '@arco-design/web-vue/es/icon'
  import { getSystemIndexStatistics } from '@/api/system'
  import { useHomeMenuIcon } from '@/views/index/composables/use-home-menu-icon'
  import { useHomeSnapshot } from '../composables/use-home-snapshot'
  import { emptyStatistics, readStatistics } from '../records'
  import { displayDensityScale, scaleDensityPixels } from '@/hooks/useDisplayDensity'

  const { snapshot: statistics, loading, loadFailed, reload: fetchStatistics, isAvailable } = useHomeSnapshot({
    read: getSystemIndexStatistics, parse: readStatistics, empty: emptyStatistics,
  })
  const { resolveMenuIcon } = useHomeMenuIcon()
  const capabilityGridRef = ref<HTMLElement | null>(null)
  const capabilityColumns = ref<1 | 2>(1)
  let capabilityResizeObserver: ResizeObserver | null = null
  let capabilityLayoutFrame = 0

  const capabilityGroups = computed(() =>
    [
      {
        key: 'ui',
        title: 'UI自动化',
        description: '页面对象与可编排步骤',
        icon: resolveMenuIcon('/uitest', markRaw(IconDesktop)),
        accent: 'var(--m-primary)',
        metrics: [
          { label: '页面', value: statistics.value.uiStats.pageCount },
          { label: '元素', value: statistics.value.uiStats.elementCount },
          { label: '页面步骤', value: statistics.value.uiStats.stepCount },
          { label: '测试用例', value: statistics.value.uiStats.caseCount },
          { label: '全局变量', value: statistics.value.uiStats.publicCount },
          { label: '授权配置', value: statistics.value.uiStats.authConfigCount },
        ],
      },
      {
        key: 'api',
        title: 'API自动化',
        description: '接口与公共调用配置',
        icon: resolveMenuIcon('/apitest', markRaw(IconThunderbolt)),
        accent: 'color-mix(in srgb, var(--m-primary) 78%, var(--m-text))',
        metrics: [
          { label: '接口', value: statistics.value.apiStats.interfaceCount },
          { label: '测试用例', value: statistics.value.apiStats.caseCount },
          { label: '执行场景', value: statistics.value.apiStats.scenarioCount },
          { label: '全局变量', value: statistics.value.apiStats.publicCount },
          { label: '公共请求头', value: statistics.value.apiStats.headerCount },
          { label: '授权配置', value: statistics.value.apiStats.authConfigCount },
        ],
      },
      {
        key: 'pytest',
        title: 'Pytest自动化',
        description: '外部工程与测试文件同步',
        icon: resolveMenuIcon('/pytest', markRaw(IconCode)),
        accent: 'color-mix(in srgb, var(--m-primary) 68%, var(--m-surface))',
        metrics: [
          { label: '工程', value: statistics.value.pytestStats.projectCount },
          { label: '测试用例', value: statistics.value.pytestStats.caseCount },
          { label: '测试文件', value: statistics.value.pytestStats.fileCount },
          { label: '已绑定工程', value: statistics.value.pytestStats.boundProjectCount },
          { label: '绑定产品', value: statistics.value.pytestStats.boundProductCount },
        ],
      },
      {
        key: 'data-factory',
        title: '数据工厂',
        description: '测试数据生成基础配置',
        icon: resolveMenuIcon('/data-factory', markRaw(IconStorage)),
        accent: 'color-mix(in srgb, var(--m-primary) 52%, var(--m-muted))',
        metrics: [
          { label: '逻辑数据源', value: statistics.value.dataFactoryStats.datasourceCount },
          { label: '数据库绑定', value: statistics.value.dataFactoryStats.datasourceBindingCount },
          { label: '数据实体', value: statistics.value.dataFactoryStats.entityCount },
          { label: '字段规则', value: statistics.value.dataFactoryStats.fieldCount },
          { label: '场景模板', value: statistics.value.dataFactoryStats.templateCount },
          { label: '用例配置', value: statistics.value.dataFactoryStats.caseConfigCount },
        ],
      },
      {
        key: 'test-config',
        title: '测试配置',
        description: '项目、环境与测试资料配置',
        icon: resolveMenuIcon('/config', markRaw(IconSettings)),
        accent: 'color-mix(in srgb, var(--m-primary) 62%, var(--m-text-2))',
        metrics: [
          { label: '项目配置', value: statistics.value.testConfigStats.projectCount },
          { label: '项目产品', value: statistics.value.testConfigStats.projectProductCount },
          { label: '数据库配置', value: statistics.value.testConfigStats.databaseCount },
          { label: '测试对象', value: statistics.value.testConfigStats.testObjectCount },
          { label: '测试文件', value: statistics.value.testConfigStats.testFileCount },
        ],
      },
      {
        key: 'scheduled-task',
        title: '定时任务',
        description: '自动触发策略与执行记录',
        icon: resolveMenuIcon('/timing', markRaw(IconCalendar)),
        accent: 'color-mix(in srgb, var(--m-primary) 46%, var(--m-muted))',
        metrics: [
          { label: '定时任务', value: statistics.value.scheduledTaskStats.taskCount },
          { label: '定时策略', value: statistics.value.scheduledTaskStats.strategyCount },
          { label: '触发记录', value: statistics.value.scheduledTaskStats.fireRecordCount },
          { label: '系统定时任务', value: statistics.value.scheduledTaskStats.systemJobCount },
        ],
      },
    ].map((group) => {
      const total = group.metrics.reduce((sum, metric) => sum + Number(metric.value || 0), 0)
      return {
        ...group,
        total,
      }
    })
  )

  function formatValue(value: number | null) {
    if (value === null || value === undefined) return '-'
    return Number(value).toLocaleString('zh-CN')
  }

  function updateCapabilityColumns() {
    const container = capabilityGridRef.value
    if (!container) return
    const style = getComputedStyle(container)
    const gap = Number.parseFloat(style.columnGap) || 0
    const minimumCardWidth = scaleDensityPixels(250)
    capabilityColumns.value = (container.clientWidth - gap) / 2 >= minimumCardWidth ? 2 : 1
  }

  function scheduleCapabilityLayout() {
    if (!isAvailable()) return
    if (capabilityLayoutFrame) window.cancelAnimationFrame(capabilityLayoutFrame)
    capabilityLayoutFrame = window.requestAnimationFrame(() => {
      if (isAvailable()) updateCapabilityColumns()
      capabilityLayoutFrame = 0
    })
  }

  function stopLayout() {
    capabilityResizeObserver?.disconnect()
    capabilityResizeObserver = null
    window.removeEventListener('resize', scheduleCapabilityLayout)
    if (capabilityLayoutFrame) window.cancelAnimationFrame(capabilityLayoutFrame)
    capabilityLayoutFrame = 0
  }
  function startLayout() {
    stopLayout()
    if (!isAvailable() || !capabilityGridRef.value) return
    scheduleCapabilityLayout()
    if (typeof ResizeObserver !== 'undefined') {
      capabilityResizeObserver = new ResizeObserver(scheduleCapabilityLayout)
      capabilityResizeObserver.observe(capabilityGridRef.value)
    } else window.addEventListener('resize', scheduleCapabilityLayout)
  }
  watch(capabilityGridRef, startLayout, { flush: 'post' })
  watch(displayDensityScale, scheduleCapabilityLayout)
  onMounted(startLayout)
  onActivated(startLayout)
  onDeactivated(stopLayout)
  onBeforeUnmount(stopLayout)

  defineExpose({ refresh: fetchStatistics })
</script>

<style lang="less" scoped>
  .mango-capability-overview {
    flex: 1;
    min-height: 0;
    padding: 6px 10px 10px;
  }

  .mango-capability-overview__spin,
  :deep(.mango-capability-overview__spin > .mango-panel-spin__content) {
    display: block;
    height: 100%;
    min-height: 0;
  }

  .mango-capability-grid {
    display: grid;
    height: 100%;
    min-height: 0;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-auto-rows: minmax(176px, 1fr);
    gap: 8px;
    overflow-y: auto;
    padding-right: 4px;
    scrollbar-gutter: stable;
  }

  .mango-capability-grid--single {
    grid-template-columns: minmax(0, 1fr);
  }

  .mango-capability-card {
    position: relative;
    display: grid;
    min-width: 0;
    min-height: 0;
    grid-template-rows: auto minmax(0, 1fr);
    gap: 8px;
    overflow: hidden;
    padding: 10px 10px 8px;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-surface);

    &::before {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      width: 3px;
      background: var(--mango-capability-accent);
      content: '';
      opacity: 0.82;
    }
  }

  .mango-capability-card__header {
    display: grid;
    min-width: 0;
    align-items: center;
    grid-template-columns: 28px minmax(92px, 1fr) auto;
    gap: 8px;

    .mango-capability-card__title {
      display: flex;
      min-width: 0;
      flex: 1;
      flex-direction: column;
    }

    strong {
      overflow: hidden;
      color: var(--m-text);
      font-size: 14px;
      line-height: 20px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span:not(.mango-capability-card__icon) {
      overflow: hidden;
      color: var(--m-muted);
      font-size: 10px;
      line-height: 15px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-capability-card__total {
    display: flex;
    flex: 0 0 auto;
    align-items: flex-end;
    flex-direction: column;

    strong {
      color: var(--mango-capability-accent);
      font-size: 17px;
      font-variant-numeric: tabular-nums;
      line-height: 21px;
    }

    span {
      color: var(--m-muted);
      font-size: 10px;
      line-height: 14px;
    }
  }

  .mango-capability-card__icon {
    display: inline-flex;
    width: 28px;
    height: 28px;
    flex: 0 0 28px;
    align-items: center;
    justify-content: center;
    border: 1px solid color-mix(in srgb, var(--mango-capability-accent) 28%, var(--m-border));
    border-radius: 6px;
    background: color-mix(in srgb, var(--mango-capability-accent) 10%, var(--m-surface));
    color: var(--mango-capability-accent);
    font-size: 15px;
  }

  .mango-capability-card__metrics {
    display: grid;
    margin: 0;
    min-height: 0;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-auto-rows: minmax(28px, 1fr);
    align-content: stretch;
    gap: 5px;
    padding-top: 8px;
    border-top: 1px solid var(--m-border);
  }

  .mango-capability-metric {
    position: relative;
    display: flex;
    min-width: 0;
    min-height: 0;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    overflow: hidden;
    padding: 4px 7px;
    border: 1px solid var(--m-border);
    border-radius: 5px;
    background: var(--m-surface-soft);

    dd {
      flex: 0 0 auto;
      margin: 0;
      color: var(--mango-capability-accent);
      font-size: 14px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      line-height: 18px;
      white-space: nowrap;
    }

    dt {
      min-width: 0;
      overflow: hidden;
      color: var(--m-text-2);
      font-size: 10px;
      line-height: 14px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-capability-overview__empty {
    display: flex;
    height: 100%;
    align-items: center;
    flex-direction: column;
    gap: 4px;
    justify-content: center;
  }

  @media (max-height: 760px) {
    .mango-capability-card {
      gap: 4px;
      padding: 7px 7px 5px;
    }

    .mango-capability-card__metrics {
      row-gap: 2px;
      padding-top: 3px;
    }

    .mango-capability-metric {
      padding: 2px 5px;

      dd {
        font-size: 12px;
        line-height: 16px;
      }

      dt {
        font-size: 9px;
        line-height: 12px;
      }
    }
  }
</style>
