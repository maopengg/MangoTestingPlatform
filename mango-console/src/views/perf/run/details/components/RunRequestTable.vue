<template>
  <a-table :columns="requestColumns" :data="rows" :loading="loading" :pagination="false" :scroll="{ x: REQUEST_TABLE_SCROLL_X }">
    <template #columns>
      <a-table-column v-for="column in requestColumns" :key="column.key" v-bind="column">
        <template #cell="{ record }">
          <div v-if="column.key === 'request'" class="mango-perf-request-name">
            <div><a-tag v-if="record.method" size="small">{{ record.method }}</a-tag><strong>{{ record.request_name || '未命名请求' }}</strong></div>
            <span v-if="record.url_path">{{ record.url_path }}</span>
          </div>
          <span v-else-if="column.key === 'error_rate'" :class="{ 'mango-perf-danger-text': Number(record.failure_count) > 0 }">{{ errorRate(record) }}</span>
          <span v-else-if="column.key === 'rps'">{{ record.rps }} / {{ record.max_rps }}</span>
          <span v-else>{{ record[column.dataIndex] ?? '-' }}</span>
        </template>
      </a-table-column>
    </template>
  </a-table>
</template>

<script setup lang="ts">
  import { REQUEST_TABLE_SCROLL_X, requestColumns } from '../config'

  defineProps<{ rows: any[]; loading: boolean }>()

  function errorRate(record: any) {
    const total = Number(record.request_count || 0)
    return `${(total ? Number(record.failure_count || 0) / total * 100 : 0).toFixed(2)}%`
  }
</script>

<style scoped lang="less">
  .mango-perf-request-name { display: grid; min-width: 0; gap: 3px; }
  .mango-perf-request-name > div { display: flex; min-width: 0; align-items: center; gap: 6px; }
  .mango-perf-request-name strong, .mango-perf-request-name span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-perf-request-name span { color: var(--m-muted); font-size: 12px; }
  .mango-perf-danger-text { color: var(--m-danger); font-weight: 600; }
</style>
