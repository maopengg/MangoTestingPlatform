<template>
  <div class="mango-variable-method-card">
    <a-table :columns="columns" :data="group.children" :scroll="{ x: scrollX }" :loading="loading"
      :pagination="false" :bordered="false" row-key="value">
      <template #parameter="{ record }">
        <div v-if="record.parameter.length" class="mango-variable-method-card__parameters">
          <a-tag v-for="(parameter, index) in record.parameter" :key="`${parameter.f}:${index}`" size="small" :title="parameter.n || parameter.f">
            {{ parameter.n || parameter.f }}
          </a-tag>
        </div>
        <span v-else class="mango-variable-method-card__empty">无</span>
      </template>
      <template #example="{ record }">
        <a-tooltip :content="wrapExpression(buildExample(record))" mini>
          <span class="mango-variable-method-card__expression">{{ wrapExpression(buildExample(record)) }}</span>
        </a-tooltip>
      </template>
      <template #actions="{ record }">
        <MangoTableActions :actions="[{ label: '测试', loading: testingExpression === buildExample(record), disabled: disabled || loading, onClick: () => select(record) }]" />
      </template>
    </a-table>
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { methodColumns, exampleColumns } from '../config'
  import { buildExample, wrapExpression } from '../records'
  import type { MethodItem, MethodMenuGroup } from '../types'
  const props = defineProps<{ group: MethodMenuGroup; disabled: boolean; loading: boolean; testingExpression?: string | null }>()
  const emit = defineEmits<{ (e: 'test', expression: string): void }>()
  const showActions = computed(() => !['cache', 'json'].includes(props.group.typeValue))
  const columns = computed(() => showActions.value ? [...methodColumns, ...exampleColumns] : methodColumns)
  const scrollX = computed(() => columns.value.reduce((sum, column) => sum + Number(column.width || 0), 0))
  function select(record: MethodItem) {
    if (!props.disabled && !props.loading && showActions.value) emit('test', buildExample(record))
  }
</script>
<style scoped>
  .mango-variable-method-card { min-width: 0; overflow: hidden; border: 1px solid var(--m-border); border-radius: var(--m-radius-lg); background: var(--m-surface); }
  .mango-variable-method-card__parameters { display: flex; flex-wrap: wrap; gap: 6px; min-width: 0; }
  .mango-variable-method-card__parameters :deep(.arco-tag) { max-width: 100%; overflow: hidden; text-overflow: ellipsis; }
  .mango-variable-method-card__expression { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: Consolas, monospace; color: var(--m-primary); }
  .mango-variable-method-card__empty { color: var(--m-muted); }
</style>
