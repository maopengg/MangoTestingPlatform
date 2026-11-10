<template>
  <div>
    <a-table
      v-if="rows.length"
      :data="rows"
      :columns="schemaColumns"
      :pagination="false"
      :scroll="{ x: 730 }"
      size="small"
      row-key="key"
    >
      <template #field="{ record }"
        ><div>{{ record.label }}</div
        ><span class="mango-schema-path">{{ record.path }}</span></template
      >
      <template #required="{ record }">{{ record.required ? '是' : '否' }}</template>
    </a-table>
    <div v-else class="mango-empty-state">{{
      schema?.type ? `类型：${schema.type}，未限定具体字段` : '未限定具体字段'
    }}</div>
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import { schemaColumns, schemaRows } from './presentation'
  import type { ParameterSchema } from '../types'
  const props = defineProps<{ schema?: ParameterSchema }>()
  const rows = computed(() => schemaRows(props.schema))
</script>
<style scoped>
  .mango-schema-path {
    color: var(--m-muted);
    overflow-wrap: anywhere;
    font-size: 12px;
  }
</style>
