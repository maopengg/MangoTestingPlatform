<template>
  <a-table row-key="metric" :data="rows" :loading="loading" :pagination="false" :columns="comparisonColumns" :scroll="{ x: COMPARISON_TABLE_SCROLL_X }">
    <template #columns>
      <a-table-column v-for="column in comparisonColumns" :key="column.key" v-bind="column">
        <template #cell="{ record }">
          <strong v-if="column.key === 'metric'" :title="title(record.metric)">{{ title(record.metric) }}</strong>
          <span v-else-if="column.key === 'current' || column.key === 'baseline'">{{ value(record.metric, record[column.key]) }}</span>
          <span v-else-if="column.key === 'delta'" :class="tone(record)">{{ delta(record) }}</span>
          <span v-else-if="column.key === 'delta_percent'" :class="tone(record)">{{ percent(record.delta_percent) }}</span>
        </template>
      </a-table-column>
    </template>
    <template #empty><div class="mango-empty-state">暂无对比指标</div></template>
  </a-table>
</template>

<script setup lang="ts">
  import { COMPARISON_TABLE_SCROLL_X, comparisonColumns, comparisonMetricLabels } from '../config'
  import type { RunComparisonMetric } from '../types'
  import { comparisonValue as value, comparisonTone as tone, comparisonDelta as delta, comparisonPercent as percent } from '../presentation'

  defineProps<{ rows: RunComparisonMetric[]; loading: boolean }>()

  const title = (metric: string) => comparisonMetricLabels[metric] || metric
</script>

<style scoped lang="less">
  .mango-perf-success-text { color: var(--m-success); font-weight: 600; }
  .mango-perf-danger-text { color: var(--m-danger); font-weight: 600; }
</style>
