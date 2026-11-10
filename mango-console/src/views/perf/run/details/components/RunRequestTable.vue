<template>
  <a-table row-key="id" :columns="requestColumns" :data="rows" :loading="loading" :pagination="false" :scroll="{ x: REQUEST_TABLE_SCROLL_X }">
    <template #columns>
      <a-table-column v-for="column in requestColumns" :key="column.key" v-bind="column">
        <template #cell="{ record }">
          <div v-if="column.key === 'request'" class="mango-perf-request-name">
            <div><a-tag v-if="record.method" size="small">{{ record.method }}</a-tag><strong :title="record.request_name || '未命名请求'">{{ record.request_name || '未命名请求' }}</strong></div>
            <span v-if="record.url_path" :title="record.url_path">{{ record.url_path }}</span>
          </div>
          <span v-else-if="column.key === 'error_rate'" :class="{ 'mango-perf-danger-text': Number(record.failure_count) > 0 }">{{ errorRate(record) }}</span>
          <span v-else-if="column.key === 'rps'">{{ number(record.rps, 2) }} / {{ number(record.max_rps, 2) }}</span>
          <span v-else>{{ cell(record, column.key) }}</span>
        </template>
      </a-table-column>
    </template>
    <template #empty><div class="mango-empty-state">暂无请求统计</div></template>
  </a-table>
</template>

<script setup lang="ts">
  import { REQUEST_TABLE_SCROLL_X, requestColumns } from '../config'
  import type { RequestColumnKey, RunRequestSummary } from '../types'
  import { formatRunNumber as number, requestErrorRate as errorRate } from '../presentation'

  defineProps<{ rows: RunRequestSummary[]; loading: boolean }>()

  function cell(record: RunRequestSummary, key: RequestColumnKey) {
    if (key === 'request' || key === 'error_rate' || key === 'rps') return '-'
    return record[key] ?? '-'
  }
</script>

<style scoped lang="less">
  .mango-perf-request-name { display: grid; min-width: 0; gap: 3px; }
  .mango-perf-request-name > div { display: flex; min-width: 0; align-items: center; gap: 6px; }
  .mango-perf-request-name strong, .mango-perf-request-name span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-perf-request-name strong { min-width: 0; }
  .mango-perf-request-name span { color: var(--m-muted); font-size: 12px; }
  .mango-perf-danger-text { color: var(--m-danger); font-weight: 600; }
</style>
