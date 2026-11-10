<template>
  <a-table :data="rows" :pagination="false" :bordered="false" size="small" :scroll="{ x: 1400 }">
    <template #columns>
      <a-table-column title="来源" data-index="source_label" :width="170" />
      <a-table-column title="验证" data-index="verified" :width="90" align="center">
        <template #cell="{ record }">
          <a-tag :color="record.verified ? 'green' : 'red'" size="small">
            {{ record.verified ? '通过' : '失败' }}
          </a-tag>
        </template>
      </a-table-column>
      <a-table-column title="匹配数" data-index="count" :width="80" align="center" />
      <a-table-column title="分数" data-index="final_score" :width="80" align="center" />
      <a-table-column title="下标" data-index="sub" :width="80" align="center">
        <template #cell="{ record }">{{ record.sub ?? '-' }}</template>
      </a-table-column>
      <a-table-column title="命中信息" data-index="diagnostic_text" :width="220" :ellipsis="true" :tooltip="true" />
      <a-table-column title="失败原因" data-index="reject_reason" :width="220" :ellipsis="true" :tooltip="true">
        <template #cell="{ record }">{{ record.reject_reason || '-' }}</template>
      </a-table-column>
      <a-table-column title="定位器" data-index="loc" :width="300" :ellipsis="true" :tooltip="true" />
      <a-table-column v-if="!diagnostic" title="操作" data-index="actions" :width="160" fixed="right" align="center">
        <template #cell="{ record }">
          <MangoTableActions :actions="[1, 2, 3].map(slot => ({
            label: record.applied_slots?.includes(slot) ? '已写入' : slot === 1 ? '主定位' : `备用${slot}`,
            disabled: !record.verified || Boolean(applyingKey) || record.applied_slots?.includes(slot),
            loading: applyingKey === `${record.record_id}-${record._candidateRowIndex}-${slot}`,
            onClick: () => emit('apply', record, record._candidateRowIndex, slot),
          }))" />
        </template>
      </a-table-column>
    </template>
  </a-table>
</template>

<script setup lang="ts">
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import type { AiCandidate } from './ui-element-ai'
  withDefaults(defineProps<{
    rows: AiCandidate[]
    applyingKey?: string
    diagnostic?: boolean
  }>(), {
    applyingKey: '',
    diagnostic: false,
  })
  const emit = defineEmits<{
    (event: 'apply', record: AiCandidate, rowIndex: number, slot: number): void
  }>()
</script>
