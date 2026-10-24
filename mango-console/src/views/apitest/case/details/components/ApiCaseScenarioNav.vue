<template>
  <a-tabs
    :active-key="activeKey"
    class="scenario-root-tabs"
    position="left"
    @tab-click="$emit('change', String($event))"
  >
    <a-tab-pane v-for="tab in tabs" :key="tab.key">
      <template #title>
        <span class="scenario-tab-title">
          {{ tab.label }}
          <span class="scenario-tab-count">{{ counts[tab.countKey] || 0 }}</span>
        </span>
      </template>
      <slot :name="tab.slot"></slot>
    </a-tab-pane>
  </a-tabs>
</template>

<script setup lang="ts">
  defineProps<{
    activeKey: string
    counts: Record<string, number>
  }>()

  defineEmits<{
    (event: 'change', value: string): void
  }>()

  const tabs = [
    { key: '1', label: '前置准备', countKey: 'front', slot: 'front' },
    { key: '0', label: '请求配置', countKey: 'request', slot: 'request' },
    { key: '2', label: '响应结果', countKey: 'response', slot: 'response' },
    { key: '4', label: '响应处理', countKey: 'posterior', slot: 'posterior' },
    { key: '3', label: '断言配置', countKey: 'assertion', slot: 'assertion' },
    { key: '6', label: '断言结果', countKey: 'assertionResult', slot: 'assertion-result' },
    { key: '5', label: '运行缓存', countKey: 'runtime', slot: 'runtime' },
    { key: '7', label: '工厂缓存', countKey: 'factory', slot: 'factory' },
  ]
</script>

<style scoped>
  .scenario-root-tabs {
    height: 100%;
    min-height: 0;
  }

  .scenario-root-tabs > :deep(.arco-tabs-nav) {
    height: 100%;
  }

  .scenario-tab-title {
    display: inline-flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .scenario-tab-count {
    display: inline-flex;
    min-width: 20px;
    height: 18px;
    padding: 0 5px;
    align-items: center;
    justify-content: center;
    border-radius: 9px;
    background: var(--m-fill-1);
    color: var(--m-text-2);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    line-height: 18px;
  }

  :deep(.arco-tabs-tab-active) .scenario-tab-count {
    background: var(--m-primary-soft);
    color: var(--m-primary);
  }
</style>
