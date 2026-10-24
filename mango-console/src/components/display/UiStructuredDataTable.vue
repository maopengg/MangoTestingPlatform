<template>
  <a-table
    :data="rows"
    :pagination="false"
    :bordered="false"
    size="small"
    :scroll="{ x: Math.max(720, columns.length * 150) }"
  >
    <template #columns>
      <a-table-column
        v-for="column in columns"
        :key="column"
        :title="column === '_index' ? '序号' : fieldLabel(column)"
        :data-index="column"
        :width="columnWidth(column)"
        :ellipsis="column !== '_index'"
        :tooltip="column !== '_index'"
      >
        <template #cell="{ record }">
          <a-tag
            v-if="BOOLEAN_COLUMNS.includes(column)"
            size="small"
            :color="record[column] ? 'green' : 'gray'"
          >
            {{ formatCell(record[column], column) }}
          </a-tag>
          <template v-else>{{ formatCell(record[column], column) }}</template>
        </template>
      </a-table-column>
    </template>
  </a-table>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  const props = defineProps<{
    rows: Record<string, any>[]
    fieldLabel: (key: string) => string
    formatCell: (value: any, key?: string) => string
  }>()
  const BOOLEAN_COLUMNS = ['verified', 'visible', 'enabled', 'editable', 'disabled', 'interactive', 'checked', 'selected', 'expanded', 'required', 'used_ai', 'auto_apply_eligible']
  const columns = computed(() => {
    const keys: string[] = ['_index']
    props.rows.forEach((row) => Object.keys(row).forEach((key) => { if (!keys.includes(key)) keys.push(key) }))
    return keys
  })
  function columnWidth(key: string) {
    if (key === '_index') return 70
    if (['loc', 'text', 'nearby_text', 'reject_reason', 'reason'].includes(key)) return 260
    return 150
  }
</script>
