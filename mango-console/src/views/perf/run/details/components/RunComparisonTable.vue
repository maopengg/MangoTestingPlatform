<template>
  <a-table :data="rows" :loading="loading" :pagination="false" :columns="comparisonColumns" :scroll="{ x: COMPARISON_TABLE_SCROLL_X }">
    <template #columns>
      <a-table-column v-for="column in comparisonColumns" :key="column.key" v-bind="column">
        <template #cell="{ record }">
          <strong v-if="column.key === 'metric'">{{ title(record.metric) }}</strong>
          <span v-else-if="column.key === 'current' || column.key === 'baseline'">{{ value(record.metric, record[column.key]) }}</span>
          <span v-else-if="column.key === 'delta'" :class="tone(record)">{{ delta(record) }}</span>
          <span v-else-if="column.key === 'delta_percent'" :class="tone(record)">{{ record.delta_percent === null ? '-' : `${Number(record.delta_percent).toFixed(2)}%` }}</span>
        </template>
      </a-table-column>
    </template>
  </a-table>
</template>

<script setup lang="ts">
  import { COMPARISON_TABLE_SCROLL_X, comparisonColumns } from '../config'

  defineProps<{ rows: any[]; loading: boolean }>()

  const labels: Record<string, string> = { request_count: '请求总数', failure_count: '失败数', avg_ms: '平均响应时间', p95_ms: 'P95 响应时间', p99_ms: 'P99 响应时间', rps: '平均 RPS' }
  const title = (metric: string) => labels[metric] || metric
  const number = (input: unknown, digits = 0) => new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(Number(input || 0))
  const value = (metric: string, input: unknown) => metric.endsWith('_ms') ? `${number(input, 2)} ms` : number(input, metric === 'rps' ? 2 : 0)
  function improved(item: any) { return ['failure_count', 'avg_ms', 'p95_ms', 'p99_ms'].includes(item.metric) ? Number(item.delta) < 0 : Number(item.delta) > 0 }
  function tone(item: any) { return !Number(item.delta) ? '' : improved(item) ? 'mango-perf-success-text' : 'mango-perf-danger-text' }
  function delta(item: any) { const current = Number(item.delta || 0); return `${current > 0 ? '+' : ''}${value(item.metric, current)}` }
</script>

<style scoped lang="less">
  .mango-perf-success-text { color: var(--m-success); font-weight: 600; }
  .mango-perf-danger-text { color: var(--m-danger); font-weight: 600; }
</style>
