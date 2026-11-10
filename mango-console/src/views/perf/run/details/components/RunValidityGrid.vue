<template>
  <div v-if="rows.length" class="mango-perf-gate-grid">
    <div v-for="item in rows" :key="item.gate_key" class="mango-soft-panel mango-perf-gate-card">
      <div><a-tag :color="statusColor(item.status)" size="small">{{ statusTitle(item.status) }}</a-tag><strong :title="item.name">{{ item.name }}</strong></div>
      <p>实际 {{ actual(item) }} · 要求 {{ required(item) }}</p>
    </div>
  </div>
  <div v-else class="mango-empty-state">暂无有效性门禁结果</div>
</template>

<script setup lang="ts">
  import type { RunValidityResult } from '../types'
  import { validityStatusLabels } from '../config'
  import { validityActual as actual, validityRequired as required } from '../presentation'
  defineProps<{ rows: RunValidityResult[] }>()

  const statusTitle = (status: string) => validityStatusLabels[status] || status
  function statusColor(status: string) { return status === 'passed' ? 'green' : status === 'warning' ? 'orange' : 'red' }
</script>

<style scoped lang="less">
  .mango-perf-gate-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--m-page-gap); }
  .mango-perf-gate-card { padding: 11px; }
  .mango-perf-gate-card > div { display: flex; min-width: 0; align-items: center; gap: 8px; }
  .mango-perf-gate-card > div > .arco-tag { flex-shrink: 0; }
  .mango-perf-gate-card strong { overflow: hidden; color: var(--m-text); text-overflow: ellipsis; white-space: nowrap; }
  .mango-perf-gate-card p { margin: 8px 0 0; color: var(--m-muted); font-size: 12px; }
  @container (max-width: 1099px) { .mango-perf-gate-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
