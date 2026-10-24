<template>
  <a-table :data="rows" :pagination="false" :bordered="false" size="small" :scroll="{ x: 900 }">
    <template #columns>
      <a-table-column title="来源" data-index="source_label" :width="170" />
      <a-table-column title="验证" data-index="verified" :width="90">
        <template #cell="{ record }">
          <a-tag :color="record.verified ? 'green' : 'red'" size="small">
            {{ record.verified ? '通过' : '失败' }}
          </a-tag>
        </template>
      </a-table-column>
      <a-table-column title="匹配数" data-index="count" :width="80" />
      <a-table-column title="分数" data-index="final_score" :width="80" />
      <a-table-column title="下标" data-index="sub" :width="80">
        <template #cell="{ record }">{{ record.sub ?? '-' }}</template>
      </a-table-column>
      <a-table-column title="命中信息" data-index="diagnostic_text" :width="220" :ellipsis="true" :tooltip="true" />
      <a-table-column title="失败原因" data-index="reject_reason" :width="220" :ellipsis="true" :tooltip="true">
        <template #cell="{ record }">{{ record.reject_reason || '-' }}</template>
      </a-table-column>
      <a-table-column title="定位器" data-index="loc" :ellipsis="true" :tooltip="true" />
      <a-table-column v-if="!diagnostic" title="操作" data-index="actions" :width="220" fixed="right">
        <template #cell="{ record }">
          <a-space>
            <a-button
              v-for="slot in 3"
              :key="slot"
              size="mini"
              :type="slot === 1 ? 'primary' : 'secondary'"
              :disabled="!record.verified"
              :loading="applyingKey === `${record.record_id}-${record._candidateRowIndex}-${slot}`"
              @click="emit('apply', record, record._candidateRowIndex, slot)"
            >
              {{ slot === 1 ? '主定位' : `备用${slot}` }}
            </a-button>
          </a-space>
        </template>
      </a-table-column>
    </template>
  </a-table>
</template>

<script setup lang="ts">
  withDefaults(defineProps<{
    rows: any[]
    applyingKey?: string
    diagnostic?: boolean
  }>(), {
    applyingKey: '',
    diagnostic: false,
  })
  const emit = defineEmits<{
    (event: 'apply', record: any, rowIndex: number, slot: number): void
  }>()
</script>
