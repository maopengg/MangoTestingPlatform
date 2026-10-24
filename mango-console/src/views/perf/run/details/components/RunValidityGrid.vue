<template>
  <div v-if="rows.length" class="mango-perf-gate-grid">
    <div v-for="item in rows" :key="item.id" class="mango-soft-panel mango-perf-gate-card">
      <div><a-tag :color="statusColor(item.status)" size="small">{{ item.status === 'passed' ? '通过' : item.status }}</a-tag><strong>{{ item.name }}</strong></div>
      <p>实际 {{ actual(item) }} · 要求 {{ required(item) }}</p>
    </div>
  </div>
  <div v-else class="mango-empty-state">暂无有效性门禁结果</div>
</template>

<script setup lang="ts">
  defineProps<{ rows: any[] }>()

  const number = (value: unknown, digits = 2) => new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(Number(value || 0))
  const percent = (value: unknown) => `${(Number(value || 0) * 100).toFixed(2)}%`
  function statusColor(status: string) { return status === 'passed' ? 'green' : status === 'warning' ? 'orange' : 'red' }
  function actual(item: any) {
    if (item.gate_key === 'generator_cpu') return `${number(item.actual_value)}%`
    if (item.gate_key === 'clock_offset') return `${number(item.actual_value, 0)} ms`
    if (['metric_coverage', 'dropped_iterations'].includes(item.gate_key)) return percent(item.actual_value)
    return number(item.actual_value, 3)
  }
  function required(item: any) {
    if (item.gate_key === 'generator_cpu') return `≤ ${number(item.required_value)}%`
    if (item.gate_key === 'clock_offset') return `≤ ${number(item.required_value, 0)} ms`
    if (item.gate_key === 'metric_coverage') return `≥ ${percent(item.required_value)}`
    if (item.gate_key === 'dropped_iterations') return `≤ ${percent(item.required_value)}`
    return number(item.required_value, 3)
  }
</script>

<style scoped lang="less">
  .mango-perf-gate-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--m-page-gap); }
  .mango-perf-gate-card { padding: 11px; }
  .mango-perf-gate-card > div { display: flex; align-items: center; gap: 8px; }
  .mango-perf-gate-card strong { overflow: hidden; color: var(--m-text); text-overflow: ellipsis; white-space: nowrap; }
  .mango-perf-gate-card p { margin: 8px 0 0; color: var(--m-muted); font-size: 12px; }
  @container (max-width: 1099px) { .mango-perf-gate-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
